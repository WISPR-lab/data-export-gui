// Builds/downloads `${givenName}_mem_perf.csv` from performance_summary (python_core/run.py).
// One row per stage, or per sample tick per stage when sampling is on — js/wasm heap
// readings share a row since they're sampled together each tick (see _MemorySampler).

const CSV_HEADER = [
  'stage',
  'duration_ms',
  'rows_processed',
  'database_calls',
  'js_sampling_mode', // disabled | unavailable | single_sample | continuous — see performance.py
  'wasm_sampling_mode',
  'sample_index',
  'elapsed_ms',
  'js_heap_bytes', // Chrome-only
  'wasm_heap_bytes', // any browser
  'database_size_before_bytes',
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
  const rows = [CSV_HEADER];
  const footer = [
    summary.database_size_before_bytes,
    summary.database_size_after_bytes,
    summary.total_duration_ms,
  ];

  for (const stage of summary.stages || []) {
    const base = [
      stage.stage,
      stage.duration_ms,
      stage.rows_processed,
      stage.database_calls,
      stage.js_sampling_mode,
      stage.wasm_sampling_mode,
    ];
    const jsSamples = stage.js_heap_samples || [];
    const wasmSamples = stage.wasm_heap_samples || [];
    const sampleCount = Math.max(jsSamples.length, wasmSamples.length);

    if (sampleCount === 0) {
      rows.push([...base, '', '', '', '', ...footer]);
      continue;
    }
    for (let i = 0; i < sampleCount; i++) {
      const js = jsSamples[i];
      const wasm = wasmSamples[i];
      const elapsedMs = (js || wasm).elapsed_ms;
      rows.push([...base, i, elapsedMs, js ? js.heap_bytes : '', wasm ? wasm.heap_bytes : '', ...footer]);
    }
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
