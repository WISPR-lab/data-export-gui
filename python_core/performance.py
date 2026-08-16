"""Per-stage timing for the pipeline (run.py).

Logs one line per stage:

    PERFORMANCE_MEMORY stage=<name> dur_ms=<float> rows=<int> db_calls=<int>

`db_calls` requires a `conn` whose execute/executemany are call-counted
(DatabaseSession._wrap_execute_counting, see db_session.py).
"""
import time
from contextlib import contextmanager

from python_core.logger import get_logger

logger = get_logger("performance")

# TODO: continuous heap sampling when PERFORMANCE_MEMORY_SAMPLING is on — background
# thread reading js.performance.memory every PERFORMANCE_MEMORY_SAMPLING_INTERVAL_MS.
# Must no-op (not raise) when `js` isn't available, e.g. running under pytest.


class _StageResult:
    rows = None


@contextmanager
def measure_stage(stage_name: str, conn=None):
    """Times a pipeline stage and logs one line on exit.

    Usage:
        with measure_stage("extract", conn=conn) as result:
            do_work()
            result.rows = count_rows()  # optional
    """
    start = time.perf_counter()
    calls_before = getattr(conn, "_execute_call_count", None) if conn is not None else None

    result = _StageResult()
    try:
        yield result
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        parts = [f"stage={stage_name}", f"dur_ms={duration_ms:.1f}"]
        if result.rows is not None:
            parts.append(f"rows={result.rows}")
        if conn is not None and calls_before is not None:
            calls_after = getattr(conn, "_execute_call_count", calls_before)
            parts.append(f"db_calls={calls_after - calls_before}")
        logger.info("PERFORMANCE_MEMORY " + " ".join(parts))
