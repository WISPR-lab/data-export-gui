// modified for WISPR-lab/data-export-gui

let sqlite3 = null;
let initializedDbs = new Set(); // Track which DBs have been initialized
// Fallback in-memory DB map when OPFS is unavailable (e.g. missing security headers). Ceiling: transient storage resetting on reload; upgrade path: restore OPFS with COOP/COEP.
let dbInstances = new Map();

async function getSqlite() {
  if (!sqlite3) {
    const { default: init } = await import('./sqlite-wasm/index.mjs');
    sqlite3 = await init({ print: console.log, printErr: console.error });
  }
  return sqlite3;
}

async function ensureSchema(db, schemaPath, dbPath) {
  /* Runs schema SQL once per dbPath lifetime (tracked by initializedDbs Set); fetches schema from a relative URL derived from schemaPath. */
  if (initializedDbs.has(dbPath)) return; // Skip if already initialized
  try {
    const fetchPath = schemaPath.startsWith('/') ? `.${schemaPath}` : `./${schemaPath}`;
    const response = await fetch(fetchPath);
    if (!response.ok) {
      throw new Error(`Failed to fetch schema: ${response.status} ${response.statusText}`);
    }
    const sql = await response.text();
    if (!sql || sql.trim().length === 0) {
      throw new Error('Schema file is empty');
    }
    db.exec(sql);
    initializedDbs.add(dbPath); // Mark as initialized
    console.log(`[Sqlite Worker] schema initialized for ${dbPath}`);
  } catch (e) {
    console.error('[sqlite Worker] error initializing schema:', e);
    throw e;
  }
}

self.onmessage = async (e) => {
  const { id, method, args } = e.data;
  if (method !== 'exec') return;

  try {
    const sq3 = await getSqlite();
    const dbPath = args.dbPath || '/userdata.db';
    let db;
    let isOpfs = true;

    if (dbInstances.has(dbPath)) {
      db = dbInstances.get(dbPath);
      isOpfs = false;
    } else {
      try {
        db = new sq3.oo1.OpfsDb(dbPath);
      } catch (opfsErr) {
        console.warn('[sqlite Worker] OPFS unavailable, falling back to in-memory DB:', opfsErr);
        db = new sq3.oo1.DB(dbPath, 'ct');
        isOpfs = false;
        dbInstances.set(dbPath, db);
      }
    }

    db.exec('PRAGMA foreign_keys = ON;');
    await ensureSchema(db, args.schemaPath, dbPath);
    
    const result = db.exec(args.sql, args.options);
    
    if (isOpfs) {
      db.close(); 
    }
    
    self.postMessage({ id, result, success: true });
  } catch (error) {
    self.postMessage({ id, error: { message: error.message } });
  }
};