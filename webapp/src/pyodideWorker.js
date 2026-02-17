// pyodideWorker.js
// SOURCE: webapp/src/pyodideWorker.js
// NOTE: This file is automatically copied to public/ during build (npm run sync-assets).
// DO NOT EDIT the version in the public/ folder.

importScripts('https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js');

let pyodide;
let pyodideReadyPromise;
let initError = null; // Track init failures for error reporting

async function initPyodide() {
  pyodide = await loadPyodide();
  console.log('[Pyodide] Loaded Pyodide core');
  
  console.log('[Pyodide] Loading built-in packages: pyyaml, pytz, pandas');
  await pyodide.loadPackage(['pyyaml', 'pytz', 'pandas']);
  console.log('[Pyodide] Built-in packages loaded');

  console.log('[Pyodide] Loading micropip for installing hjson, json5');
  await pyodide.loadPackage('micropip');
  console.log('[Pyodide] Micropip loaded, importing micropip module...');
  const micropip = pyodide.pyimport('micropip');
  console.log('[Pyodide] Micropip module imported, starting installation...');
  
  try {
    console.log('[Pyodide] Installing hjson...');
    await micropip.install('hjson');
    console.log('[Pyodide] hjson installed');
    
    console.log('[Pyodide] Installing json5...');
    await micropip.install('json5');
    console.log('[Pyodide] json5 installed');
  
    
    console.log('[Pyodide] All JSON packages installed successfully');
  } catch (error) {
    console.error('[Pyodide] JSON package installation error:', error);
    console.error('[Pyodide] Error details:', error.message || String(error));
    console.warn('[Pyodide] Parsing will continue with available parsers');
  }

  // Fetch and mount our custom Python parser logic
  // Now mounting the centralized Python code
  
  // 1. Mount parsers (recursively or list known files)
  const parserFiles = [
    'pyodide.py',
    'base.py',
    'errors.py',
    'parseresult.py',
    'json_.py',
    'jsonl_.py',
    'csv_.py',
    'json_label_values.py',
    'csv_multi.py',
    'schema_utils.py',
    'time_utils.py'
  ];

  // Create package structure in Pyodide
  pyodide.FS.mkdir('/parsers');
  pyodide.FS.mkdir('/python'); // for root-level scripts

  for (const file of parserFiles) {
    const response = await fetch(`/python_core/parsers/${file}`);
    if (!response.ok) {
        console.error(`[Pyodide] Failed to fetch parser ${file}: ${response.statusText}`);
        continue;
    }
    const content = await response.text();
    // Some files might expect to be at root? 
    // The previous setup had them at root. The refactor put them in `python_core/parsers/`.
    // We should put them in `parsers/` or root?
    // Let's mimic the new structure: put them in `/parsers/` and add `/` to sys.path
    pyodide.FS.writeFile(`/parsers/${file}`, content);
    console.log(`[Pyodide] Mounted: /parsers/${file}`);
  }

  // 2. Mount Worker Scripts (Ingest & Compiler)
  const workerFiles = ['ingest_worker.py', 'schema_compiler.py'];
  for (const file of workerFiles) {
      const response = await fetch(`/python_core/${file}`);
      if (response.ok) {
          const content = await response.text();
          pyodide.FS.writeFile(`/${file}`, content); // Root level for easy import
          console.log(`[Pyodide] Mounted: /${file}`);
      } else {
          console.error(`[Pyodide] Failed to fetch ${file}`);
      }
  }

  // Mount OPFS (Shared Buffer)
  if (navigator.storage && navigator.storage.getDirectory) {
      const opfsRoot = await navigator.storage.getDirectory();
      const mountPoint = "/mnt/data";
      pyodide.FS.mkdir(mountPoint);
      pyodide.mountNativeFS(mountPoint, opfsRoot);
      console.log(`[Pyodide] Mounted OPFS to ${mountPoint}`);
  }

  // Mount Schemas (from public/schemas to /schemas)
  // We can't list directory via fetch easily without a manifest.
  // We'll rely on the worker to know what to load or mount them one by one if we knew them.
  // Ideally, we pass the schemas list or content.
  // For now, let's assume we might need to fetch them in the python script or pass list.
  // But ingest_worker.py expects /schemas dir.
  // We can try to mount the schema dir if we convert it to a zip?
  // Or just mkdir /schemas and fetch known schemas.
  // Let's create the directory so python doesn't crash on os.listdir check, 
  // though it will be empty unless we fill it.
  pyodide.FS.mkdir('/manifests');
  
  // Note: Schema loading is currently separate (User passes YAML string), 
  // or we need a way to list available schemas. 
  // ingest_worker.py tries `os.listdir('/manifests')`.
  // We should fetch known schemas (hardcoded list or manifest) and write them.
  const knownSchemas = ['apple.yaml', 'facebook.yaml', 'instagram.yaml', 'discord.yaml', 'all_fields.yaml'];
  for (const s of knownSchemas) {
      const res = await fetch(`/manifests/${s}`);
      if (res.ok) {
          const txt = await res.text();
          pyodide.FS.writeFile(`/manifests/${s}`, txt);
      }
  }
  
  console.log('[Pyodide] All modules mounted');

  // The files are written to the root of Pyodide's filesystem
  // Execute the bridge module directly to load all functions into the global namespace
  pyodide.runPython(`
import sys
# Add parsers to path
if '/parsers' not in sys.path:
    sys.path.insert(0, '/parsers')
if '/' not in sys.path:
    sys.path.insert(0, '/')

# Import Ingest Logic
try:
    import ingest_worker
    print("[Pyodide] Imported ingest_worker")
except Exception as e:
    print(f"[Pyodide] Error importing ingest_worker: {e}")

# Load legacy bridge for 'group_schema_by_path' and 'parse' if still used by UI
try:
    with open('/parsers/pyodide.py', 'r') as f:
        bridge_code = f.read()
        exec(bridge_code, globals())
except Exception as e:
    print(f"[Pyodide] Warning: could not load legacy bridge: {e}")

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
      case 'ingest':
        // Trigger Ingest Loop
        // ingest_loop is async, so we use runPythonAsync or wrap in a way that returns a promise
        await pyodide.runPythonAsync(`
import asyncio
try:
    await ingest_worker.ingest_loop()
    result = "Ingest Complete"
except Exception as e:
    import traceback
    traceback.print_exc()
    result = f"Error: {e}"
`);
        result = pyodide.globals.get('result');
        break;

      case 'test_environment':
        result = pyodide.runPython('test_environment()').toJs({ dict_converter: Object.fromEntries });
        break;
      
      
      // Legacy commands support via direct python bridge for now, but should eventually migrate
      case 'group_schema_by_path':
        const { schemaYaml } = args;
        pyodide.globals.set('schema_str', schemaYaml);
        // We need to ensure group_schema_by_path is available. 
        // It resides in pyodide.py which we executed in globals() earlier
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
