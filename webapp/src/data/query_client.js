import sqlite3InitModule from '@sqlite.org/sqlite-wasm';

/**
 * QueryClient (The Reader)
 * Single entry point for the UI to read from the Shared Buffer (OPFS SQLite DB).
 */
export class QueryClient {
  constructor() {
    this.db = null;
    this.isInitialized = false;
    this.initPromise = null;
  }

  async init() {
    if (this.isInitialized) return true;
    if (this.initPromise) return this.initPromise;

    this.initPromise = (async () => {
      try {
        console.log('[QueryClient] Initializing sqlite-wasm...');
        const sqlite3 = await sqlite3InitModule({
          print: console.log,
          printErr: console.error,
        });

        if (!sqlite3.oo1 || !sqlite3.oo1.OpfsDb) {
          throw new Error("sqlite3.oo1.OpfsDb is not available. OPFS not supported?");
        }

        // Shared Buffer Access: Open in Read-Write (rw) mode.
        // Even for reading, WAL mode requires rw access to shm/wal files.
        this.db = new sqlite3.oo1.OpfsDb('/forensics.db', 'rw'); 
        
        console.log('[QueryClient] Connected to /forensics.db in OPFS');
        
        // Verify WAL
        this.db.exec('PRAGMA journal_mode=WAL;'); 
        
        this.isInitialized = true;
        return true;
      } catch (e) {
        console.error('[QueryClient] Initialization failed:', e);
        this.initPromise = null; // Allow retry
        throw e;
      }
    })();

    return this.initPromise;
  }

  /**
   * Execute a raw SQL query and return results as an array of objects.
   * @param {string} sql 
   * @param {Array} bindParams 
   * @returns {Promise<Array>}
   */
  async runQuery(sql, bindParams = []) {
    await this.init();
    const results = [];
    try {
      this.db.exec({
        sql: sql,
        bind: bindParams,
        rowMode: 'object',
        callback: (row) => results.push(row)
      });
      return results;
    } catch (e) {
      console.error(`[QueryClient] SQL Error: ${e.message} \nQuery: ${sql}`);
      throw e;
    }
  }

  /**
   * Get events for the timeline query.
   * Replaces legacy BrowserDB.getEvents
   * 
   * @param {object} options { query, limit, offset }
   */
  async getEvents(options = {}) {
    // TODO: This should query the 'Silver Layer' Views (e.g., view_apple_login)
    // For now, validting connection with raw_events
    const limit = options.limit || 50;
    const offset = options.offset || 0;
    
    // Simple fetch from raw_events for now
    const sql = `
      SELECT id, source_file, adapter_type, raw_data 
      FROM raw_events 
      ORDER BY id DESC 
      LIMIT ? OFFSET ?
    `;
    
    return this.runQuery(sql, [limit, offset]);
  }
}

// Singleton Export
export const db = new QueryClient();
export default db;
