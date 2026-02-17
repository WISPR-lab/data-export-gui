let db = null;
let sqlite3 = null;

async function initSQLite(dbPath = '/mnt/data/timeline.db') {
  const { default: sqlite3InitModule } = await import(
    /* webpackIgnore: true */
    '/sqlite-wasm/index.mjs'
  );
  
  sqlite3 = await sqlite3InitModule({
    print: console.log,
    printErr: console.error,
  });
  
  db = new sqlite3.oo1.OpfsDb(dbPath);
  console.log('[DB Worker] OPFS database ready at', dbPath);
}

self.onmessage = async (e) => {
  const { id, method, args } = e.data;
  
  try {
    let result;
    
    switch (method) {
      case 'init':
        await initSQLite(args && args.dbPath);
        result = { success: true };
        break;
        
      case 'exec':
        result = db.exec(args.sql, args.options);
        break;
        
      case 'close':
        if (db) {
          db.close();
          db = null;
        }
        result = { success: true };
        break;
        
      default:
        throw new Error(`Unknown method: ${method}`);
    }
    
    self.postMessage({ id, result });
  } catch (error) {
    self.postMessage({ 
      id, 
      error: {
        message: error.message,
        name: error.name,
        stack: error.stack
      }
    });
  }
};
