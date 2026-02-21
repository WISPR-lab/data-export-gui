// pyodide-worker.js
// SOURCE: webapp/src/pyodide-worker.js
// NOTE: This file is automatically copied to public/ during build (npm run sync-assets).
// DO NOT EDIT the version in the public/ folder.

// const { reject } = require("lodash");

// importScripts('https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js');
importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js');
importScripts('https://cdn.jsdelivr.net/npm/js-yaml@4.1.0/dist/js-yaml.min.js');

let pyodide;
let pyodideReadyPromise;
let config = null;
let opfsMountPoint = null; // e.g. "/mnt/data" — Emscripten path where OPFS root is mounted
const isFirefox = navigator.userAgent.toLowerCase().includes('firefox');

async function loadConfig() {
  const response = await fetch('./config.yaml');
  if (!response.ok) {
    throw new Error('Failed to load config.yaml: ' + response.statusText);
  }
  const text = await response.text();
  config = jsyaml.load(text);
  return config;
}

async function setupOPFSMount(pyInstance, mountPoint) {
  const opfsRoot = await navigator.storage.getDirectory();
  
  const parts = mountPoint.split('/').filter(p => p);
  let currentPath = '';
  for (const part of parts) {
    currentPath += `/${part}`;
    try { 
      pyInstance.FS.mkdir(currentPath); 
    } catch (e) { 
    }
  }

  try {
    pyInstance.FS.unmount(mountPoint);
    console.log(`[Pyodide Worker] Unmounted stale OPFS at ${mountPoint}`);
  } catch (e) {
    //
  }

  await pyInstance.mountNativeFS(mountPoint, opfsRoot);
  console.log(`[Pyodide Worker] OPFS successfully mounted to ${mountPoint}`);
  return mountPoint;
}

