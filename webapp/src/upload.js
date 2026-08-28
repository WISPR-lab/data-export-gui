import { OPFSManager } from '@/storage/opfs_manager.js';
import { ERROR_TYPES } from '@/constants/error_types';
import DB from '@/database/index.js';
import { executeUpload } from '@/pyodide/pyodide-client.js';
import EventBus from '@/event-bus.js';

import { getLogger } from '@/utils/logger.js';

const logger = getLogger('UploadService');


export async function processUpload(file, platform, givenName, projectId, store) {
  /* Forces DB context to userdata.db, runs the full extract→pipeline→UI-refresh cycle, and cleans up on failure. Returns a summary object. */
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
    logger.debug(`Starting upload process for ${platform} with file: ${file.name}`);
    
    // CRITICAL: Ensure uploads always target userdata.db, never demo.db
    if (store) {
      store.commit('SET_DEMO_MODE', false);
      store.commit('SET_CURRENT_DB', 'userdata');
    }
    logger.debug('Database context set to userdata.db');
    
    const opfsManager = new OPFSManager();
    
    const result = await executeUpload(file, platform, givenName, opfsManager, {
      onProgress: (evt) => {
        logger.debug(`${evt.stage} (${evt.progress}%)`);
        if (store) {
          store.commit('UPDATE_UPLOAD_PROGRESS', { status: evt.stage, progress: evt.progress });
        }
      },
      onError: (evt) => {
        logger.error(`${evt.stage}: ${evt.error}`);
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
    logger.debug('Refreshing UI...');
    if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'complete', progress: 95 });
    
    try {
      const previousIds = ((store.state.project && store.state.project.dataExports) || []).map((de) => de.id);
      const uploads = await DB.getUploads('userdata');
      const virtualProject = {
        id: 1,
        name: 'Local Takeout Workspace',
        description: 'Browser-only processing',
        status: [{ status: 'ready' }],
        dataExports: uploads.uploads || []
      };
      
      const meta = await DB.getEventMeta('userdata');
      store.commit('SET_PROJECT', { objects: [virtualProject], meta });
      const newIds = virtualProject.dataExports
        .map((de) => de.id)
        .filter((id) => !previousIds.includes(id));
      if (newIds.length > 0) {
        store.commit('SET_ENABLED_DATA_EXPORTS', newIds);
      }
      EventBus.$emit('data-export-updated', newIds);
      summary.success = true;
      store.commit('COMPLETE_UPLOAD', summary);
      logger.debug('Upload complete');
    } catch (error) {
      const msg = `Failed to refresh UI: ${error.message}`;
      summary.errors.push(msg);
      summary.warnings.push('Data uploaded but UI refresh failed. Try reloading.');
      if (store) store.commit('COMPLETE_UPLOAD', summary);
    }
    
  } catch (error) {
    logger.error('Upload failed:', error);
    summary.errors.push(error.message);
    summary.errorType = error.errorType || ERROR_TYPES.PARSER_ERROR;
    if (error.uploadId) {
      logger.debug(`Cleaning up failed upload data for ID: ${error.uploadId}`);
      try {
        await DB.deleteUpload(error.uploadId);
      } catch (deleteError) {
        logger.error(`Failed to clean up upload data: ${deleteError.message}`);
      }
    }
    if (store) store.commit('FAIL_UPLOAD', summary);
  } finally {
    summary.processingTimeMs = Date.now() - startTime;
    logger.debug(`Upload completed in ${summary.processingTimeMs}ms`);
  }
  
  return summary;
}
