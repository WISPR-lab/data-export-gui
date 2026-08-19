// Builds/downloads `${givenName}_mem_perf.csv` from performance_summary (python_core/run.py).
// One row per stage, or per heap sample per stage when sampling is on.

const CSV_HEADER = [
  'stage',
  'duration_ms',
  'rows_processed',
  'database_calls',
  'sampling_mode', // disabled | unavailable | single_sample | continuous — see performance.py
  'sample_index',
  'elapsed_ms',
  'heap_bytes',
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
      stage.sampling_mode,
    ];
    if (stage.heap_samples && stage.heap_samples.length) {
      stage.heap_samples.forEach((sample, i) => {
        rows.push([...base, i, sample.elapsed_ms, sample.heap_bytes, ...footer]);
      });
    } else {
      rows.push([...base, '', '', '', ...footer]);
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