async function initPyodide() {
  console.log('[Pyodide] Loading config...');
  config = await loadConfig();
  console.log('[Pyodide] Config loaded:', config);
  
  pyodide = await loadPyodide();
  console.log('[Pyodide] Loaded Pyodide core');
  
  console.log('[Pyodide] Loading built-in packages: pyyaml, pytz, pandas, sqlite3');
  await pyodide.loadPackage(['pyyaml', 'pytz', 'pandas', 'sqlite3']);
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
  
  // Fetch dynamic Python manifest
  let pythonManifest;
  try {
    const manifestResponse = await fetch('./_dynamic_py_manifest.json');
    if (!manifestResponse.ok) {
      throw new Error(`Failed to fetch manifest: ${manifestResponse.statusText}`);
    }
    pythonManifest = await manifestResponse.json();
    console.log('[Pyodide] Loaded Python manifest:', pythonManifest);
  } catch (error) {
    console.error('[Pyodide] Failed to load manifest, falling back to hardcoded lists:', error);
    pythonManifest = {
      core_files: ['errors.py', 'manifest.py', 'db_session.py', 'extractor_worker.py', 'semantic_map_worker.py'],
      extractors: ['__init__.py', 'base.py', 'json_.py', 'jsonl_.py', 'csv_.py', 'csv_multi.py', 'json_label_values.py'],
      semantic_map: ['__init__.py', 'map_utils.py', 'action_message_builder.py', 'deduplicate_events.py'],
      utils: ['__init__.py', 'filter_builder.py', 'safe_path_utils.py', 'json_utils.py', 'time_utils.py', 'misc.py']
    };
  }
  
  // Create directory structure
  const pyCorePath = config.paths.python_core;
  pyodide.FS.mkdir(pyCorePath);
  pyodide.FS.mkdir(`${pyCorePath}/extractors`);
  pyodide.FS.mkdir(`${pyCorePath}/semantic_map`);
  pyodide.FS.mkdir(`${pyCorePath}/utils`);
  
  const fetchBaseUrl = pyCorePath.startsWith('/') ? `.${pyCorePath}` : `./${pyCorePath}`;
  // Mount core files
  for (const file of pythonManifest.core_files) {
    const response = await fetch(`${fetchBaseUrl}/${file}`);
    if (!response.ok) {
      console.error(`[Pyodide] Failed to fetch ${file}: ${response.statusText}`);
      continue;
    }
    const content = await response.text();
    pyodide.FS.writeFile(`${pyCorePath}/${file}`, content);
    console.log(`[Pyodide] Mounted: ${pyCorePath}/${file}`);
  }
  
  // Mount extractor files
  for (const file of pythonManifest.extractors) {
    const response = await fetch(`${fetchBaseUrl}/extractors/${file}`);
    if (!response.ok) {
      console.error(`[Pyodide] Failed to fetch extractors/${file}: ${response.statusText}`);
      continue;
    }
    const content = await response.text();
    pyodide.FS.writeFile(`${pyCorePath}/extractors/${file}`, content);
    console.log(`[Pyodide] Mounted: ${pyCorePath}/extractors/${file}`);
  }
  
  // schema.sql lives at the repo root, served from /schema.sql
    const response = await fetch(config.paths.schema.startsWith('/') ? `.${config.paths.schema}` : `./${config.paths.schema}`);
    if (!response.ok) {
      console.error(`[Pyodide] Failed to fetch schema.sql: ${response.statusText}`);
    } else {
      const content = await response.text();
      pyodide.FS.writeFile(config.paths.schema, content);
      console.log(`[Pyodide] Mounted: ${config.paths.schema}`);
    }

  // Mount semantic map files
  for (const file of pythonManifest.semantic_map) {
    const response = await fetch(`${fetchBaseUrl}/semantic_map/${file}`);
    if (!response.ok) {
      console.error(`[Pyodide] Failed to fetch semantic_map/${file}: ${response.statusText}`);
      continue;
    }
    const content = await response.text();
    pyodide.FS.writeFile(`${pyCorePath}/semantic_map/${file}`, content);
    console.log(`[Pyodide] Mounted: ${pyCorePath}/semantic_map/${file}`);
  }
  
  // Mount utils files
  for (const file of pythonManifest.utils) {
    const response = await fetch(`${fetchBaseUrl}/utils/${file}`);
    if (!response.ok) {
      console.error(`[Pyodide] Failed to fetch utils/${file}: ${response.statusText}`);
      continue;
    }
    const content = await response.text();
    pyodide.FS.writeFile(`${pyCorePath}/utils/${file}`, content);
    console.log(`[Pyodide] Mounted: ${pyCorePath}/utils/${file}`);
  }

  // Mount OPFS (Shared Buffer)
  //     try { pyodide.FS.mkdir(mountPoint); } catch (e) {}

  //     try {
  //       await pyodide.mountNativeFS(mountPoint, opfsRoot);
  //       opfsMountPoint = mountPoint;
  //       console.log(`[Pyodide] Mounted OPFS to ${mountPoint}`);
  //       try {
  //         const mountContents = pyodide.FS.readdir(mountPoint).filter(f => f !== '.' && f !== '..');
  //         console.log(`[Pyodide] OPFS mount contents at ${mountPoint} (at init):`, mountContents);
  //       } catch (e) {
  //         console.warn(`[Pyodide] Could not list mount point ${mountPoint}:`, e.message);
  //       }
  //     } catch (e) {
  //       console.error(`[Pyodide] Failed to mount NativeFS:`, e);
  //     }
  // }
  // Mount OPFS (Shared Buffer)
  if (navigator.storage && navigator.storage.getDirectory) {
    // Derive mount point from db_path (e.g. "/mnt/data/timeline.db" -> "/mnt/data")
    const dbPathParts = config.database.db_path.split('/');
    const mountPoint = dbPathParts.slice(0, -1).join('/');
    
    try {
      opfsMountPoint = await setupOPFSMount(pyodide, mountPoint);
    } catch (e) {
      console.error(`[Pyodide] Failed to mount NativeFS:`, e);
    }
  }

  // Mount manifests so Python can os.listdir(MANIFESTS_DIR)
  const manifestsPath = config.paths.manifests;
  const manifestsBaseUrl = manifestsPath.startsWith('/') ? `.${manifestsPath}` : `./${manifestsPath}`;
  pyodide.FS.mkdir(manifestsPath);
  const knownSchemas = ['apple.yaml', 'facebook.yaml', 'instagram.yaml', 'discord.yaml'];
  for (const s of knownSchemas) {
      const res = await fetch(`${manifestsBaseUrl}/${s}`);
      if (res.ok) {
          const txt = await res.text();
          pyodide.FS.writeFile(`${manifestsPath}/${s}`, txt);
      }
  }
  
  console.log('[Pyodide] All modules mounted');

  // Inject config into Python globals
  pyodide.runPython(`
import builtins

builtins.DB_PATH = "${config.database.db_path}"
builtins.SCHEMA_PATH = "${config.paths.schema}"
builtins.TEMP_ZIP_DATA_STORAGE = "${config.storage.temp_zip_storage}"
builtins.MANIFESTS_DIR = "${config.paths.manifests}"
builtins.IS_FIREFOX = ${isFirefox? 'True' : 'False'}


print("[Pyodide] Config loaded:", DB_PATH, SCHEMA_PATH)
  `);
  console.log('[Pyodide] Config injected into Python globals');

  // Import the worker modules into the Python runtime
  pyodide.runPython(`
import sys
# Add python_core to path
if '${config.paths.python_core}' not in sys.path:
    sys.path.insert(0, '${config.paths.python_core}')
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
  
  console.log('[Pyodide] Fully initialized and ready for use');
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
      
      // If this was the last attempt, rethrow
      if (attempt === MAX_RETRIES) {
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
 * Flush Pyodide's in-memory database to OPFS storage.
 * Synchronizes the filesystem so Python writes are persisted.
 */
async function flushOPFSDatabase() {
  if (isFirefox) {
    // Python already manually flushed the bytes to OPFS safely.
    console.log("[Pyodide Worker] Firefox detected: manually syncing db to opfs without calling syncfs() to avoid Firefox stat() crash.");
    try {
      const dbBytes = pyodide.FS.readFile('/mnt/data/timeline.db') // TODO EVENTUALLY NO HARDCODING
      const opfsRoot = await navigator.storage.getDirectory();
      const dbHandle = await opfsRoot.getFileHandle('timeline.db', { create: true });
      const accessHandle = await dbHandle.createSyncAccessHandle();
      accessHandle.truncate(0);
      accessHandle.write(dbBytes, { at: 0 });
      accessHandle.flush();
      accessHandle.close();
      return; 
    } catch (e) {
      console.error('[Pyodide Worker] Firefox manual OPFS sync failed:', e);
      return;
    }
  }
  return new Promise((resolve, reject) => {
    pyodide.FS.syncfs(false, (err) => {
      if (err) {
        console.error('[Pyodide Worker] sync to opfs failed:', err);
        reject(err);
      } else {
        console.log('[Pyodide Worker] database flushed to opfs');
        resolve();
      }
    });
  });
}

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
      case 'isPyodideReady': {
        result = { pyodideReady: typeof pyodide !== 'undefined' };
        break;
      }
      case 'warmup': {
        // Just wait for Pyodide to be ready, don't do anything else
        result = { status: 'warmup_complete' };
        break;
      }
      case 'extract': {
        // Call Python extractor_worker
        const { platform, givenName } = args;
        console.log(`[Pyodide Worker] extract called: platform=${platform}, givenName=${givenName}`);

        // Remount OPFS so Emscripten picks up files written by JS after initial mount.
        // syncfs() only syncs file contents, NOT new directory entries.
        // Unmount + remount forces a full directory rescan.
        if (opfsMountPoint) {
          console.log(`[Pyodide Worker] Remounting OPFS at ${opfsMountPoint}...`);
          try {
            await setupOPFSMount(pyodide, opfsMountPoint);
          } catch (e) {
            console.error('[Pyodide Worker] OPFS remount failed:', e);
          }
        } else {
          console.warn('[Pyodide Worker] opfsMountPoint not set — cannot remount OPFS');
        }

        // Show what Python can see in tmpstore after remount
        try {
          const tmpPath = config.storage.temp_zip_storage;
          const tmpContents = pyodide.FS.readdir(tmpPath).filter(f => f !== '.' && f !== '..');
          // console.log(`[Pyodide Worker] tmpstore visible to Python after remount (${tmpPath}):`, tmpContents);
        } catch (e) {
          console.warn(`[Pyodide Worker] tmpstore not visible after remount (${config.storage.temp_zip_storage}):`, e.message);
        }

        pyodide.globals.set('platform', platform);
        pyodide.globals.set('given_name', givenName);

        result = await pyodide.runPythonAsync(`
import extractor_worker
result = extractor_worker.extract(platform, given_name)
result
`);

        await flushOPFSDatabase();

        result = result.toJs({ dict_converter: Object.fromEntries });
        console.log(`[Pyodide Worker] extract result:`, result);
        break;
      }
        // result = result.toJs({ dict_converter: Object.fromEntries });
        // if (result.status !== 'success') {
        //   console.error('[Pyodide Worker] ❌ extractor_worker returned failure:', result);
        // } else {
        //   console.log(`[Pyodide Worker] extract result:`, result);
        // }
        // break;
      
      
      case 'semantic_map': {
        // Call Python semantic_map_worker
        const { platform: mapPlatform, uploadId } = args;
        console.log(`[Pyodide Worker] semantic_map called: platform=${mapPlatform}, uploadId=${uploadId}`);
        
        if (!uploadId) {
          throw new Error(`uploadId is missing from args: ${JSON.stringify(args)}`);
        }
        
        pyodide.globals.set('platform', mapPlatform);
        pyodide.globals.set('upload_id', uploadId);
        
        await pyodide.runPythonAsync(`
import semantic_map_worker
semantic_map_worker.map(platform, upload_id)
`);
        
        await flushOPFSDatabase();
        
        // Get result counts from DB
        result = await pyodide.runPythonAsync(`
import builtins
from db_session import DatabaseSession

with DatabaseSession(builtins.DB_PATH, use_dict_factory=True) as conn:
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
      }

      case 'get_whitelist': {
        // Returns file path patterns from the manifest for a given platform
        const { platform: wlPlatform } = args;
        pyodide.globals.set('platform', wlPlatform);
        
        result = await pyodide.runPythonAsync(`
from manifest import Manifest
m = Manifest(platform=platform)
paths = m.file_paths()
paths
`);
        result = result.toJs();
        break;
      }

      default:
        throw new Error(`Unknown command: ${command}`);
    }
    
    self.postMessage({ id, result, success: true });
    console.log(`[Pyodide Worker] Command '${command}' completed successfully`);
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
