// pyodideWorker.js
// SOURCE: webapp/src/pyodideWorker.js
// NOTE: This file is automatically copied to public/ during build (npm run sync-assets).
// DO NOT EDIT the version in the public/ folder.

importScripts('https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js');

let pyodide;
let pyodideReadyPromise;
let initError = null; // Track init failures for error reporting

/**
 * Initializes Pyodide, installs dependencies, and mounts Python source files.
 */
async function initPyodide() {
  pyodide = await loadPyodide();
  
  // Load specialized Python libraries
  await pyodide.loadPackage(['pyyaml', 'pytz']);

  // Fetch and mount our custom Python parser logic
  const pythonFiles = [
    'pyodide.py',
    'base.py',
    'json_.py',
    'jsonl_.py',
    'csv_.py',
    'json_label_values.py',
    'csv_multi.py',
    'schema_utils.py',
    'time_utils.py'
  ];

  for (const file of pythonFiles) {
    const response = await fetch(`/pyparser/${file}`);
    if (!response.ok) {
      console.error(`Failed to fetch ${file}: ${response.statusText}`);
      continue;
    }
    const content = await response.text();
    pyodide.FS.writeFile(file, content);
  }

  // The files are written to the root of Pyodide's filesystem
  // Execute the bridge module directly to load all functions into the global namespace
  pyodide.runPython(`
import sys
if '/' not in sys.path:
    sys.path.insert(0, '/')

# Import everything from our bridge module (which is just pyodide.py in the root)
# Execute it in the global namespace so all functions are available
with open('pyodide.py', 'r') as f:
    bridge_code = f.read()
    exec(bridge_code, globals())
`);
  
  return pyodide;
}

/**
 * Initialize Pyodide with retry logic and timeout.
 * Retries up to 3 times with exponential backoff on failure.
 * 
 * @returns {Promise<object>} Pyodide instance
 * @throws {Error} If all retry attempts fail
 */
async function initPyodideWithRetry() {
  const MAX_RETRIES = 3;
  const INIT_TIMEOUT = 30000; // 30 seconds per attempt
  
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      // Race between init and timeout
      const result = await Promise.race([
        initPyodide(),
        new Promise((_, reject) =>
          setTimeout(
            () => reject(new Error('Pyodide initialization timeout')),
            INIT_TIMEOUT
          )
        )
      ]);
      
      console.log('Pyodide initialized successfully');
      return result;
    } catch (error) {
      const errorMsg = error.message || String(error);
      console.warn(
        `Pyodide init failed (attempt ${attempt}/${MAX_RETRIES}): ${errorMsg}`
      );
      
      // If this was the last attempt, store error and rethrow
      if (attempt === MAX_RETRIES) {
        initError = {
          type: 'PYODIDE_INIT_FAILED',
          message: errorMsg,
          attempt: attempt,
          timestamp: new Date().toISOString(),
        };
        throw error;
      }
      
      // Exponential backoff: 100ms, 500ms, 2500ms
      const backoffMs = 100 * Math.pow(2, attempt - 1);
      await new Promise(resolve => setTimeout(resolve, backoffMs));
    }
  }
}

pyodideReadyPromise = initPyodideWithRetry();

/**
 * Message handler for main thread commands.
 * 
 * Structured error response format:
 * {
 *   id: number,
 *   success: false,
 *   error: string (message),
 *   errorType: string (one of ERROR_TYPES),
 *   source: string ('pyodide_init', 'parser', 'unknown')
 * }
 */
self.onmessage = async (event) => {
  const { id, command, args } = event.data;
  
  try {
    // Check if Pyodide init failed
    if (initError) {
      return self.postMessage({
        id,
        success: false,
        error: initError.message,
        errorType: 'PYODIDE_INIT_FAILED',
        source: 'pyodide_init',
      });
    }

    // Wait for Pyodide to be ready
    try {
      await Promise.race([
        pyodideReadyPromise,
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Worker timeout waiting for Pyodide')), 60000)
        )
      ]);
    } catch (timeoutError) {
      return self.postMessage({
        id,
        success: false,
        error: 'Timeout waiting for parser initialization',
        errorType: 'WORKER_TIMEOUT',
        source: 'pyodide_init',
      });
    }

    let result;
    switch (command) {
      case 'test_environment':
        result = pyodide.runPython('test_environment()').toJs({ dict_converter: Object.fromEntries });
        break;
      
      case 'group_schema_by_path':
        const { schemaYaml } = args;
        pyodide.globals.set('schema_str', schemaYaml);
        result = pyodide.runPython('group_schema_by_path(schema_str)').toJs({ dict_converter: Object.fromEntries });
        break;
        
      case 'parse':
        const { schemaYaml: parseSchema, fileContent, filename } = args;
        // use global variables to pass large strings to avoid shell escaping issues with runPython
        pyodide.globals.set('schema_str', parseSchema);
        pyodide.globals.set('file_content', fileContent);
        pyodide.globals.set('filename', filename);
        
        result = pyodide.runPython('parse(schema_str, file_content, filename)').toJs({ dict_converter: Object.fromEntries });
        break;
        
      default:
        throw new Error(`Unknown command: ${command}`);
    }
    
    self.postMessage({ id, result, success: true });
  } catch (error) {
    const errorMsg = error.message || String(error);
    
    // Classify error for UI
    let errorType = 'UNKNOWN_ERROR';
    if (errorMsg.includes('timeout')) errorType = 'WORKER_TIMEOUT';
    else if (errorMsg.includes('parse')) errorType = 'PARSER_ERROR';
    else if (errorMsg.includes('schema')) errorType = 'SCHEMA_MISMATCH';
    
    self.postMessage({
      id,
      success: false,
      error: errorMsg,
      errorType,
      source: 'parser',
    });
  }
};
