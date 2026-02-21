let sqlite3 = null;
let hasInitialized = false;

async function loadConfig() {
  const response = await fetch('/config.yaml');
  if (!response.ok) {
    throw new Error('Failed to load config.yaml: ' + response.statusText);
  }
  const text = await response.text();
  config = jsyaml.load(text);
  return config;
}

async function getSqlite() {
  if (!sqlite3) {
    const { default: init } = await import('/sqlite-wasm/index.mjs');
    sqlite3 = await init({ print: console.log, printErr: console.error });
  }
  return sqlite3;
}

async function ensureSchema(db, schemaPath) {
  if (hasInitialized) return;
  try {
    const response = await fetch(schemaPath);
    if (response.ok) {
      const sql = await response.text();
      db.exec(sql);
      console.log('[Sqlite Worker] schema initialized');
    }
  } catch (e) {
    console.error('[sqlite Worker] error initializing schema', e);
  }
  hasInitialized = true;
}

self.onmessage = async (e) => {
  const { id, method, args } = e.data;
  if (method !== 'exec') return;

  try {
    const sq3 = await getSqlite();
    
    const db = new sq3.oo1.OpfsDb('/timeline.db');  // TODO fix config so not hardcoding
    await ensureSchema(db, args.schemaPath);
    
    const result = db.exec(args.sql, args.options);
    
    db.close(); 
    
    self.postMessage({ id, result, success: true });
  } catch (error) {
    self.postMessage({ id, error: { message: error.message } });
  }
};