import { OPFSManager } from '@/storage/opfs_manager.js';
import { classifyError, ERROR_TYPES } from '@/constants/error_types';
import DB from '@/database/index.js';
import { callPyodideWorker } from '@/pyodide/pyodide-client.js';

const DEBUG_LOGGING = true;

function log(...args) {
  if (DEBUG_LOGGING) { console.log('[UploadService]', ...args); }
}

function logError(...args) { console.error('[UploadService]', ...args); }


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
    if (store) store.commit('START_UPLOAD', file.name);
    log(`Starting upload process for ${platform} platform with file: ${file.name}`);
    
    // Step 1: Extract ZIP to OPFS
    log('Step 1: Extracting ZIP to OPFS...');
    if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'validating', progress: 10 });
    
    const opfsManager = new OPFSManager();
    try {
      await opfsManager.processZipUpload(file, platform);
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
      const extractResult = await callPyodideWorker('extract', {platform, givenName: file.name});
      if (extractResult.status !== 'success') {
        const errMsg = extractResult.error || 'Extraction failed';
        console.error('[UploadService] Extractor returned failure:', errMsg);
        throw new Error(errMsg);
    }
      uploadId = extractResult.upload_id;
      if (!uploadId) {
        logError('Extractor did not return an upload ID');
        throw new Error('Extractor did not return an upload ID');
      }
      log(`Extraction complete. Upload ID: ${uploadId}`);
    } catch (error) {
      await DB.getDB();
      const msg = `Python extraction error: ${error.message}`;
      summary.errors.push(msg);
      summary.errorType = error.errorType || ERROR_TYPES.PARSER_ERROR;
      if (store) store.commit('FAIL_UPLOAD', summary);
      return summary;
    }

    // Step 3 Clean up OPFS temp files — no longer needed after extraction
    log('Step 3: Cleaning up OPFS temp files...');
    try {
      await opfsManager.clearTempStorage();
      log('OPFS temp files cleared');
    } catch (error) {
      log(`Warning: failed to clear OPFS temp files: ${error.message}`);
      summary.warnings.push('Temp files may not have been cleaned up from local storage.');
    }
    
    // Step 3: Call Python semantic mapper
    log('Step 3: Running Python semantic mapper...');
    if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'inserting', progress: 60 });
    
    try {
      if (!uploadId) {
        throw new Error('Upload ID not available for semantic mapping');
      }
      
      const mapResult = await callPyodideWorker('semantic_map', { 
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
    console.error('[UploadService] Unexpected error during upload process:', error);
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
