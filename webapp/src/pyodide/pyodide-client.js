import { getLogger } from '@/utils/logger';
import { downloadPerformanceCsv } from '@/utils/performanceExport';
import { loadConfig } from '@/utils/config';

const logger = getLogger('PyodideClient');
let pyodideWorker = null;
let workerMessageId = 0;


let isPyodideReady = false;

export function getPyodideWorker() {
  if (!pyodideWorker) {
    pyodideWorker = new Worker('./pyodide-worker.js');
    logger.debug('Created Pyodide worker (singleton)');
    pyodideWorker.addEventListener('message', (event) => {
      if (event.data && event.data.type === 'packageInstallFailure') {
        logger.error('Packages failed to install in Pyodide:', event.data.packages);
      } else if (event.data && event.data.type === 'pyodide_ready') {
        isPyodideReady = true;
        logger.debug('Pyodide worker initialized and ready');
      }
    });
  }
  return pyodideWorker;
}

export function callPyodideWorker(command, args, onProgress, timeoutMs) {
  /* Routes progress events to onProgress callback; rejects with WORKER_TIMEOUT errorType if timeoutMs elapses (default 60s, 0 disables). */
  const timeoutVal = timeoutMs === undefined ? 60000 : timeoutMs;
  return new Promise((resolve, reject) => {
    const worker = getPyodideWorker();
    const id = workerMessageId++;
    
    let timer = null;
    if (timeoutVal > 0) {
      timer = setTimeout(() => {
        worker.removeEventListener('message', handler);
        const error = new Error(`Worker timeout on ${command}`);
        error.errorType = 'WORKER_TIMEOUT';
        reject(error);
      }, timeoutVal);
    }

    const handler = (event) => {
      if (event.data.id === id) {
        if (event.data.type === 'progress') {
          if (onProgress) {
            onProgress({ stage: event.data.stage, progress: event.data.progress });
          }
          return;
        }

        if (timer) clearTimeout(timer);
        worker.removeEventListener('message', handler);
        if (event.data.success) {
          resolve(event.data.result);
        } else {
          const error = new Error(event.data.error);
          error.errorType = event.data.errorType || 'UNKNOWN_ERROR';
          error.source = event.data.source || 'worker';
          reject(error);
        }
      }
    };
    worker.addEventListener('message', handler);
    worker.postMessage({ id, command, args });
  });
}


async function startJsHeapRelay() {
  /* performance.memory only exists on window, not inside pyodide-worker.js's dedicated Worker -
     so relay it in from here on an interval while a run is in flight. Returns the interval
     handle (or null if sampling is off / this browser doesn't expose performance.memory at all,
     e.g. Firefox/Safari) so the caller can clearInterval() it when the run finishes. */
  let config;
  try {
    config = await loadConfig();
  } catch (e) {
    return null;
  }
  const perf = window.performance;
  if (!config.performance || !config.performance.memory_sampling_enabled || !perf || !perf.memory) {
    return null;
  }
  const worker = getPyodideWorker();
  const send = () => worker.postMessage({ type: 'jsHeapSample', bytes: perf.memory.usedJSHeapSize });
  send(); // seed immediately - don't make the pipeline's first stage wait a full interval for a reading
  return setInterval(send, config.performance.memory_sampling_interval_ms || 100);
}

export function terminatePyodideWorker() {
  if (pyodideWorker) {
    pyodideWorker.terminate();
    pyodideWorker = null;
    logger.debug('Worker terminated');
  }
}


export async function executeUpload(file, platform, givenName, opfsManager, callbacks) {
  /* Orchestrates ZIP→OPFS extraction (JS side), then delegates extract/map/normalize/group to Pyodide, then cleans temp storage. Attaches uploadId to errors for upstream cleanup. */
  const cb = callbacks || {};
  const onProgress = cb.onProgress;
  const onError = cb.onError;
  let uploadId;

  try {
    // Step 0: Notify Pyodide startup if worker is still booting
    if (!isPyodideReady && onProgress) {
      onProgress({ stage: 'init_pyodide', progress: 5 });
    }

    // Step 1: ZIP extraction (JS side)
    if (onProgress) onProgress({ stage: 'extract_zip', progress: 15 });
    await opfsManager.init(platform);
    await opfsManager.processZipUpload(file, platform);

    // Consolidated Step: Run entire pipeline in Pyodide (extract, semantic map, normalize, group)
    const jsHeapRelayTimer = await startJsHeapRelay();
    let result;
    try {
      // no timeout atm... todo
      result = await callPyodideWorker('run_pipeline', { platform, givenName: givenName || file.name }, onProgress, 0);
    } finally {
      if (jsHeapRelayTimer) clearInterval(jsHeapRelayTimer);
    }
    uploadId = result.upload_id;

    if (result.performance_summary && typeof process !== 'undefined' && process.env && process.env.VUE_APP_EXPORT_PERF_CSV === 'true') {
      try {
        downloadPerformanceCsv(givenName || file.name, result.performance_summary);
      } catch (e) {
        logger.warn('Failed to download performance CSV:', e);
      }
    }

    // Step 6: Cleanup OPFS
    if (onProgress) onProgress({ stage: 'cleanup', progress: 90 });
    await opfsManager.clearTempStorage();

    return {
      success: true,
      uploadId,
      events_count: result.events_count || 0,
      devices_count: result.devices_count || 0,
      partial_errors: result.partial_errors || []
    };
  } catch (error) {
    const errorMsg = error.message || String(error);
    if (onError) onError({ stage: uploadId ? 'processing' : 'extract', error: errorMsg, uploadId });
    if (uploadId) {
      error.uploadId = uploadId;
    }
    throw error;
  }
}
