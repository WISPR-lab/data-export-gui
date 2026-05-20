import DB from '@/database/index.js'
import { demoInstagramSql } from './demoData.js'

class DemoDataLoader {
  constructor() {
    this.demoDbLoaded = false
  }

  async initializeDemoDb() {
    if (this.demoDbLoaded) return
    
    try {
      console.log('[DemoDataLoader] Initializing demo database...')
      
      DB.setActiveDatabase('demo')
      
      const sqlContent = demoInstagramSql
      const statements = this.parseSqlStatements(sqlContent)
      console.log(`[DemoDataLoader] Parsed ${statements.length} SQL statements`)
      
      const db = await DB.getDB()
      for (const statement of statements) {
        if (statement.trim().length === 0) continue
        try {
          await db.exec(statement, { returnValue: 'resultRows' })
        } catch (e) {
          console.warn('[DemoDataLoader] Error executing statement (continuing):', e.message)
        }
      }
      
      this.demoDbLoaded = true
      console.log('[DemoDataLoader] Demo database initialized successfully')
    } catch (e) {
      console.error('[DemoDataLoader] Failed to initialize demo database:', e)
      throw e
    }
  }

  parseSqlStatements(sqlContent) {
    const statements = []
    let current = ''
    let inString = false
    let stringChar = null
    
    for (let i = 0; i < sqlContent.length; i++) {
      const char = sqlContent[i]
      const prevChar = i > 0 ? sqlContent[i - 1] : ''
      
      if ((char === '"' || char === "'") && prevChar !== '\\') {
        if (!inString) {
          inString = true
          stringChar = char
        } else if (char === stringChar) {
          inString = false
          stringChar = null
        }
      }
      
      if (char === ';' && !inString) {
        current += char
        statements.push(current.trim())
        current = ''
        continue
      }
      
      if (!inString && char === '-' && sqlContent[i + 1] === '-') {
        while (i < sqlContent.length && sqlContent[i] !== '\n') {
          i++
        }
        continue
      }
      
      current += char
    }
    
    if (current.trim().length > 0) {
      statements.push(current.trim())
    }
    
    return statements
  }

  async clearDemoDb() {
    try {
      console.log('[DemoDataLoader] Clearing demo database...')
      DB.setActiveDatabase('demo')
      await DB.clearAllTables()
      this.demoDbLoaded = false
      console.log('[DemoDataLoader] Demo database cleared')
    } catch (e) {
      console.error('[DemoDataLoader] Failed to clear demo database:', e)
    }
  }
}

export default new DemoDataLoader()
