let pyodideWorker = null;
let workerMessageId = 0;


export function getPyodideWorker() {
  if (!pyodideWorker) {
    pyodideWorker = new Worker('./pyodide-worker.js');
    console.log('[PyodideClient] Created Pyodide worker (singleton)');
    pyodideWorker.addEventListener('message', (event) => {
      if (event.data.type === 'packageInstallFailure') {
        console.error('[PyodideClient] Packages failed to install in Pyodide:', event.data.packages);
      }
    });
  }
  return pyodideWorker;
}

export function callPyodideWorker(command, args, onProgress, timeoutMs) {
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


export function terminatePyodideWorker() {
  if (pyodideWorker) {
    pyodideWorker.terminate();
    pyodideWorker = null;
    console.log('[PyodideClient] Worker terminated');
  }
}


export async function executeUpload(file, platform, opfsManager, callbacks) {
  const cb = callbacks || {};
  const onProgress = cb.onProgress;
  const onError = cb.onError;
  let uploadId;

  try {
    // Step 1: ZIP extraction (JS side)
    if (onProgress) onProgress({ stage: 'extract_zip', progress: 15 });
    await opfsManager.init(platform);
    await opfsManager.processZipUpload(file, platform);

    // Consolidated Step: Run entire pipeline in Pyodide (extract, semantic map, normalize, group)
    const result = await callPyodideWorker('run_pipeline', { platform, givenName: file.name }, onProgress);
    uploadId = result.upload_id;

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
