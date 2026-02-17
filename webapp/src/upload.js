import { OPFSManager } from '@/storage/opfs_manager.js';
import { classifyError, ERROR_TYPES } from '@/constants/error_types';
import DB from '@/database/index.js';

const DEBUG_LOGGING = true;

// Singleton: Create worker only once, reuse across all imports
let pyodideWorker = null;
function getPyodideWorker() {
  if (!pyodideWorker) {
    pyodideWorker = new Worker('/pyodideWorker.js');
    console.log('[UploadService] Created Pyodide worker (singleton)');
  }
  return pyodideWorker;
}

let workerMessageId = 0;

function log(...args) {
  if (DEBUG_LOGGING) { console.log('[UploadService]', ...args); }
}

function logError(...args) { console.error('[UploadService]', ...args); }

/**
 * sends a command to the Pyodide Worker
 * 
 * @returns {Promise<{result, errorType?, source?}>} Worker response
 */
function callWorker(command, args) {
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
          error.errorType = event.data.errorType || classifyError(event.data.error, event.data.source);
          error.source = event.data.source || 'worker';
          reject(error);
        }
      }
    };
    worker.addEventListener('message', handler);
    worker.postMessage({ id, command, args });
  });
}

/**
 * Terminate the Pyodide worker (for safe exit)
 */
export function terminateWorker() {
  if (pyodideWorker) {
    pyodideWorker.terminate();
    pyodideWorker = null;
    console.log('[UploadService] Worker terminated');
  }
}

/**
 * Main upload and processing function
 * 
 * Flow:
 * 1. Extract ZIP to OPFS
 * 2. Call Python extractor worker (parse files → raw_data table)
 * 3. Call Python semantic mapper (raw_data → events table)
 * 4. Refresh UI
 * 
 * returns summary with optional errorType field for UI classification:
 * - errorType: string (one of ERROR_TYPES) - helps UI show appropriate message
 * - errors: array of strings - individual errors encountered
 */
export async function processUpload(file, platform, sketchId, store) {
  const startTime = Date.now();
  const summary = {
    success: false,
    platform,
    totalEventsAdded: 0,
    totalStatesAdded: 0,
    errors: [],
    errorType: null,
    warnings: [],
    processingTimeMs: 0
  };

  try {
    if (store) {
      store.commit('START_UPLOAD', file.name);
    }
    
    log(`Starting upload process for ${platform} platform with file: ${file.name}`);
    
    // Step 1: Extract ZIP to OPFS
    log('Step 1: Extracting ZIP to OPFS...');
    if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'validating', progress: 10 });
    
    const opfsManager = new OPFSManager();
    try {
      await opfsManager.processZipUpload(file);
      log('ZIP extraction complete');
    } catch (error) {
      const msg = `Failed to extract ZIP: ${error.message}`;
      summary.errors.push(msg);
      if (store) store.commit('FAIL_UPLOAD', { errors: [msg], errorType: ERROR_TYPES.FILE_ERROR });
      return summary;
    }
    
    // Step 2: Call Python extractor worker
    log('Step 2: Running Python extractor...');
    if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'parsing', progress: 30 });
    
    let uploadId;
    try {
      const extractResult = await callWorker('extract', { 
        platform, 
        givenName: file.name 
      });
      
      if (extractResult.status !== 'success') {
        throw new Error(extractResult.error || 'Extraction failed');
      }
      
      uploadId = extractResult.upload_id;
      log(`Extraction complete. Upload ID: ${uploadId}`);
    } catch (error) {
      const msg = `Python extraction error: ${error.message}`;
      summary.errors.push(msg);
      summary.errorType = error.errorType || ERROR_TYPES.PARSER_ERROR;
      if (store) store.commit('FAIL_UPLOAD', summary);
      return summary;
    }
    
    // Step 3: Call Python semantic mapper
    log('Step 3: Running Python semantic mapper...');
    if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'inserting', progress: 60 });
    
    try {
      const mapResult = await callWorker('semantic_map', { 
        platform, 
        uploadId 
      });
      
      if (mapResult.status !== 'success') {
        throw new Error(mapResult.error || 'Semantic mapping failed');
      }
      
      summary.totalEventsAdded = mapResult.events_count || 0;
      summary.totalStatesAdded = mapResult.devices_count || 0;
      log(`Semantic mapping complete. ${summary.totalEventsAdded} events, ${summary.totalStatesAdded} devices`);
    } catch (error) {
      const msg = `Python semantic mapping error: ${error.message}`;
      summary.errors.push(msg);
      summary.errorType = error.errorType || ERROR_TYPES.DATABASE_ERROR;
      if (store) store.commit('FAIL_UPLOAD', summary);
      return summary;
    }
    
    // Step 4: Update UI store
    log('Step 4: Refreshing UI...');
    if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'complete', progress: 90 });
    
    try {
      const uploads = await DB.getUploads();
      const virtualSketch = {
        id: 1,
        name: 'Local Takeout Workspace',
        description: 'Browser-only processing',
        status: [{ status: 'ready' }],
        timelines: uploads.objects || []
      };
      
      const meta = await DB.getEventMeta();
      store.commit('SET_SKETCH', { objects: [virtualSketch], meta });
      
      summary.success = true;
      store.commit('COMPLETE_UPLOAD', summary);
      log('Upload complete');
    } catch (error) {
      const msg = `Failed to refresh UI: ${error.message}`;
      summary.errors.push(msg);
      summary.warnings.push('Data uploaded but UI refresh failed. Try reloading the page.');
      if (store) store.commit('COMPLETE_UPLOAD', summary);
    }
    
  } catch (error) {
    summary.errors.push(`Unexpected error: ${error.message}`);
    if (!summary.errorType) {
      summary.errorType = error.errorType || ERROR_TYPES.UNKNOWN_ERROR;
    }
    if (store) store.commit('FAIL_UPLOAD', summary);
  } finally {
    summary.processingTimeMs = Date.now() - startTime;
    log(`Upload process completed in ${summary.processingTimeMs}ms`);
  }
  
  return summary;
}
