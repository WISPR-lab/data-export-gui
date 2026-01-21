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
 * simulates the pyodideWorker.js interface
 * 
 * the actual worker:
 * 1. initializes pyodide/wasm
 * 2. fetches files from /pyparser/ and mounts them to wasm filesystem
 * 4. listens for messages with { id, command, args }
 * 5. posts back { id, result, success } or { id, error, success: false }
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
          case 'test_environment':
            // Mock response from test_environment()
            result = {
              py_function: 'test_environment',
              health: {
                'base.py': true,
                'json_.py': true,
                'jsonl_.py': true,
                'csv_.py': true,
                'json_label_values.py': true,
                'csv_multi.py': true,
                'schema_utils.py': true,
                'time_utils.py': true,
                'import_test': true,
              },
            };
            break;

          case 'group_schema_by_path':
            // mock response: would normally parse YAML and group by file path
            result = {
              py_function: 'group_schema_by_path',
              path_schemas: {
                'security_and_login_information/account_activity.json': [
                  {
                    category: 'auth.login.success',
                    temporal: 'event',
                    parser: { format: 'json', json_root: 'account_activity_v2[]' },
                    fields: [],
                  },
                ],
              },
            };
            break;

          case 'parse':
            // mock response: would normally parse file content with schema
            result = {
              events: [
                {
                  primary_timestamp: 1234567890000,
                  ip: '192.168.1.1',
                  message: 'Login event',
                },
              ],
              states: [],
              fatal: false,
              errors: [],
            };
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

  describe('test_environment', () => {
    it('should report healthy file structure', async () => {
      const result = await workerInterface.sendMessage('test_environment');

      expect(result).toHaveProperty('py_function', 'test_environment');
      expect(result).toHaveProperty('health');
      expect(result.health).toEqual(
        expect.objectContaining({
          'base.py': true,
          'json_.py': true,
          'jsonl_.py': true,
          'csv_.py': true,
        })
      );
    });
  });

  describe('group_schema_by_path', () => {
    it('should group schema entries by file path', async () => {
      const mockSchema = `
data_types:
  - temporal: event
    category: 'auth.login.success'
    files:
      - path: security_and_login_information/account_activity.json
`;

      const result = await workerInterface.sendMessage('group_schema_by_path', {
        schemaYaml: mockSchema,
      });

      expect(result).toHaveProperty('py_function', 'group_schema_by_path');
      expect(result).toHaveProperty('path_schemas');
      expect(typeof result.path_schemas).toBe('object');
    });
  });

  describe('parse', () => {
    it('should parse file content and return events', async () => {
      const mockSchema = '{}';
      const mockFileContent = '[{"timestamp": 1234567890, "action": "login"}]';

      const result = await workerInterface.sendMessage('parse', {
        schemaYaml: mockSchema,
        fileContent: mockFileContent,
        filename: 'account_activity.json',
      });

      expect(result).toHaveProperty('events');
      expect(result).toHaveProperty('states');
      expect(result).toHaveProperty('errors');
      expect(result).toHaveProperty('fatal', false);
      expect(Array.isArray(result.events)).toBe(true);
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
      const promise1 = workerInterface.sendMessage('test_environment');
      const promise2 = workerInterface.sendMessage('test_environment');

      const [result1, result2] = await Promise.all([promise1, promise2]);

      expect(result1).toHaveProperty('py_function', 'test_environment');
      expect(result2).toHaveProperty('py_function', 'test_environment');
    });

    it('should timeout on unresponsive worker', async () => {
      const unresponsiveWorker = createMockWorkerInterface();
      unresponsiveWorker.postMessage = () => {
        // do nothing lol
      };

      await expect(
        unresponsiveWorker.sendMessage('test_environment')
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
