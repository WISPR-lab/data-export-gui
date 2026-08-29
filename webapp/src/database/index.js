// custom to anonymous-research-group/data-export-gui

import * as events from './queries/events.js';
import * as uploads from './queries/uploads.js';
import * as comments from './queries/comments.js';
import * as metadata from './queries/metadata.js';
import * as devicesV2 from './queries/devices_v2.js';
import { loadConfig } from '../utils/config.js';
import { getLogger } from '../utils/logger.js';
import EventBus from '../event-bus.js';
import { terminatePyodideWorker } from '../pyodide/pyodide-client.js';
import { OPFSManager } from '../storage/opfs_manager.js';

const logger = getLogger('Database');

// Matches sqlite errors that indicate the on-disk schema (from a previous app version)
// no longer matches the shipped schema.sql, e.g. "no such column: x", "no such table: x",
// "table x has no column named y".
const SCHEMA_MISMATCH_RE = /no such (column|table)|has no column named/i;

let worker = null;
let messageId = 0;

function assertValidDbName(dbName) {
  var target = dbName || 'userdata';
  if (target !== 'userdata' && target !== 'demo') {
    throw new Error(`[Database] Invalid dbName: ${JSON.stringify(dbName)}`);
  }
  return target;
}

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

async function getDbPaths(dbName) {
  assertValidDbName(dbName);
  const cfg = await loadConfig();
  const dbFilename = cfg.database.db_path.split('/').pop(); // e.g., "userdata.db"
  const dbPath = dbName === 'userdata' ? `/${dbFilename}` : '/demo.db';

  return {
    schemaPath: cfg.paths.schema,
    dbPath,
  };
}

export async function getDB(dbName) {
  /* Lazy-creates the sqlite worker; returns an exec-only interface bound to the explicitly-requested db. */
  assertValidDbName(dbName);
  if (!worker) {
    // [Database] Initializing
    worker = new Worker('./sqlite-worker.js');
    window.dbWorker = worker; // debug
  }

  return {
    async exec(sql, options) {
      const { schemaPath, dbPath } = await getDbPaths(dbName);
      return callPyodideWorker('exec', {
        sql,
        options: options || {},
        schemaPath,
        dbPath,
      }).catch(function(err) {
        const msg = (err && err.message) || String(err);
        if (msg.indexOf('OpfsDb') !== -1 && msg.indexOf('constructor') !== -1) {
          EventBus.$emit('opfsUnavailable');
        } else if (SCHEMA_MISMATCH_RE.test(msg)) {
          EventBus.$emit('schemaMismatch', msg);
        }
        throw err;
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
    logger.debug('Worker terminated');
  }
}

export async function resetAllLocalData(options) {
  /* Shared "hard refresh" mechanism: closes the sqlite worker and the pyodide worker
     (so no open OPFS file handles block deletion), then recursively wipes OPFS and
     browser storage. Single place this logic lives - reused by SafeExitButton,
     DebugOPFS's "Nuke All", OpfsCompatibilityDialog, and SchemaRefreshDialog. */
  const opts = options || {};
  const unregisterServiceWorkers = opts.unregisterServiceWorkers || false;

  try {
    await closeDB();
  } catch (e) {
    logger.warn('Failed to close DB during reset:', e);
  }

  try {
    terminatePyodideWorker();
  } catch (e) {
    logger.warn('Failed to terminate pyodide worker during reset:', e);
  }

  try {
    const opfsManager = new OPFSManager();
    await opfsManager.nukeAll();
  } catch (e) {
    logger.warn('Failed to nuke OPFS during reset:', e);
  }

  try {
    localStorage.clear();
    sessionStorage.clear();
  } catch (e) {
    logger.warn('Failed to clear local/session storage during reset:', e);
  }

  if (unregisterServiceWorkers && navigator.serviceWorker) {
    try {
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map((r) => r.unregister().catch(function() {})));
    } catch (e) {
      logger.warn('Failed to unregister service workers during reset:', e);
    }
  }
}

export async function clearAllTables(dbName) {
  /* Dynamically queries sqlite_master for all user tables and DELETEs their rows (not DROP — preserves schema). */
  const targetDb = dbName || 'userdata';
  const db = await getDB(targetDb);

  // Query sqlite_master to get all tables dynamically
  const result = await db.exec(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';",
    { returnValue: 'resultRows', rowMode: 'object' }
  );
  
  const tables = result.map(row => row.name);
  
  for (const table of tables) {
    await db.exec(`DELETE FROM ${table};`);
  }
  logger.debug(`Cleared all DB tables`);
}



export default {
  getDB,
  closeDB,
  clearAllTables,
  resetAllLocalData,

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
  addTagToEventsQuery: events.addTagToEventsQuery,
  updateDeviceTags: devicesV2.updateDeviceTags,

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
