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
  
  console.log('[Pyodide] Mounting Python core modules...');
  
  // Create directory structure
  pyodide.FS.mkdir('/python_core');
  pyodide.FS.mkdir('/python_core/extractors');
  pyodide.FS.mkdir('/python_core/database');
  pyodide.FS.mkdir('/python_core/semantic_map');
  pyodide.FS.mkdir('/python_core/utils');
  
  // Core worker files
  const coreFiles = [
    'cfg.py',
    'errors.py',
    'manifest.py',
    'extractor_worker.py',
    'semantic_map_worker.py',
  ];
  
  for (const file of coreFiles) {
    const response = await fetch(`/python_core/${file}`);
    if (!response.ok) {
      console.error(`[Pyodide] Failed to fetch ${file}: ${response.statusText}`);
      continue;
    }
    const content = await response.text();
    pyodide.FS.writeFile(`/python_core/${file}`, content);
    console.log(`[Pyodide] Mounted: /python_core/${file}`);
  }
  
  // Extractor files
  const extractorFiles = [
    '__init__.py',
    'base.py',
    'json_.py',
    'jsonl_.py',
    'csv_.py',
    'csv_multi.py',
    'json_label_values.py',
  ];
  
  for (const file of extractorFiles) {
    const response = await fetch(`/python_core/extractors/${file}`);
    if (!response.ok) {
      console.error(`[Pyodide] Failed to fetch extractors/${file}: ${response.statusText}`);
      continue;
    }
    const content = await response.text();
    pyodide.FS.writeFile(`/python_core/extractors/${file}`, content);
    console.log(`[Pyodide] Mounted: /python_core/extractors/${file}`);
  }
  
  // Database files
  const dbFiles = ['db_session.py', 'schema.sql'];
  for (const file of dbFiles) {
    const response = await fetch(`/python_core/database/${file}`);
    if (!response.ok) {
      console.error(`[Pyodide] Failed to fetch database/${file}: ${response.statusText}`);
      continue;
    }
    const content = await response.text();
    pyodide.FS.writeFile(`/python_core/database/${file}`, content);
    console.log(`[Pyodide] Mounted: /python_core/database/${file}`);
  }
  
  // Semantic map files
  const semanticMapFiles = [
    '__init__.py',
    'map_utils.py',
    'action_message_builder.py',
    'deduplicate_events.py',
  ];
  
  for (const file of semanticMapFiles) {
    const response = await fetch(`/python_core/semantic_map/${file}`);
    if (!response.ok) {
      console.error(`[Pyodide] Failed to fetch semantic_map/${file}: ${response.statusText}`);
      continue;
    }
    const content = await response.text();
    pyodide.FS.writeFile(`/python_core/semantic_map/${file}`, content);
    console.log(`[Pyodide] Mounted: /python_core/semantic_map/${file}`);
  }
  
  // Utils files
  const utilFiles = [
    '__init__.py',
    'filter_builder.py',
    'json_utils.py',
    'time_utils.py',
    'misc.py',
  ];
  
  for (const file of utilFiles) {
    const response = await fetch(`/python_core/utils/${file}`);
    if (!response.ok) {
      console.error(`[Pyodide] Failed to fetch utils/${file}: ${response.statusText}`);
      continue;
    }
    const content = await response.text();
    pyodide.FS.writeFile(`/python_core/utils/${file}`, content);
    console.log(`[Pyodide] Mounted: /python_core/utils/${file}`);
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

  // Load config.yaml and inject into Python globals
  console.log('[Pyodide] Loading config.yaml...');
  let config;
  try {
    const configResponse = await fetch('/config.yaml');
    const configText = await configResponse.text();
    
    // Parse YAML in JavaScript (we'll need to add js-yaml or use simple parsing)
    // For now, inject the raw values directly
    pyodide.runPython(`
import builtins

# Global config variables injected from config.yaml
builtins.DB_PATH = "/mnt/data/timeline.db"
builtins.SCHEMA_PATH = "/python_core/database/schema.sql"
builtins.BATCH_SIZE = 500
builtins.TEMP_ZIP_DATA_STORAGE = "/mnt/data/tmpstore"
builtins.MANIFESTS_DIR = "/manifests"

print("[Pyodide] Config globals injected:", DB_PATH, SCHEMA_PATH, BATCH_SIZE)
    `);
    console.log('[Pyodide] Config injected into Python globals');
  } catch (error) {
    console.error('[Pyodide] Failed to load config.yaml:', error);
  }

  // The files are written to the root of Pyodide's filesystem
  // Execute the bridge module directly to load all functions into the global namespace
  pyodide.runPython(`
import sys
# Add python_core to path
if '/python_core' not in sys.path:
    sys.path.insert(0, '/python_core')
if '/' not in sys.path:
    sys.path.insert(0, '/')

# Import worker modules
try:
    import extractor_worker
    print("[Pyodide] Imported extractor_worker")
except Exception as e:
    print(f"[Pyodide] Error importing extractor_worker: {e}")

try:
    import semantic_map_worker
    print("[Pyodide] Imported semantic_map_worker")
except Exception as e:
    print(f"[Pyodide] Error importing semantic_map_worker: {e}")

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
      case 'extract':
        // Call Python extractor_worker
        const { platform, givenName } = args;
        pyodide.globals.set('platform', platform);
        pyodide.globals.set('given_name', givenName);
        
        result = await pyodide.runPythonAsync(`
import extractor_worker
result = extractor_worker.extract(platform, given_name)
result
`);
        result = result.toJs({ dict_converter: Object.fromEntries });
        break;
      
      case 'semantic_map':
        // Call Python semantic_map_worker
        const { platform: mapPlatform, uploadId } = args;
        pyodide.globals.set('platform', mapPlatform);
        pyodide.globals.set('upload_id', uploadId);
        
        await pyodide.runPythonAsync(`
import semantic_map_worker
semantic_map_worker.map(platform, upload_id)
`);
        
        // Get result counts from DB
        result = await pyodide.runPythonAsync(`
from database.db_session import DatabaseSession
import cfg

with DatabaseSession(cfg.DB_PATH, use_dict_factory=True) as conn:
    events_count = conn.execute(
        'SELECT COUNT(*) as count FROM events WHERE upload_id = ?', 
        (upload_id,)
    ).fetchone()['count']
    
    devices_count = conn.execute(
        'SELECT COUNT(*) as count FROM auth_devices_initial WHERE upload_id = ?', 
        (upload_id,)
    ).fetchone()['count']
    
    result = {
        'status': 'success',
        'events_count': events_count,
        'devices_count': devices_count
    }
result
`);
        result = result.toJs({ dict_converter: Object.fromEntries });
        break;

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
