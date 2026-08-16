import os
import js
from manifest import Manifest
from db_session import DatabaseSession, configure_row_factory
from extractors import worker as extractor_worker
import semantic_map.worker as semantic_map_worker
from field_normalization import worker as norm_worker
import device_grouping2.worker as device_grouping2_worker
from semantic_map.worker import get_counts
from performance import measure_stage
from python_core.runtime.pyodide_utils import get_config_value
from python_core.logger import get_logger

logger = get_logger("performance")

# TODO: collect each stage's (name, duration_ms, rows, db_calls) here and log
# a single JSON summary at the end of run(), for the JS worker to parse.


def _rows_in_table(conn, table: str, upload_id: str) -> int:
    # Nested DatabaseSession(...) calls inside the worker modules can leave conn.row_factory
    # set to the dict factory when they return (see db_session.py) — reset it so fetchone()
    # here is a plain tuple regardless of what the stage we're timing just did.
    configure_row_factory(conn, use_dict_factory=False)
    return conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE upload_id = ?", (upload_id,)
    ).fetchone()[0]


def _database_size_bytes() -> int:
    try:
        return os.path.getsize(get_config_value("DB_PATH"))
    except OSError:
        return None


def run(platform: str, given_name: str) -> dict:
    manifest = Manifest(platform=platform)
    database_size_before = _database_size_bytes()

    with DatabaseSession() as conn:
        with measure_stage("extract", conn=conn) as result:
            js.reportProgress("extract", 30)
            extract_res = extractor_worker.extract(platform, given_name, manifest=manifest, conn=conn)
            upload_id = extract_res.get("upload_id")
            if not upload_id:
                raise ValueError("Extraction failed to return an upload_id")
            result.rows = _rows_in_table(conn, "events", upload_id)

        with measure_stage("semantic_map", conn=conn) as result:
            js.reportProgress("semantic_map", 40)
            semantic_map_worker.map(platform, upload_id, manifest=manifest, conn=conn)
            result.rows = _rows_in_table(conn, "events", upload_id)

        with measure_stage("normalize", conn=conn) as result:
            js.reportProgress("normalize", 60)
            norm_res = norm_worker.normalize(upload_id, conn=conn)
            result.rows = norm_res.get("records_normalized", 0)

        with measure_stage("group", conn=conn) as result:
            js.reportProgress("group", 85)
            device_grouping2_worker.group(upload_id, conn=conn)
            result.rows = _rows_in_table(conn, "device_groups", upload_id)

        counts = get_counts(upload_id, conn=conn)

    database_size_after = _database_size_bytes()
    logger.info(
        f"PERFORMANCE_MEMORY database_size_before_bytes={database_size_before} "
        f"database_size_after_bytes={database_size_after}"
    )

    return {
        "status": "success",
        "upload_id": upload_id,
        "events_count": counts.get("events_count", 0),
        "devices_count": counts.get("devices_count", 0),
        "partial_errors": extract_res.get("partial_errors", []),
    }
