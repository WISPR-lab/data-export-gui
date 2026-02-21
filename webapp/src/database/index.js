// custom to WISPR-lab/data-export-gui

import * as events from './queries/events.js';
import * as uploads from './queries/uploads.js';
import * as comments from './queries/comments.js';
import * as metadata from './queries/metadata.js';
import { loadConfig } from '../utils/config.js';


let worker = null;
let messageId = 0;

function callPyodideWorker(method, args) {
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
  if (!worker) {
    console.log('[Database] Initializing stateless sqlite-worker...');
    // Use relative path that works with publicPath
    worker = new Worker('./sqlite-worker.js');
    window.dbWorker = worker; // debug
  }


  return {
    exec(sql, options) {
      return callPyodideWorker('exec', { 
        sql, 
        options: options || {},
        schemaPath: './schema.sql' // attached so worker can self-heal TODO FIX HARDCODING IN CONFIG
      });
    }
  }
};

/*
  if (db) return db;
  
  if (!initPromise) {
    initPromise = (async () => {
      console.log('[Database] Starting worker with OPFS...');
      
      const cfg = await loadConfig();

      // OpfsDb interprets the path as an OPFS-internal virtual path.
      // config.database.db_path is "/mnt/data/timeline.db" (a Pyodide mount path),
      // but OpfsDb would create literal "mnt/data/" dirs inside OPFS root.
      // Extract just the filename so the DB sits at (root)/timeline.db,
      // which Pyodide (mounting OPFS root at /mnt/data) sees as /mnt/data/timeline.db.
      const dbFilename = cfg.database.db_path.split('/').pop(); // "timeline.db"
      
      worker = new Worker('./sqlite-worker.js');
      window.dbWorker = worker;
      
      await callPyodideWorker('init', { 
        dbPath: "/timeline.db",  // TODO FIX HARDCODING IN CONFIG
        schemaPath: cfg.paths.schema
      });
      console.log('[Database] Database ready');
      
      const tables = await callPyodideWorker('exec', { 
        sql: "SELECT name FROM sqlite_master WHERE type='table';", 
        options: {returnValue: 'resultRows', rowMode: 'object'}});
      
      const tableNames = (tables && tables.length > 0) 
        ? tables.map(function(row) { return row.name; }).join(', ') 
        : 'None';
      
      console.log('[Database] Existing tables:', tableNames);

      
      return {
        exec(sql, options) {
          return callPyodideWorker('exec', { sql, options: options || {} });
        },
        close() {
          return callPyodideWorker('close');
        }
      };
    })();
  }
  
  db = await initPromise;
  return db;
}*/

export async function closeDB() {
  if (worker) {
    worker.terminate();
    worker = null;
    console.log('[Database] Connection closed, sqlite-worker thread terminated');
  }
  // if (db) {
  //   await db.close();
  //   if (worker) {
  //     worker.terminate();
  //     worker = null;
  //   }
  //   db = null;
  //   initPromise = null;
  //   console.log('[Database] Connection closed');
  // }
}

export async function clearAllTables() {
  const db = await getDB();
  const tables = [
    'uploads', 
    'uploaded_files', 
    'raw_data', 
    'events', 
    'auth_devices_initial', 
    'event_comments'
  ];
  
  for (const table of tables) {
    await db.exec(`DELETE FROM ${table};`);
  }
  console.log('[Database] All imported data rows have been cleared.');
}



export default {
  getDB,
  closeDB,
  clearAllTables,
  
  searchEvents: events.searchEvents,
  getEventCount: events.getEventCount,
  // Note: Frontend uses getEventActions (event_action field), not getCategories (event_category field)
  getEventActions: events.getEventActions,
  getEventTags: events.getEventTags,
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

  getEventMeta: metadata.getEventMeta,
  getDeviceMeta: metadata.getDeviceMeta
};
