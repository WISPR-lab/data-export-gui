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

export function callPyodideWorker(command, args) {
  return new Promise((resolve, reject) => {
    const worker = getPyodideWorker();
    const id = workerMessageId++;
    const handler = (event) => {
      if (event.data.id === id) {
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

function postToWorker(command, args) {
  return new Promise((resolve, reject) => {
    const worker = getPyodideWorker();
    const id = workerMessageId++;
    const timeout = setTimeout(() => {
      worker.removeEventListener('message', handler);
      reject(new Error(`Worker timeout on ${command}`));
    }, 60000);
    const handler = (event) => {
      if (event.data.id === id) {
        clearTimeout(timeout);
        worker.removeEventListener('message', handler);
        if (event.data.success) {
          resolve(event.data.result);
        } else {
          const error = new Error(event.data.error);
          error.errorType = event.data.errorType || 'UNKNOWN_ERROR';
          reject(error);
        }
      }
    };
    worker.addEventListener('message', handler);
    worker.postMessage({ id, command, args });
  });
}

export async function executeUpload(file, platform, opfsManager, callbacks = {}) {
  const { onProgress, onError } = callbacks;
  let uploadId;

  try {
    // Step 1: ZIP extraction (JS side)
    if (onProgress) onProgress({ stage: 'extract_zip', progress: 15 });
    await opfsManager.init(platform);
    await opfsManager.processZipUpload(file, platform);

    // Step 2: Extract data from ZIP
    if (onProgress) onProgress({ stage: 'extract', progress: 30 });
    const extractResult = await postToWorker('extract', { platform, givenName: file.name });
    if (extractResult.status !== 'success') {
      throw new Error(extractResult.error || 'Extract failed');
    }
    uploadId = extractResult.upload_id;
    if (!uploadId) throw new Error('No upload ID returned');

    // Step 2.5: Semantic mapping
    if (onProgress) onProgress({ stage: 'semantic_map', progress: 40 });
    const mapResult = await postToWorker('semantic_map', { platform, uploadId });
    if (mapResult.status !== 'success') {
      throw new Error(mapResult.error || 'Semantic mapping failed');
    }

    // Step 3: Normalize fields
    if (onProgress) onProgress({ stage: 'normalize', progress: 60 });
    const normalizeResult = await postToWorker('normalize', { uploadId });
    if (normalizeResult.status !== 'success') {
      throw new Error(normalizeResult.error || 'Normalize failed');
    }

    // Step 4: Device grouping
    if (onProgress) onProgress({ stage: 'group', progress: 85 });
    const groupResult = await postToWorker('group', { uploadId });
    if (groupResult.status !== 'success') {
      throw new Error(groupResult.error || 'Device grouping failed');
    }

    // Step 6: Cleanup OPFS
    if (onProgress) onProgress({ stage: 'cleanup', progress: 90 });
    await opfsManager.clearTempStorage();

    return {
      success: true,
      uploadId,
      events_count: mapResult.events_count || 0,
      devices_count: mapResult.devices_count || 0,
      partial_errors: extractResult.partial_errors || []
    };
  } catch (error) {
    const errorMsg = error.message || String(error);
    if (onError) onError({ stage: uploadId ? 'processing' : 'extract', error: errorMsg, uploadId });
    throw error;
  }
}
