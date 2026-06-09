import DB from '@/database/index.js'
import { demoInstagramSql } from './demoData.js'

/**
 * DemoDatabaseLoader manages the database state for the demo.
 * It is responsible for parsing and executing the sample data SQL.
 */
class DemoDatabaseLoader {
  constructor() {
    this.demoDbLoaded = false
  }

  /**
   * Initializes the demo database by executing sample SQL statements.
   */
  async initializeDemoDb() {
    if (this.demoDbLoaded) return

    try {
      console.log('[DemoDatabaseLoader] Initializing demo database...')
      DB.setActiveDatabase('demo')

      // Clear any pre-existing demo data to avoid PK conflicts from persistent OPFS
      await DB.clearAllTables()

      const sqlContent = demoInstagramSql
      console.log(`[DemoDatabaseLoader] Executing SQL script`)

      const db = await DB.getDB()
      await db.exec(sqlContent)

      this.demoDbLoaded = true
      console.log('[DemoDatabaseLoader] Demo database initialized successfully')
    } catch (e) {
      console.error('[DemoDatabaseLoader] Critical initialization error:', e)
      throw e
    }
  }

  /**
   * Resets the loaded state, allowing re-initialization if needed.
   */
  reset() {
    this.demoDbLoaded = false
  }

  /**
   * Clears the demo database entirely.
   */
  async clearDemoDb() {
    try {
      await DB.clearAllTables()
      this.demoDbLoaded = false
      console.log('[DemoDatabaseLoader] Demo database cleared')
    } catch (e) {
      console.error('[DemoDatabaseLoader] Failed to clear demo database:', e)
    }
  }
}

export default new DemoDatabaseLoader()

