import json
import os
import time
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


def _stage_summary(stage_name: str, result) -> dict:
    entry = {
        "stage": stage_name,
        "duration_ms": round(result.duration_ms, 1) if result.duration_ms is not None else None,
        "rows_processed": result.rows,
        "database_calls": result.db_calls,
        "sampling_mode": result.sampling_mode,
    }
    if result.heap_samples:
        entry["heap_samples"] = [
            {"elapsed_ms": round(elapsed_ms, 1), "heap_bytes": heap_bytes}
            for elapsed_ms, heap_bytes in result.heap_samples
        ]
    return entry


def run(platform: str, given_name: str) -> dict:
    manifest = Manifest(platform=platform)
    database_size_before = _database_size_bytes()
    pipeline_start = time.perf_counter()
    stage_summaries = []

    with DatabaseSession() as conn:
        with measure_stage("extract", conn=conn) as result:
            js.reportProgress("extract", 30)
            extract_res = extractor_worker.extract(platform, given_name, manifest=manifest, conn=conn)
            upload_id = extract_res.get("upload_id")
            if not upload_id:
                raise ValueError("Extraction failed to return an upload_id")
            result.rows = _rows_in_table(conn, "events", upload_id)
        stage_summaries.append(_stage_summary("extract", result))

        with measure_stage("semantic_map", conn=conn) as result:
            js.reportProgress("semantic_map", 40)
            semantic_map_worker.map(platform, upload_id, manifest=manifest, conn=conn)
            result.rows = _rows_in_table(conn, "events", upload_id)
        stage_summaries.append(_stage_summary("semantic_map", result))

        with measure_stage("normalize", conn=conn) as result:
            js.reportProgress("normalize", 60)
            norm_res = norm_worker.normalize(upload_id, conn=conn)
            result.rows = norm_res.get("records_normalized", 0)
        stage_summaries.append(_stage_summary("normalize", result))

        with measure_stage("group", conn=conn) as result:
            js.reportProgress("group", 85)
            device_grouping2_worker.group(upload_id, conn=conn)
            result.rows = _rows_in_table(conn, "device_groups", upload_id)
        stage_summaries.append(_stage_summary("group", result))

        counts = get_counts(upload_id, conn=conn)

    database_size_after = _database_size_bytes()
    total_duration_ms = round((time.perf_counter() - pipeline_start) * 1000, 1)

    pipeline_summary = {
        "total_duration_ms": total_duration_ms,
        "stages": stage_summaries,
        "database_size_before_bytes": database_size_before,
        "database_size_after_bytes": database_size_after,
        "memory_sampling_enabled": bool(get_config_value("PERFORMANCE_MEMORY_SAMPLING", default=False)),
    }
    # Machine-parseable summary line — matches the `pipeline_summary` shape documented
    # in the README. Also returned below as `performance_summary` so the JS worker can
    # consume it directly (more robust than scraping this log line).
    logger.info("PERFORMANCE_MEMORY_SUMMARY " + json.dumps({"pipeline_summary": pipeline_summary}))

    return {
        "status": "success",
        "upload_id": upload_id,
        "events_count": counts.get("events_count", 0),
        "devices_count": counts.get("devices_count", 0),
        "partial_errors": extract_res.get("partial_errors", []),
        "performance_summary": pipeline_summary,
    }
