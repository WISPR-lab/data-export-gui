// custom to WISPR-lab/data-export-gui

import * as events from './queries/events.js';
import * as uploads from './queries/uploads.js';
import * as comments from './queries/comments.js';
import * as metadata from './queries/metadata.js';
import { loadConfig } from '../utils/config.js';


let worker = null;
let messageId = 0;
let activeDbName = 'userdata'; // Track which DB is active ('userdata' mode vs 'demo')

function callPyodideWorker(method, args) {
  /* Promise wrapper for worker.postMessage; matches response by auto-incrementing id and reconstructs Error objects from serialized error payloads. */
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
  const cfg = await loadConfig();
  const dbFilename = cfg.database.db_path.split('/').pop(); // e.g., "userdata.db"
  const dbPath = activeDbName === 'userdata' ? `/${dbFilename}` : '/demo.db';
  
  return {
    schemaPath: cfg.paths.schema,
    dbPath,
  };
}

export async function getDB() {
  /* Lazy-creates the sqlite worker; returns an exec-only interface that resolves DB path per-call based on activeDbName. */
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

      // config.database.db_path is "/mnt/data/userdata.db" (a Pyodide mount path),
      // OpfsDb interprets the path as an OPFS-internal virtual path.
      // config.database.db_path is "/mnt/data/userdata.db" (a Pyodide mount path),
      // but OpfsDb would create literal "mnt/data/" dirs inside OPFS root.
      // Extract just the filename so the DB sits at (root)/userdata.db,
      // which Pyodide (mounting OPFS root at /mnt/data) sees as /mnt/data/userdata.db.
      const dbFilename = cfg.database.db_path.split('/').pop(); // "userdata.db"
      
      worker = new Worker('./sqlite-worker.js');
      window.dbWorker = worker;
      
      await callPyodideWorker('init', { 
        dbPath: "/userdata.db",  // TODO FIX HARDCODING IN CONFIG
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
} */

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
  /* Dynamically queries sqlite_master for all user tables and DELETEs their rows (not DROP — preserves schema). */
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
  
  // DB switching
  setActiveDatabase(dbName) {
    activeDbName = dbName; // 'userdata' or 'demo'
    console.log(`[Database] Switched to ${dbName} database`);
  },
  getActiveDatabase() {
    return activeDbName;
  },
  
  searchEvents: events.searchEvents,
  getEventCount: events.getEventCount,
  // Note: Frontend uses getEventActions (event_action field), not getCategories (event_category field)
  getEventActions: events.getEventActions,
  getEventTypes: events.getEventTypes,
  getEventTags: events.getEventTags,
  getIPAddresses: events.getIPAddresses,
  deleteEvents: events.deleteEvents,
  addLabelEvent: events.addLabelEvent,
  removeLabelEvent: events.removeLabelEvent,
  updateEventTags: events.updateEventTags,
  clearAllTags: events.clearAllTags,
  
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
