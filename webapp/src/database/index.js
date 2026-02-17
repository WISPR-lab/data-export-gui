// custom to WISPR-lab/data-export-gui

import * as events from './queries/events.js';
import * as uploads from './queries/uploads.js';
import * as comments from './queries/comments.js';
import * as metadata from './queries/metadata.js';
import yaml from 'js-yaml';

let db = null;
let worker = null;
let initPromise = null;
let messageId = 0;
let config = null;

async function loadConfig() {
  if (config) return config;
  
  try {
    const response = await fetch('/config.yaml');
    const yamlText = await response.text();
    config = yaml.load(yamlText);
    console.log('[Database] Config loaded:', config);
    return config;
  } catch (error) {
    console.error('[Database] Failed to load config.yaml, using defaults:', error);
    config = {
      database: {
        db_path: '/mnt/data/timeline.db',
        schema_path: '/python_core/database/schema.sql',
        batch_size: 500
      },
      storage: {
        temp_zip_storage: '/mnt/data/tmpstore',
        manifests_dir: '/manifests'
      }
    };
    return config;
  }
}

function callWorker(method, args) {
  return new Promise((resolve, reject) => {
    const id = messageId++;
    const handler = (e) => {
      if (e.data.id === id) {
        worker.removeEventListener('message', handler);
        if (e.data.error) {
          const err = new Error(e.data.error.message);
          err.name = e.data.error.name;
          err.stack = e.data.error.stack;
          reject(err);
        } else {
          resolve(e.data.result);
        }
      }
    };
    worker.addEventListener('message', handler);
    worker.postMessage({ id, method, args });
  });
}

export async function getDB() {
  if (db) return db;
  
  if (!initPromise) {
    initPromise = (async () => {
      console.log('[Database] Starting worker with OPFS...');
      
      const cfg = await loadConfig();
      
      worker = new Worker('/sqliteWorker.js');
      
      await callWorker('init', { dbPath: cfg.database.db_path });
      console.log('[Database] Database ready');
      
      return {
        exec(sql, options) {
          return callWorker('exec', { sql, options });
        },
        close() {
          return callWorker('close');
        }
      };
    })();
  }
  
  db = await initPromise;
  return db;
}

export async function closeDB() {
  if (db) {
    await db.close();
    if (worker) {
      worker.terminate();
      worker = null;
    }
    db = null;
    initPromise = null;
    console.log('[Database] Connection closed');
  }
}

export default {
  getDB,
  closeDB,
  
  searchEvents: events.searchEvents,
  getEventCount: events.getEventCount,
  getCategories: events.getCategories,
  deleteEvents: events.deleteEvents,
  addLabelEvent: events.addLabelEvent,
  removeLabelEvent: events.removeLabelEvent,
  updateEventTags: events.updateEventTags,
  
  getUploads: uploads.getUploads,
  getUploadById: uploads.getUploadById,
  updateUpload: uploads.updateUpload,
  deleteUpload: uploads.deleteUpload,
  
  getEventComments: comments.getEventComments,
  addEventComment: comments.addEventComment,
  updateEventComment: comments.updateEventComment,
  deleteEventComment: comments.deleteEventComment,
};
