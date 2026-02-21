// Upload Functionality Tests
// npm test -- upload.test.js

import { describe, it, expect, beforeEach, vi, beforeAll } from 'vitest'
import fs from 'fs'
import path from 'path'
import { execSync } from 'child_process'

// Mapping for manual testing with real data (drop files in tests/zip_data/)
const REAL_DATA_MAPPING = {
  facebook: '../zip_data/facebook.zip',
  apple: '../zip_data/apple.zip',
  google: '../zip_data/google.zip'
}

const PYTHON_PATH = path.join(__dirname, '../../.venv/bin/python')
const BRIDGE_PATH = path.join(__dirname, '../python/test_js_bridge.py')

// State to toggle between purely fake outcomes and real python bridge calls
let workerMode = 'MOCK' // 'MOCK' or 'BRIDGE'

// Mock global Worker BEFORE importing upload.js
class MockWorker {
  constructor(url) {
    this.url = url
    this.onmessage = null
  }
  postMessage(data) {
    if (workerMode === 'MOCK') {
      this.handleMockMode(data)
    } else {
      this.handleBridgeMode(data)
    }
  }

  handleMockMode(data) {
    setTimeout(() => {
      if (data.command === 'extract') {
        this.onmessage({ data: { id: data.id, success: true, result: { status: 'success', upload_id: 'mock-upload-001' } } })
      } else if (data.command === 'semantic_map') {
        this.onmessage({ data: { id: data.id, success: true, result: { status: 'success', events_count: 1, devices_count: 0 } } })
      } else if (data.command === 'get_whitelist') {
        this.onmessage({ data: { id: data.id, success: true, result: ['security_and_login_information/account_activity.json'] } })
      }
    }, 0)
  }

  handleBridgeMode(data) {
    if (data.command === 'extract') {
      try {
        const input = JSON.stringify({
          platform: data.args.platform,
          given_name: data.args.givenName,
        })
        const resultRaw = execSync(`${PYTHON_PATH} ${BRIDGE_PATH} extract`, {
          input,
          encoding: 'utf-8',
          maxBuffer: 10 * 1024 * 1024
        })
        const result = JSON.parse(resultRaw)
        setTimeout(() => {
          this.onmessage({ data: { id: data.id, success: true, result } })
        }, 0)
      } catch (e) {
        setTimeout(() => {
          this.onmessage({ data: { id: data.id, success: false, error: e.message } })
        }, 0)
      }
    } else if (data.command === 'semantic_map') {
      try {
        const input = JSON.stringify({
          platform: data.args.platform,
          upload_id: data.args.uploadId,
        })
        const resultRaw = execSync(`${PYTHON_PATH} ${BRIDGE_PATH} semantic_map`, {
          input,
          encoding: 'utf-8',
          maxBuffer: 10 * 1024 * 1024
        })
        const result = JSON.parse(resultRaw)
        setTimeout(() => {
          this.onmessage({ data: { id: data.id, success: true, result } })
        }, 0)
      } catch (e) {
        setTimeout(() => {
          this.onmessage({ data: { id: data.id, success: false, error: e.message } })
        }, 0)
      }
    } else if (data.command === 'get_whitelist') {
      // Use regex to extract paths from the manifest for bridge mode
      const platform = data.args.platform
      const schemaPath = path.join(__dirname, '../../manifests', `${platform}.yaml`)
      if (fs.existsSync(schemaPath)) {
        const content = fs.readFileSync(schemaPath, 'utf8')
        const paths = []
        const pathMatches = content.matchAll(/path: ["']?([^"'\n ]+)["']?/g)
        for (const match of pathMatches) {
          paths.push(match[1])
        }
        setTimeout(() => {
          this.onmessage({ data: { id: data.id, success: true, result: paths } })
        }, 0)
      } else {
        setTimeout(() => {
          this.onmessage({ data: { id: data.id, success: true, result: [] } })
        }, 0)
      }
    }
  }

  addEventListener(type, handler) { this.onmessage = handler }
  removeEventListener() {}
}
global.Worker = MockWorker

// Mock global fetch
global.fetch = vi.fn().mockImplementation((url) => {
  const filename = url.split('/').pop()
  const schemaPath = path.join(__dirname, '../../schemas', filename)
  if (fs.existsSync(schemaPath)) {
    return Promise.resolve({
      ok: true,
      text: () => Promise.resolve(fs.readFileSync(schemaPath, 'utf8'))
    })
  }
  return Promise.resolve({
    ok: true,
    text: () => Promise.resolve('data_types: []')
  })
})

// Mock dependencies
vi.mock('../../webapp/src/database.js', () => ({
  default: {
    createTimeline: vi.fn(),
    bulkInsert: vi.fn(),
    saveSketchTimeline: vi.fn(),
    getTimelines: vi.fn()
  }
}))

// Use dynamic import after global mocks are set
let processUpload;
beforeAll(async () => {
  const module = await import('../../webapp/src/upload.js')
  processUpload = module.processUpload
})

import BrowserDB from '../../webapp/src/database.js'
import JSZip from 'jszip'

