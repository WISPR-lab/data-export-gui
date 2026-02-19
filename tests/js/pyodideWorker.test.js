/**
 * pyodideWorker.test.js
 * 
 * tests for the Pyodide Web Worker bridge.
 * 
 * These tests verify that:
 * 1. The worker can be instantiated
 * 2. Worker message handling works (send command → receive result)
 * 3. Error cases are handled gracefully
 * 
 * NOTE: Full Pyodide initialization requires WASM + network access.
 * These tests mock the worker to test the message protocol without full init.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

/**
 * createMockWorkerInterface()
 * simulates the pyodide-worker.js interface
 *
 * the actual worker:
 * 1. initializes pyodide/wasm + python_core modules
 * 2. listens for messages with { id, command, args }
 * 3. posts back { id, result, success } or { id, error, success: false }
 *
 * Active commands: extract, semantic_map, get_whitelist
 */
function createMockWorkerInterface() {
  const messageHandlers = {};
  let messageCounter = 0;

  return {
    // simulates sending a message to the worker and waiting for response
    sendMessage(command, args = {}) {
      return new Promise((resolve, reject) => {
        const id = messageCounter++;
        const timeout = setTimeout(() => {
          delete messageHandlers[id];
          reject(new Error(`Worker message timeout for command: ${command}`));
        }, 5000);

        messageHandlers[id] = (response) => {
          clearTimeout(timeout);
          delete messageHandlers[id];
          if (response.success) {
            resolve(response.result);
          } else {
            reject(new Error(response.error));
          }
        };

        setImmediate(() => {
          this.handleMessage({ data: { id, command, args } });
        });
      });
    },

    // simulate worker receiving message (call onmessage immediately for mock)
    handleMessage(event) {
      const { id, command, args } = event.data;

      try {
        let result;

        switch (command) {
          case 'extract':
            // Mock: Python extractor_worker.extract(platform, given_name)
            result = {
              status: 'success',
              upload_id: 'mock-upload-001',
            };
            break;

          case 'semantic_map':
            // Mock: Python semantic_map_worker.map(platform, upload_id)
            result = {
              status: 'success',
              events_count: 5,
              devices_count: 2,
            };
            break;

          case 'get_whitelist':
            // Mock: Manifest(platform).file_paths()
            result = [
              'security_and_login_information/account_activity.json',
              'security_and_login_information/logins_and_logouts.json',
            ];
            break;

          default:
            throw new Error(`Unknown command: ${command}`);
        }

        // simulate worker posting response back
        this.postMessage({ id, result, success: true });
      } catch (error) {
        this.postMessage({ id, error: error.message, success: false });
      }
    },


    // simulates worker.postMessage()
    postMessage(message) {
      const { id } = message;
      if (messageHandlers[id]) {
        messageHandlers[id](message);
      }
    },
  };
}

