"""Per-stage timing for the pipeline (run.py).

Logs one line per stage:

    PERFORMANCE_MEMORY stage=<name> dur_ms=<float> rows=<int> db_calls=<int>

`db_calls` requires a `conn` whose execute/executemany are call-counted
(DatabaseSession._wrap_execute_counting, see db_session.py).

When PERFORMANCE_MEMORY_SAMPLING is on (see builtins, injected by
pyodide-worker.js from config.yaml's performance.memory_sampling_enabled),
each stage also gets continuous JS-heap sampling on a background thread —
see _HeapSampler below. If continuous sampling does not work for some reason, downgrates
to single sample or is totally disabeld (see sampling_mode)"""
import threading
import time
from contextlib import contextmanager

from python_core.logger import get_logger
from python_core.runtime.pyodide_utils import get_config_value

logger = get_logger("performance")

_sampling_unavailable_logged = False


class _StageResult:
    rows = None
    duration_ms = None
    db_calls = None
    heap_samples = None  # list of (elapsed_ms, heap_bytes), only set when sampling is on
    # What kind of heap sampling this stage actually got — always set, so a run never
    # silently claims more than it delivered. One of:
    #   "disabled"      — PERFORMANCE_MEMORY_SAMPLING was off, sampling wasn't attempted
    #   "unavailable"    — sampling was on but nothing could be read at all (no `js`,
    #                       no performance.memory, e.g. Firefox/Safari or pytest)
    #   "single_sample"  — sampling was on but we only ever got the one synchronous
    #                       reading at stage start — i.e. the background thread never
    #                       actually produced a second point (no real concurrency in
    #                       this Pyodide build, or the stage finished before the first
    #                       interval elapsed). Not a time series — treat as a snapshot.
    #   "continuous"     — the background thread genuinely ran alongside the stage and
    #                       produced more than one sample; a real time series.
    sampling_mode = "disabled"


class _HeapSampler:
    """Samples js.performance.memory.usedJSHeapSize on a background thread. """

    def __init__(self, interval_ms: float):
        self.interval_s = max(interval_ms, 1) / 1000.0
        self.samples = []  # (elapsed_ms, heap_bytes)
        self._start = None
        self._stop_event = None
        self._thread = None
        self._available = True
        self.mode = "unavailable"  # set by stop()

    def _sample_once(self):
        import js

        heap = getattr(getattr(js, "performance", None), "memory", None)
        if heap is None:
            return None
        return int(heap.usedJSHeapSize)

    def _run(self):
        # wait() before sampling, a full interval must actually elapse before count        
        while not self._stop_event.wait(self.interval_s):
            try:
                value = self._sample_once()
            except Exception:
                # Chrome-only API,  stop silently if not working
                self._available = False
                return
            if value is not None:
                elapsed_ms = (time.perf_counter() - self._start) * 1000
                self.samples.append((elapsed_ms, value))

    def start(self):
        global _sampling_unavailable_logged
        self._start = time.perf_counter()
        try:
            # sync sample now so we have a data point even if the thread never runs
            value = self._sample_once()
            if value is not None:
                self.samples.append((0.0, value))

            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        except Exception as e:
            self._available = False
            if not _sampling_unavailable_logged:
                logger.debug(f"Heap sampling unavailable ({type(e).__name__}: {e}); timing-only.")
                _sampling_unavailable_logged = True

    def stop(self):
        if self._stop_event is not None:
            self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=0.5)

        if len(self.samples) > 1:
            self.mode = "continuous"
        elif len(self.samples) == 1:
            self.mode = "single_sample"
        else:
            self.mode = "unavailable"


@contextmanager
def measure_stage(stage_name: str, conn=None):
    """Times a pipeline stage and logs one line on exit.

    Usage:
        with measure_stage("extract", conn=conn) as result:
            do_work()
            result.rows = count_rows()  # optional

    Populates result.duration_ms/db_calls/sampling_mode (+heap_samples if sampled).
    """
    start = time.perf_counter()
    calls_before = getattr(conn, "_execute_call_count", None) if conn is not None else None

    sampling_enabled = bool(get_config_value("PERFORMANCE_MEMORY_SAMPLING", default=False))
    sampler = None
    if sampling_enabled:
        interval_ms = get_config_value("PERFORMANCE_MEMORY_SAMPLING_INTERVAL_MS", default=100)
        try:
            interval_ms = float(interval_ms)
        except (TypeError, ValueError):
            interval_ms = 100
        sampler = _HeapSampler(interval_ms)
        sampler.start()

    result = _StageResult()
    result.sampling_mode = "disabled" if not sampling_enabled else "unavailable"
    try:
        yield result
    finally:
        if sampler is not None:
            sampler.stop()
            result.sampling_mode = sampler.mode
            if sampler.samples:
                result.heap_samples = sampler.samples

        duration_ms = (time.perf_counter() - start) * 1000
        result.duration_ms = duration_ms

        parts = [f"stage={stage_name}", f"dur_ms={duration_ms:.1f}"]
        if result.rows is not None:
            parts.append(f"rows={result.rows}")
        if conn is not None and calls_before is not None:
            calls_after = getattr(conn, "_execute_call_count", calls_before)
            result.db_calls = calls_after - calls_before
            parts.append(f"db_calls={result.db_calls}")
        parts.append(f"sampling_mode={result.sampling_mode}")  # always logged, disabled included
        if result.heap_samples:
            parts.append(f"heap_samples={len(result.heap_samples)}")
            parts.append(f"heap_last_bytes={result.heap_samples[-1][1]}")
        logger.info("PERFORMANCE_MEMORY " + " ".join(parts))