describe('Upload Functionality', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // By default, make BrowserDB methods return empty success responses
    BrowserDB.createTimeline.mockResolvedValue({ data: { objects: [{ id: 123 }] } })
    BrowserDB.bulkInsert.mockResolvedValue(true)
    BrowserDB.saveSketchTimeline.mockResolvedValue({})
    BrowserDB.getTimelines.mockResolvedValue({ data: { objects: [] } })
    workerMode = 'MOCK' // Reset to pure JS mock by default
  })

  describe('[Unit] JS Orchestration Logic (Pure Mock)', () => {
    async function createValidZip() {
      const zip = new JSZip()
      zip.file('test.json', '{"dummy": "data"}')
      const buffer = await zip.generateAsync({ type: 'nodebuffer' })
      return new File([buffer], 'test.zip', { type: 'application/zip' })
    }

    it('should drive the full UI/UX flow from start to database insertion', async () => {
      const mockFile = await createValidZip()
      const mockStore = {
        commit: vi.fn()
      }
      
      const summary = await processUpload(mockFile, 'facebook', 1, mockStore)
      
      expect(summary.success).toBe(true)
      expect(summary.totalEventsAdded).toBe(1) // Defined in MockWorker.handleMockMode
      expect(BrowserDB.bulkInsert).toHaveBeenCalled()
      expect(mockStore.commit).toHaveBeenCalledWith('START_UPLOAD', 'test.zip')
      expect(mockStore.commit).toHaveBeenCalledWith('COMPLETE_UPLOAD')
    })

    it('should correctly handle and report manifest retrieval failures', async () => {
      const mockFile = await createValidZip()
      const mockStore = {
        commit: vi.fn()
      }
      
      global.fetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Not Found'
      })

      const summary = await processUpload(mockFile, 'nonexistent', 1, mockStore)
      
      expect(summary.success).toBe(false)
      expect(summary.errors[0]).toContain('Failed to read manifest for nonexistent')
      expect(mockStore.commit).toHaveBeenCalledWith('FAIL_UPLOAD', expect.any(String))
    })

    it('should handle ZIP extraction errors', async () => {
      // Passing junk content will cause JSZip to throw
      const mockFile = new File(['not a zip'], 'test.zip')
      const mockStore = {
        commit: vi.fn()
      }
      
      const summary = await processUpload(mockFile, 'facebook', 1, mockStore)
      
      expect(summary.success).toBe(false)
      expect(summary.errors.length).toBeGreaterThan(0)
      expect(mockStore.commit).toHaveBeenCalledWith('FAIL_UPLOAD', expect.any(String))
    })
  })

  describe('[Integration] Parser Integration (Python Bridge)', () => {
    beforeEach(() => {
      workerMode = 'BRIDGE'
    })

    async function createFacebookZip() {
      const zip = new JSZip()
      // Use a real path and structure from facebook.yaml
      const data = {
        account_activity_v2: [
          {
            action: 'Login',
            timestamp: 1600000000,
            ip_address: '1.2.3.4',
            user_agent: 'Mozilla/5.0',
            datr_cookie: 'abc'
          }
        ]
      }
      zip.file('security_and_login_information/account_activity.json', JSON.stringify(data))
      const buffer = await zip.generateAsync({ type: 'nodebuffer' })
      return new File([buffer], 'facebook_test.zip', { type: 'application/zip' })
    }

    it('should successfully parse real JSON data through the Python bridge', async () => {
      const mockFile = await createFacebookZip()
      const summary = await processUpload(mockFile, 'facebook', 1)
      
      expect(summary.success).toBe(true)
      expect(summary.totalEventsAdded).toBe(1)
      
      // Verify standardized fields from real parser
      const insertCall = BrowserDB.bulkInsert.mock.calls[0]
      const events = insertCall[2]
      expect(events[0]).toHaveProperty('primary_timestamp')
      expect(events[0].ip).toBe('1.2.3.4')
    })
  })

  describe('[End-to-End] Real Data Validation (Python Bridge)', () => {
    beforeAll(() => {
      workerMode = 'BRIDGE'
    })

    // Manual tests for real data (ignored if files aren't present)
    const filesToTest = Object.entries(REAL_DATA_MAPPING).filter(([_, filename]) => 
      fs.existsSync(path.join(__dirname, filename))
    )

    if (filesToTest.length > 0) {
      filesToTest.forEach(([platform, filename]) => {
        const filePath = path.join(__dirname, filename)

        it(`should process real zip: ${filename}`, async () => {
          const buffer = fs.readFileSync(filePath)
          const file = new File([buffer], filename, { type: 'application/zip' })
          
          console.log(`\n[DATA INGESTION TEST: ${platform}]`)
          const summary = await processUpload(file, platform, 1)
          
          console.log(`Step 1: Upload Logic ... ${summary.success ? 'OK' : 'FAILED'}`)
          console.log(`Step 2: Parsing ... Found ${summary.totalEventsAdded} events, ${summary.totalStatesAdded} states`)
          
          if (BrowserDB.bulkInsert.mock.calls.length > 0) {
            const lastCall = BrowserDB.bulkInsert.mock.calls[BrowserDB.bulkInsert.mock.calls.length - 1]
            const [sketchId, timelineId, events, states] = lastCall
            
            // DUMP OUTPUT FOR DEBUGGING
            const debugFile = path.join(__dirname, `../tmp_outputs/debug_${platform}.json`)
            fs.writeFileSync(debugFile, JSON.stringify({
              platform,
              events,
              states
            }, null, 2))
          }
          
          if (summary.errors.length > 0) {
            console.log(`Found Errors:`, summary.errors)
          }
          
          expect(summary.success).toBe(true)
          console.log(`-----------------------------------\n`)
        })
      })
    }
  })
})



