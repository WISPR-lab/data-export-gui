// Builds/downloads `${givenName}_mem_perf.csv` from performance_summary (python_core/run.py).
// One row per stage, plus a leading "after_pyodide_load" row - the memory reading taken once
// Pyodide finished loading but before any pipeline stage ran, so pipeline cost can be told apart
// from Pyodide runtime/package-loading overhead.
//
// Each stage's *_heap_before_bytes / *_heap_after_bytes bracket that stage's own work, so
// *_heap_delta_bytes is that stage's own memory cost - not shifted onto the next row. If a
// background sampling thread was available, *_heap_peak_bytes also captures any intermediate
// high point; the full raw time series (when longer than 2 points) is in the console's
// PERFORMANCE_MEMORY_SUMMARY JSON, not this CSV, to keep this file one-row-per-stage.

const CSV_HEADER = [
  'stage',
  'duration_ms',
  'rows_processed',
  'database_calls',
  'js_sampling_mode', // disabled | unavailable | start_only | start_end_only | continuous - see performance.py
  'js_heap_before_bytes', // Chrome-only, relayed from the main thread (see pyodide-client.js)
  'js_heap_after_bytes',
  'js_heap_delta_bytes', // this stage's own JS heap cost = after - before
  'js_heap_peak_bytes', // highest reading seen during this stage (only exceeds after_bytes if JS GC'd mid-stage)
  'wasm_sampling_mode',
  'wasm_heap_before_bytes', // any browser
  'wasm_heap_after_bytes',
  'wasm_heap_delta_bytes', // this stage's own WASM memory cost = after - before
  'wasm_heap_peak_bytes', // WASM memory only grows, so this always equals after_bytes
  'database_size_before_bytes', // whole-pipeline, repeated on every row so this loads flat into pandas
  'database_size_after_bytes',
  'total_duration_ms',
];

function csvEscape(value) {
  if (value === undefined || value === null) return '';
  const str = String(value);
  if (/[",\n]/.test(str)) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  return str;
}

export function buildPerformanceCsv(summary) {
  const footer = [
    summary.database_size_before_bytes,
    summary.database_size_after_bytes,
    summary.total_duration_ms,
  ];

  const rows = [CSV_HEADER];

  rows.push([
    'after_pyodide_load', '', '', '',
    '', '', summary.after_pyodide_load_js_heap_bytes, '', '',
    '', '', summary.after_pyodide_load_wasm_heap_bytes, '', '',
    ...footer,
  ]);

  for (const stage of summary.stages || []) {
    rows.push([
      stage.stage,
      stage.duration_ms,
      stage.rows_processed,
      stage.database_calls,
      stage.js_sampling_mode,
      stage.js_heap_before_bytes,
      stage.js_heap_after_bytes,
      stage.js_heap_delta_bytes,
      stage.js_heap_peak_bytes,
      stage.wasm_sampling_mode,
      stage.wasm_heap_before_bytes,
      stage.wasm_heap_after_bytes,
      stage.wasm_heap_delta_bytes,
      stage.wasm_heap_peak_bytes,
      ...footer,
    ]);
  }

  return rows.map((row) => row.map(csvEscape).join(',')).join('\n') + '\n';
}

export function downloadPerformanceCsv(givenName, summary) {
  if (!summary) return;
  const csv = buildPerformanceCsv(summary);
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const safeName = (givenName || 'upload').replace(/[^\w.-]+/g, '_');
  const a = document.createElement('a');
  a.href = url;
  a.download = `${safeName}_mem_perf.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
