"""Per-stage timing for the pipeline (run.py).

Logs one line per stage:

    PERFORMANCE_MEMORY stage=<name> dur_ms=<float> rows=<int> db_calls=<int>

`db_calls` requires a `conn` whose execute/executemany are call-counted
(DatabaseSession._wrap_execute_counting, see db_session.py).

When PERFORMANCE_MEMORY_SAMPLING is on (see builtins, injected by
pyodide-worker.js from config.yaml's performance.memory_sampling_enabled),
each stage also gets a before/after memory reading from two sources:
  js:   relayed from the main thread's performance.memory.usedJSHeapSize —
        Chrome-only, and only reachable via relay because performance.memory
        does not exist inside a dedicated Worker (this pipeline's execution
        context), only on window. See getJsHeapBytes in pyodide-worker.js
        and the postMessage sender in pyodide-client.js.
  wasm: js.getWasmMemoryBytes() (pyodide._module.HEAP8.buffer.byteLength,
        pyodide-worker.js) — works in any browser, no relay needed.

A source always gets a reading at stage-start and stage-end even when no
real background thread is available (see _MemorySampler.stop) — that's the
"start_end_only" sampling_mode. If a background thread *is* available it adds
real in-between readings too ("continuous"). Each source downgrades
independently; see sampling_mode."""
import threading
import time
from contextlib import contextmanager

from python_core.logger import get_logger
from python_core.runtime.pyodide_utils import get_config_value

logger = get_logger("performance")

_sampling_unavailable_logged = False


def _read_js_heap():
    import js
    getter = getattr(js, "getJsHeapBytes", None)
    if getter is None:
        return None
    value = getter()
    return int(value) if value is not None else None


def _read_wasm_heap():
    import js
    return int(js.getWasmMemoryBytes())


_MEMORY_SOURCES = {
    "js": _read_js_heap,
    "wasm": _read_wasm_heap,
}


class _StageResult:
    rows = None
    duration_ms = None
    db_calls = None

    js_sampling_mode = "disabled"
    js_heap_before_bytes = None
    js_heap_after_bytes = None
    js_heap_delta_bytes = None
    js_heap_peak_bytes = None
    js_heap_samples = None  # raw [(elapsed_ms, bytes), ...] - only len()>2 when a background thread ran

    wasm_sampling_mode = "disabled"
    wasm_heap_before_bytes = None
    wasm_heap_after_bytes = None
    wasm_heap_delta_bytes = None
    wasm_heap_peak_bytes = None
    wasm_heap_samples = None


def read_after_pyodide_load() -> dict:
    """One-off reading of each source, taken once after Pyodide finishes loading and before
    the pipeline's first stage runs - the reference point stage deltas should be read against."""
    reading = {}
    for name, reader in _MEMORY_SOURCES.items():
        try:
            value = reader()
        except Exception:
            value = None
        reading[f"{name}_heap_bytes"] = value
    logged = " ".join(f"{k}={v}" for k, v in reading.items() if v is not None)
    if logged:
        logger.info("PERFORMANCE_MEMORY_AFTER_PYODIDE_LOAD " + logged)
    return reading


class _MemorySampler:
    """Samples all _MEMORY_SOURCES together, once per tick, on one background thread.
    Always guarantees a reading at start() and stop() regardless of whether the thread
    actually ran, so every stage gets a real before/after pair even in Pyodide builds
    without real thread support."""

    def __init__(self, interval_ms: float):
        self.interval_s = max(interval_ms, 1) / 1000.0
        self.samples = {name: [] for name in _MEMORY_SOURCES}  # name -> [(elapsed_ms, bytes)]
        self._dead = set()  # sources that raised errors, stop retrying
        self._start = None
        self._stop_event = None
        self._thread = None

    def _sample_all(self):
        for name, reader in _MEMORY_SOURCES.items():
            if name in self._dead:
                continue
            try:
                value = reader()
            except Exception:
                self._dead.add(name)
                continue
            if value is not None:
                elapsed_ms = (time.perf_counter() - self._start) * 1000
                self.samples[name].append((elapsed_ms, value))

    def _run(self):
        # wait() before sampling - a full interval must actually elapse before it counts.
        while not self._stop_event.wait(self.interval_s):
            self._sample_all()

    def start(self):
        global _sampling_unavailable_logged
        self._start = time.perf_counter()
        self._sample_all()  # "before" reading - guaranteed even if the thread never runs
        try:
            self._stop_event = threading.Event()
            thread = threading.Thread(target=self._run, daemon=True)
            thread.start()
            self._thread = thread  # only publish once start() actually succeeds
        except Exception as e:
            self._thread = None  # never started - stop() must not try to join it
            if not _sampling_unavailable_logged:
                logger.debug(f"Background memory sampling unavailable ({type(e).__name__}: {e}); start_end_only only.")
                _sampling_unavailable_logged = True

    def stop(self):
        if self._stop_event is not None:
            self._stop_event.set()
        self._sample_all()  # "after" reading - guaranteed even if no thread ran or added no samples
        if self._thread is not None:
            self._thread.join(timeout=0.5)

    def mode(self, name):
        n = len(self.samples[name])
        if n >= 3:
            return "continuous"  # background thread added real in-between readings
        if n == 2:
            return "start_end_only"  # only the guaranteed start+end readings
        if n == 1:
            return "start_only"  # source died between the start and end readings
        return "unavailable"


@contextmanager
def measure_stage(stage_name: str, conn=None):
    """Times a pipeline stage and logs one line on exit.

    Usage:
        with measure_stage("extract", conn=conn) as result:
            do_work()
            result.rows = count_rows()  # optional

    Populates result.duration_ms/db_calls + per-source js_*/wasm_* fields
    (sampling_mode, before/after/delta/peak bytes, raw samples).
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
        sampler = _MemorySampler(interval_ms)
        sampler.start()

    result = _StageResult()
    try:
        yield result
    finally:
        if sampler is not None:
            sampler.stop()
            for name in _MEMORY_SOURCES:
                samples = sampler.samples[name]
                setattr(result, f"{name}_sampling_mode", sampler.mode(name))
                if samples:
                    values = [v for _, v in samples]
                    setattr(result, f"{name}_heap_samples", samples)
                    setattr(result, f"{name}_heap_before_bytes", values[0])
                    setattr(result, f"{name}_heap_after_bytes", values[-1])
                    setattr(result, f"{name}_heap_delta_bytes", values[-1] - values[0])
                    setattr(result, f"{name}_heap_peak_bytes", max(values))

        duration_ms = (time.perf_counter() - start) * 1000
        result.duration_ms = duration_ms

        parts = [f"stage={stage_name}", f"dur_ms={duration_ms:.1f}"]
        if result.rows is not None:
            parts.append(f"rows={result.rows}")
        if conn is not None and calls_before is not None:
            calls_after = getattr(conn, "_execute_call_count", calls_before)
            result.db_calls = calls_after - calls_before
            parts.append(f"db_calls={result.db_calls}")
        for name in _MEMORY_SOURCES:  # always logged, disabled included
            mode = getattr(result, f"{name}_sampling_mode")
            parts.append(f"{name}_sampling_mode={mode}")
            before = getattr(result, f"{name}_heap_before_bytes")
            after = getattr(result, f"{name}_heap_after_bytes")
            if before is not None:
                parts.append(f"{name}_heap_before_bytes={before}")
                parts.append(f"{name}_heap_after_bytes={after}")
                parts.append(f"{name}_heap_delta_bytes={after - before}")
        logger.info("PERFORMANCE_MEMORY " + " ".join(parts))
