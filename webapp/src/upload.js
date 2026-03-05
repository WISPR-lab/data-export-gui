import { OPFSManager } from '@/storage/opfs_manager.js';
import { classifyError, ERROR_TYPES } from '@/constants/error_types';
import DB from '@/database/index.js';
import { executeUpload } from '@/pyodide/pyodide-client.js';

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
    log(`Starting upload process for ${platform} with file: ${file.name}`);
    
    const opfsManager = new OPFSManager();
    
    const result = await executeUpload(file, platform, opfsManager, {
      onProgress: (evt) => {
        log(`${evt.stage} (${evt.progress}%)`);
        if (store) {
          store.commit('UPDATE_UPLOAD_PROGRESS', { status: evt.stage, progress: evt.progress });
        }
      },
      onError: (evt) => {
        logError(`${evt.stage}: ${evt.error}`);
      }
    });

    summary.totalEventsAdded = result.events_count;
    summary.totalStatesAdded = result.devices_count;
    
    if (result.partial_errors && result.partial_errors.length) {
      result.partial_errors.forEach(e => {
        if (e.level === 'error') {
          summary.warnings.push(`Skipped "${e.file}": ${e.msg}`);
        }
      });
    }

    // Update UI store
    log('Refreshing UI...');
    if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'complete', progress: 95 });
    
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
      summary.warnings.push('Data uploaded but UI refresh failed. Try reloading.');
      if (store) store.commit('COMPLETE_UPLOAD', summary);
    }
    
  } catch (error) {
    console.error('[UploadService] Upload failed:', error);
    summary.errors.push(error.message);
    summary.errorType = error.errorType || ERROR_TYPES.PARSER_ERROR;
    if (store) store.commit('FAIL_UPLOAD', summary);
  } finally {
    summary.processingTimeMs = Date.now() - startTime;
    log(`Upload completed in ${summary.processingTimeMs}ms`);
  }
  
  return summary;
}
