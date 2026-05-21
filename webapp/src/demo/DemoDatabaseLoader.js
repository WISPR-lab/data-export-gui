import DB from '@/database/index.js'
import { demoInstagramSql } from './DemoData.js'

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

      const sqlContent = demoInstagramSql
      const statements = sqlContent.split(';').filter((s) => s.trim().length > 0)
      console.log(`[DemoDatabaseLoader] Parsed ${statements.length} SQL statements`)

      for (const statement of statements) {
        try {
          await DB.runRawSql(statement + ';')
        } catch (e) {
          console.warn('[DemoDatabaseLoader] Error executing statement (continuing):', e.message)
        }
      }

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
      await DB.wipeAllData()
      this.demoDbLoaded = false
      console.log('[DemoDatabaseLoader] Demo database cleared')
    } catch (e) {
      console.error('[DemoDatabaseLoader] Failed to clear demo database:', e)
    }
  }
}

export default new DemoDatabaseLoader()
