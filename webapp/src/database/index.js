// custom to WISPR-lab/data-export-gui

import * as events from './queries/events.js';
import * as uploads from './queries/uploads.js';
import * as comments from './queries/comments.js';
import * as metadata from './queries/metadata.js';
import * as devices from './queries/devices.js';
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

let cachedPaths = null;

async function getDbPaths() {
  if (cachedPaths) return cachedPaths;
  const cfg = await loadConfig();
  cachedPaths = {
    schemaPath: cfg.paths.schema,
    dbPath: '/' + cfg.database.db_path.split('/').pop(),
  };
  return cachedPaths;
}

export async function getDB() {
  if (!worker) {
    // [Database] Initializing
    worker = new Worker('./sqlite-worker.js');
    window.dbWorker = worker; // debug
  }

  return {
    async exec(sql, options) {
      const { schemaPath, dbPath } = await getDbPaths();
      return callPyodideWorker('exec', { 
        sql, 
        options: options || {},
        schemaPath,
        dbPath,
      });
    }
  };
};

/*
  if (db) return db;
  
  if (!initPromise) {
    initPromise = (async () => {
      // [Database] Starting worker
      
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
      // [Database] Ready
      
      const tables = await callPyodideWorker('exec', { 
        sql: "SELECT name FROM sqlite_master WHERE type='table';", 
        options: {returnValue: 'resultRows', rowMode: 'object'}});
      
      const tableNames = (tables && tables.length > 0) 
        ? tables.map(function(row) { return row.name; }).join(', ') 
        : 'None';
      
      // [Database] Tables loaded

      
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
    // [Database] Closed
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

  // Query sqlite_master to get all tables dynamically
  const result = await db.exec(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';",
    { returnValue: 'resultRows', rowMode: 'object' }
  );
  
  const tables = result.map(row => row.name);
  
  for (const table of tables) {
    await db.exec(`DELETE FROM ${table};`);
  }
  // [Database] Data cleared
}



export default {
  getDB,
  closeDB,
  clearAllTables,
  
  searchEvents: events.searchEvents,
  getEventCount: events.getEventCount,
  // Note: Frontend uses getEventActions (event_action field), not getCategories (event_category field)
  getEventActions: events.getEventActions,
  getEventMessages: events.getEventMessages,
  getEventTags: events.getEventTags,
  deleteEvents: events.deleteEvents,
  addLabelEvent: events.addLabelEvent,
  removeLabelEvent: events.removeLabelEvent,
  updateEventTags: events.updateEventTags,
  
  getUploads: uploads.getUploads,
  getUploadById: uploads.getUploadById,
  getUploadedFiles: uploads.getUploadedFiles,
  updateUpload: uploads.updateUpload,
  deleteUpload: uploads.deleteUpload,
  
  getEventComments: comments.getEventComments,
  addEventComment: comments.addEventComment,
  updateEventComment: comments.updateEventComment,
  deleteEventComment: comments.deleteEventComment,

  getEventMeta: metadata.getEventMeta,
  getDeviceMeta: metadata.getDeviceMeta
};
