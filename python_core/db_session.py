import sqlite3
import os
import logging
import json
import python_core.utils.safe_file_utils as safefileutils
import tempfile


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_config_value(name, default="NONE FOUND"):
    """Get config value from builtins (injected by JS) or use default."""
    try:
        import builtins
        return getattr(builtins, name, default)
    except (ImportError, AttributeError):
        return default



class DatabaseSession:
    # synchronous context manager for SQLite
    def __init__(self, db_path=None, schema_path=None, use_dict_factory=False):
        self.db_path_orig = db_path or get_config_value('DB_PATH')
        self.db_path_target = None
        self.schema_path = schema_path or get_config_value('SCHEMA_PATH')

        self.is_firefox = get_config_value('IS_FIREFOX', default=False)
        self.firefox_internal_temp_path = "/tmp/working_db.sqlite"

        self.use_dict_factory = use_dict_factory
        self.conn = None
        self.logger = logging.getLogger(__name__)


    # def _firefox_workaround_opfs_to_memfs(self):
    #     # Workaround: Mirror OPFS to internal MEMFS to avoid Firefox stat() crash
    #     os.makedirs("/tmp", exist_ok=True)
    #     fd, path = tempfile.mkstemp(suffix=".sqlite", dir="/tmp")
    #     os.close(fd) 
    #     self.firefox_internal_temp_path = path

    #     if safefileutils.exists(self.db_path_orig):
    #         # with open(self.db_path_orig, 'rb') as src, open(self.firefox_internal_temp_path, 'wb') as dst:
    #         #     dst.write(src.read())
    #         with open(self.firefox_internal_temp_path, 'rb') as src:
    #             data = src.read()
    #         with open(self.db_path_orig, 'wb') as dst:
    #             dst.write(data)
    #     return self.firefox_internal_temp_path
    
    def _firefox_workaround_opfs_to_memfs(self):
        # Workaround: Mirror OPFS to internal MEMFS to avoid Firefox stat() crash
        os.makedirs("/tmp", exist_ok=True)

        if safefileutils.exists(self.db_path_orig):
            db_bytes = safefileutils.read_bytes(self.db_path_orig)
            with open(self.firefox_internal_temp_path, 'wb') as dst:
                dst.write(db_bytes)
        else:
            # Create an empty file to ensure it exists for Firefox
            with open(self.firefox_internal_temp_path, 'wb') as dst:
                dst.write(b"")
                
        return self.firefox_internal_temp_path
    
    def _firefox_flush_memfs_to_opfs(self):
        if self.firefox_internal_temp_path and safefileutils.exists(self.firefox_internal_temp_path):
            with open(self.firefox_internal_temp_path, 'rb') as src, open(self.db_path_orig, 'wb') as dst:
                dst.write(src.read())
            os.remove(self.firefox_internal_temp_path)
            self.firefox_internal_temp_path = None


    def __enter__(self):

        try:
            if self.is_firefox:
                print(f"[DBSession] Firefox detected, applying OPFS to MEMFS workaround for DB path: {self.db_path_orig}")
                self.db_path_target = self._firefox_workaround_opfs_to_memfs()
                print(f"[DBSession] Using temporary MEMFS path for SQLite connection: {self.db_path_target}")
            else:
                db_dir = os.path.dirname(self.db_path_orig)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                self.db_path_target = self.db_path_orig
                
            
            self.conn = sqlite3.connect(self.db_path_target, timeout=10.0, check_same_thread=False)
            print(f"[DB] Successfully connected to {self.db_path_target}")


            if self.use_dict_factory:
                self.conn.row_factory = dict_factory
            # else: defaults to tuple, used in worker bc more efficient

            self.conn.execute('PRAGMA journal_mode = DELETE; ')
            self.conn.execute('PRAGMA foreign_keys = ON;')
            
            if self.schema_path:
                if not safefileutils.exists(self.schema_path):
                    raise FileNotFoundError(f"Schema file not found at: {self.schema_path}")
                
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    self.conn.executescript(f.read())
                
                self.conn.commit()
                
            return self.conn

        except Exception as e:
            if self.conn:
                self.conn.close()
            if self.is_firefox and safefileutils.exists(self.firefox_internal_temp_path):
                os.remove(self.firefox_internal_temp_path)
            print(f"[DBSession] Error during __enter__: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            try:
                if exc_type is None:
                    self.conn.commit()
                self.conn.close()
            
                if self.is_firefox:
                    if exc_type is None:
                        self._firefox_flush_memfs_to_opfs()
                    if self.firefox_internal_temp_path and safefileutils.exists(self.firefox_internal_temp_path):
                        os.remove(self.firefox_internal_temp_path)
            
            except Exception as e:
                print(f"[DBSession] Error during __exit__: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()