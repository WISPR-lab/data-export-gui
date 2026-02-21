let pyodideWorker = null;
let workerMessageId = 0;


export function getPyodideWorker() {
  if (!pyodideWorker) {
    // Use relative path that works with publicPath
    pyodideWorker = new Worker('./pyodide-worker.js');
    console.log('[PyodideClient] Created Pyodide worker (singleton)');
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
