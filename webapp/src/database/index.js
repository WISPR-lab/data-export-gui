// custom to WISPR-lab/data-export-gui

import sqlite3InitModule from '@sqlite.org/sqlite-wasm';
import * as events from './queries/events.js';
import * as uploads from './queries/uploads.js';
import * as comments from './queries/comments.js';
let db = null;
let initPromise = null;

export async function getDB() {
  if (db) return db;
  
  if (!initPromise) {
    initPromise = (async () => {
      console.log('[Database] Initializing SQLite WASM...');
      const sqlite3 = await sqlite3InitModule({
        print: console.log,
        printErr: console.error,
      });
      
      console.log('[Database] Opening OPFS database...');
      db = new sqlite3.oo1.OpfsDb('/mnt/data/timeline.db');
      console.log('[Database] Database ready');
      
      return db;
    })();
  }
  
  return initPromise;
}

export async function closeDB() {
  if (db) {
    db.close();
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
  deleteEvents: events.deleteEvents,
  
  getUploads: uploads.getUploads,
  getUploadById: uploads.getUploadById,
  
  getEventComments: comments.getEventComments,
  addEventComment: comments.addEventComment,
  updateEventComment: comments.updateEventComment,
  deleteEventComment: comments.deleteEventComment,
};
