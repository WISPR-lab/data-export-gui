import sqlite3
import os
import json
import python_core.runtime.safe_file_utils as safefileutils
from python_core.runtime.pyodide_utils import get_config_value
from python_core.logger import get_logger

logger = get_logger("DBSession")


class _CountingConnection(sqlite3.Connection):
    """ sqlite3.Connection subclass to deal with the fact that the regular connection 
    object has no __dict__ and thus _execute_call_count can't be set"""


def dict_factory(cursor: sqlite3.Cursor, row: tuple, json_columns: set = None) -> dict:
    d = {}
    for idx, col in enumerate(cursor.description):
        val = row[idx]
        if json_columns and col[0] in json_columns and isinstance(val, str):
            try:
                d[col[0]] = json.loads(val) if val else {}
            except (json.JSONDecodeError, ValueError):
                d[col[0]] = {}
        else:
            d[col[0]] = val
    return d


def configure_row_factory(conn: sqlite3.Connection, use_dict_factory: bool = False, json_columns: set = None) -> None:
    # Set/reset row_factory on an already-open connection
    conn.row_factory = (
        (lambda cursor, row: dict_factory(cursor, row, json_columns or set()))
        if use_dict_factory
        else None
    )


class DatabaseSession:
    """synchronous context manager for SQLite"""

    def __init__(
        self,
        db_path: str = None,
        schema_path: str = None,
        use_dict_factory: bool = False,
        json_columns: list = None,
        existing_conn: sqlite3.Connection = None,
    ) -> None:
        self.db_path_orig = db_path or get_config_value("DB_PATH")
        self.db_path_target = None
        self.schema_path = schema_path or get_config_value("SCHEMA_PATH")
        self.json_columns = set(json_columns or [])

        self.is_firefox = get_config_value("IS_FIREFOX", default=False)
        self.is_safari = get_config_value("IS_SAFARI", default=False)
        self.firefox_internal_temp_path = "/tmp/working_db.sqlite"

        self.use_dict_factory = use_dict_factory
        self.conn = None
        # If set, __enter__/__exit__ borrow this connection (just reconfigure row_factory)
        # instead of opening/closing/copying their own — lets pipeline stages share one
        # connection across a run instead of each paying the Firefox/Safari OPFS<->MEMFS
        # copy cost separately. See run.py.
        self.existing_conn = existing_conn

    def _wrap_execute_counting(self) -> None:
        # Counts execute/executemany calls on conn (see python_core/performance.py).
        # Idempotent so stages sharing a connection (existing_conn) share one running count.
        if getattr(self.conn, "_execute_counting_wrapped", False):
            return

        self.conn._execute_call_count = 0
        orig_execute = self.conn.execute
        orig_executemany = self.conn.executemany

        def execute(sql, params=None):
            self.conn._execute_call_count += 1
            return orig_execute(sql, params) if params is not None else orig_execute(sql)

        def executemany(sql, params_list):
            self.conn._execute_call_count += 1
            return orig_executemany(sql, params_list)

        self.conn.execute = execute
        self.conn.executemany = executemany
        self.conn._execute_counting_wrapped = True

    def _wrap_json_serialization(self) -> None:
        orig_execute = self.conn.execute
        orig_executemany = self.conn.executemany

        def execute(sql, params=None):
            if params and isinstance(params, dict):
                params = self._serialize_params(params)
            return orig_execute(sql, params)

        def executemany(sql, params_list):
            if params_list and isinstance(params_list[0], dict):
                params_list = [self._serialize_params(p) for p in params_list]
            return orig_executemany(sql, params_list)

        self.conn.execute = execute
        self.conn.executemany = executemany

    def _serialize_params(self, params: dict) -> dict:
        params = params.copy()
        for col in self.json_columns:
            if col in params and params[col] is not None:
                val = params[col]
                if isinstance(val, (list, dict)):
                    params[col] = json.dumps(val)
        return params

    def _firefox_workaround_opfs_to_memfs(self) -> str:
        """Workaround: Mirror OPFS to internal MEMFS to avoid Firefox stat() crash"""
        os.makedirs("/tmp", exist_ok=True)

        if safefileutils.exists(self.db_path_orig):
            db_bytes = safefileutils.read_bytes(self.db_path_orig)
            with open(self.firefox_internal_temp_path, "wb") as dst:
                dst.write(db_bytes)
        else:
            # Create an empty file to ensure it exists for Firefox
            with open(self.firefox_internal_temp_path, "wb") as dst:
                dst.write(b"")

        return self.firefox_internal_temp_path

    def _firefox_flush_memfs_to_opfs(self) -> None:
        if self.firefox_internal_temp_path and safefileutils.exists(
            self.firefox_internal_temp_path
        ):
            with (
                open(self.firefox_internal_temp_path, "rb") as src,
                open(self.db_path_orig, "wb") as dst,
            ):
                dst.write(src.read())
            os.remove(self.firefox_internal_temp_path)
            self.firefox_internal_temp_path = None

    def __enter__(self) -> sqlite3.Connection:
        if self.existing_conn is not None:
            self.conn = self.existing_conn
            configure_row_factory(self.conn, self.use_dict_factory, self.json_columns)
            self._wrap_execute_counting()
            return self.conn

        try:
            if self.is_firefox or self.is_safari:
                self.db_path_target = self._firefox_workaround_opfs_to_memfs()
            else:
                db_dir = os.path.dirname(self.db_path_orig)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                self.db_path_target = self.db_path_orig

            self.conn = sqlite3.connect(
                self.db_path_target,
                timeout=10.0,
                check_same_thread=False,
                factory=_CountingConnection,
            )

            configure_row_factory(self.conn, self.use_dict_factory, self.json_columns)
            self._wrap_execute_counting()

            self.conn.execute("PRAGMA journal_mode = DELETE; ")
            self.conn.execute("PRAGMA foreign_keys = ON;")

            if self.schema_path:
                if not safefileutils.exists(self.schema_path):
                    raise FileNotFoundError(
                        f"Schema file not found at: {self.schema_path}"
                    )

                with open(self.schema_path, "r", encoding="utf-8") as f:
                    self.conn.executescript(f.read())

                self.conn.commit()

            return self.conn

        except Exception as e:
            if self.conn:
                self.conn.close()
            if (self.is_firefox or self.is_safari) and safefileutils.exists(
                self.firefox_internal_temp_path
            ):
                os.remove(self.firefox_internal_temp_path)
            logger.error(f"Error during __enter__: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.existing_conn is not None:
            # Borrowed connection — its owner (see run.py) closes/copies it once,
            # after every stage sharing it has finished. Just commit this stage's work.
            if self.conn and exc_type is None:
                self.conn.commit()
            return

        if self.conn:
            try:
                if exc_type is None:
                    self.conn.commit()
                self.conn.close()

                if self.is_firefox or self.is_safari:
                    if exc_type is None:
                        self._firefox_flush_memfs_to_opfs()
                    if self.firefox_internal_temp_path and safefileutils.exists(
                        self.firefox_internal_temp_path
                    ):
                        os.remove(self.firefox_internal_temp_path)

            except Exception as e:
                logger.error(f"Error during __exit__: {type(e).__name__}: {e}")
                import traceback

                traceback.print_exc()