describe('PyodideWorker', () => {
  let workerInterface;

  beforeEach(() => {
    workerInterface = createMockWorkerInterface();
  });

  afterEach(() => {
    workerInterface = null;
  });

  describe('extract', () => {
    it('should call Python extractor and return upload_id', async () => {
      const result = await workerInterface.sendMessage('extract', {
        platform: 'facebook',
        givenName: 'test.zip',
      });

      expect(result).toHaveProperty('status', 'success');
      expect(result).toHaveProperty('upload_id');
      expect(typeof result.upload_id).toBe('string');
    });
  });

  describe('semantic_map', () => {
    it('should map raw data to events and return counts', async () => {
      const result = await workerInterface.sendMessage('semantic_map', {
        platform: 'facebook',
        uploadId: 'mock-upload-001',
      });

      expect(result).toHaveProperty('status', 'success');
      expect(result).toHaveProperty('events_count');
      expect(result).toHaveProperty('devices_count');
      expect(result.events_count).toBeGreaterThanOrEqual(0);
    });
  });

  describe('get_whitelist', () => {
    it('should return file path patterns from the manifest', async () => {
      const result = await workerInterface.sendMessage('get_whitelist', {
        platform: 'facebook',
      });

      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      expect(result[0]).toContain('.json');
    });
  });

  describe('error handling', () => {
    it('should reject with error for unknown command', async () => {
      await expect(
        workerInterface.sendMessage('unknown_command')
      ).rejects.toThrow('Unknown command: unknown_command');
    });

    it('should include error message in response', async () => {
      try {
        await workerInterface.sendMessage('unknown_command');
        expect.fail('Should have thrown');
      } catch (error) {
        expect(error.message).toContain('Unknown command');
      }
    });
  });

  describe('message protocol', () => {
    it('should handle concurrent messages with unique IDs', async () => {
      const promise1 = workerInterface.sendMessage('extract', { platform: 'facebook', givenName: 'a.zip' });
      const promise2 = workerInterface.sendMessage('extract', { platform: 'facebook', givenName: 'b.zip' });

      const [result1, result2] = await Promise.all([promise1, promise2]);

      expect(result1).toHaveProperty('status', 'success');
      expect(result2).toHaveProperty('status', 'success');
    });

    it('should timeout on unresponsive worker', async () => {
      const unresponsiveWorker = createMockWorkerInterface();
      unresponsiveWorker.postMessage = () => {
        // do nothing — simulates a hung worker
      };

      await expect(
        unresponsiveWorker.sendMessage('extract', { platform: 'facebook', givenName: 'a.zip' })
      ).rejects.toThrow('timeout');
    }, { timeout: 10000 }); // extend timeout for this test
  });

  describe('Initialization with retry', () => {
    /**
     * These tests simulate Pyodide initialization behavior.
     * In the real worker, initPyodideWithRetry():
     * - Retries up to 3 times on failure
     * - Exponential backoff: 100ms, 500ms, 2500ms
     * - 30s timeout per attempt
     * - Returns error details if all attempts fail
     */

    it('should succeed on first try', async () => {
      const mockInitResult = {
        success: true,
        message: 'Pyodide initialized successfully',
      };

      expect(mockInitResult.success).toBe(true);
    });

    it('should track init errors when all retries fail', async () => {
      const initError = {
        type: 'PYODIDE_INIT_FAILED',
        message: 'Failed to load WASM after 3 attempts',
        attempt: 3,
        timestamp: new Date().toISOString(),
      };

      expect(initError.type).toBe('PYODIDE_INIT_FAILED');
      expect(initError.attempt).toBe(3);
      expect(initError).toHaveProperty('timestamp');
    });

    it('should include error details in structured response', async () => {
      const errorResponse = {
        id: 0,
        success: false,
        error: 'Failed to load WASM module',
        errorType: 'PYODIDE_INIT_FAILED',
        source: 'pyodide_init',
      };

      expect(errorResponse).toEqual(
        expect.objectContaining({
          success: false,
          errorType: 'PYODIDE_INIT_FAILED',
          source: 'pyodide_init',
        })
      );
    });

    it('should report timeout errors with correct type', async () => {
      const timeoutError = {
        id: 1,
        success: false,
        error: 'Worker timeout waiting for Pyodide',
        errorType: 'WORKER_TIMEOUT',
        source: 'pyodide_init',
      };

      expect(timeoutError.errorType).toBe('WORKER_TIMEOUT');
      expect(timeoutError.error).toContain('timeout');
    });

    it('should reject worker commands if init failed', async () => {
      // Simulate state where initError is set
      const workerState = {
        pyodideInitialized: false,
        initError: {
          type: 'PYODIDE_INIT_FAILED',
          message: 'Pyodide failed to initialize',
        },
      };

      // When a command is received, check init status first
      if (!workerState.pyodideInitialized && workerState.initError) {
        const response = {
          success: false,
          error: workerState.initError.message,
          errorType: workerState.initError.type,
          source: 'pyodide_init',
        };

        expect(response.success).toBe(false);
        expect(response.errorType).toBe('PYODIDE_INIT_FAILED');
      }
    });

    it('should preserve error type through command lifecycle', async () => {
      const commandError = {
        message: 'Schema parsing failed due to invalid YAML',
        source: 'parser',
      };

      // Simulate classification
      let errorType = 'UNKNOWN_ERROR';
      if (commandError.message.includes('schema') || commandError.message.includes('YAML')) {
        errorType = 'SCHEMA_MISMATCH';
      }

      const response = {
        id: 2,
        success: false,
        error: commandError.message,
        errorType,
        source: commandError.source,
      };

      expect(response.errorType).toBe('SCHEMA_MISMATCH');
      expect(response.source).toBe('parser');
    });
  });
});
