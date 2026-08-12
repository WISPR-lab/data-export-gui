import DB from '@/database/index.js'
import { demoInstagramSql } from './demoData.js'
import { getLogger } from '@/utils/logger';

const logger = getLogger('DemoDatabaseLoader');

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
      logger.debug('Initializing demo database...')
      DB.setActiveDatabase('demo')

      // Clear any pre-existing demo data to avoid PK conflicts from persistent OPFS
      await DB.clearAllTables()

      const sqlContent = demoInstagramSql
      logger.debug('Executing SQL script')

      const db = await DB.getDB()
      await db.exec(sqlContent)

      this.demoDbLoaded = true
      logger.debug('Demo database initialized successfully')
    } catch (e) {
      logger.error('Critical initialization error:', e)
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
      logger.debug('Demo database cleared')
    } catch (e) {
      logger.error('Failed to clear demo database:', e)
    }
  }
}

export default new DemoDatabaseLoader()

