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
    this._initPromise = null
  }

  async initializeDemoDb() {
    if (this.demoDbLoaded) return
    if (this._initPromise) return this._initPromise

    this._initPromise = this._doInit().finally(() => {
      this._initPromise = null
    })
    return this._initPromise
  }

  async _doInit() {
    try {
      logger.debug('Initializing demo database...')

      // Clear any pre-existing demo data to avoid PK conflicts from persistent OPFS
      await DB.clearAllTables('demo')

      const sqlContent = demoInstagramSql
      logger.debug('Executing SQL script')

      const db = await DB.getDB('demo')
      await db.exec(sqlContent)

      this.demoDbLoaded = true
      logger.debug('Demo database initialized successfully')
    } catch (e) {
      logger.error('Critical initialization error:', e)
      throw e
    }
  }

  reset() {
    this.demoDbLoaded = false
  }

  async clearDemoDb() {
    if (this._initPromise) {
      await this._initPromise.catch(() => {}) // already logged by _doInit
    }
    try {
      await DB.clearAllTables('demo')
      this.demoDbLoaded = false
      logger.debug('Demo database cleared')
    } catch (e) {
      logger.error('Failed to clear demo database:', e)
    }
  }
}

export default new DemoDatabaseLoader()

