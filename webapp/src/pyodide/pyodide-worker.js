/* global importScripts, jsyaml, loadPyodide */
// pyodide-worker.js
// SOURCE: webapp/src/pyodide-worker.js
// NOTE: This file is automatically copied to public/ during build (npm run sync-assets).
// DO NOT EDIT the version in the public/ folder.


importScripts('./vendor/js-yaml.min.js');
importScripts('./pyodide/pyodide.js');

// ponytail: lightweight worker logger matching webapp/src/utils/logger.js
const LOG_LEVELS = { DEBUG: 10, INFO: 20, WARN: 30, ERROR: 40, SILENT: 50 };
var workerLogLevel = LOG_LEVELS.INFO;
var showWorkerPrefix = true;

function createWorkerLogger(name) {
  var prefix = '[' + name + ']';
  return {
    debug: function() {
      if (workerLogLevel <= LOG_LEVELS.DEBUG) {
        var args = Array.prototype.slice.call(arguments);
        console.debug.apply(console, showWorkerPrefix ? [prefix].concat(args) : args);
      }
    },
    info: function() {
      if (workerLogLevel <= LOG_LEVELS.INFO) {
        var args = Array.prototype.slice.call(arguments);
        console.info.apply(console, showWorkerPrefix ? [prefix].concat(args) : args);
      }
    },
    warn: function() {
      if (workerLogLevel <= LOG_LEVELS.WARN) {
        var args = Array.prototype.slice.call(arguments);
        console.warn.apply(console, showWorkerPrefix ? [prefix].concat(args) : args);
      }
    },
    error: function() {
      if (workerLogLevel <= LOG_LEVELS.ERROR) {
        var args = Array.prototype.slice.call(arguments);
        console.error.apply(console, showWorkerPrefix ? [prefix].concat(args) : args);
      }
    }
  };
}

const logger = createWorkerLogger('Pyodide Worker');

// Same line shape as the Python-side PERFORMANCE_MEMORY lines (python_core/performance.py).
// self.performance.memory is Chrome-only.
function logPerformanceMemory(stage, durationMs, extra) {
  const parts = ['stage=' + stage];
  if (durationMs !== undefined) parts.push('dur_ms=' + durationMs.toFixed(1));
  if (extra) {
    for (const key in extra) parts.push(key + '=' + extra[key]);
  }
  if (self.performance && self.performance.memory) {
    parts.push('heap_mb=' + Math.round(self.performance.memory.usedJSHeapSize / 1048576));
  }
  logger.info('PERFORMANCE_MEMORY ' + parts.join(' '));
}


let pyodide;
let pyodideReadyPromise;
let config = null;
let baseUrl = null; // e.g. "https://.../data-export-gui/"
let opfsMountPoint = null; // e.g. "/mnt/data" — Emscripten path where OPFS root is mounted
const isFirefox = navigator.userAgent.toLowerCase().includes('firefox');
const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent); // excludes Chrome (which also contains 'Safari')

function getBaseUrl() {
  const workerUrl = self.location.href;
  return workerUrl.substring(0, workerUrl.lastIndexOf('/') + 1);
}

function buildResourceUrl(resourcePath) {
  return baseUrl + resourcePath.replace(/^\//, '');
}

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
  /* Idempotent: creates mount-point dirs, unmounts if already mounted, then mounts OPFS root at mountPoint. */
  const opfsRoot = await navigator.storage.getDirectory();
  
  const parts = mountPoint.split('/').filter(p => p);
  let currentPath = '';
  for (const part of parts) {
    currentPath += `/${part}`;
    try { 
      pyInstance.FS.mkdir(currentPath); 
    } catch (e) { 
      // ignore mkdir failures if dir already exists
    }
  }

  try {
    pyInstance.FS.unmount(mountPoint);
  } catch (e) {
    // ignore unmount failures if not mounted
  }

  await pyInstance.mountNativeFS(mountPoint, opfsRoot);
  return mountPoint;
}




async function extractPythonCoreZip(pyInstance, pyCorePath) {
  /* Fetches python_core.zip and extracts it, stripping the top-level python_core/ directory prefix so contents land directly in pyCorePath. */
  const zipResponse = await fetch('./python_core.zip');
  if (!zipResponse.ok) {
    throw new Error(`Failed to fetch python_core.zip: ${zipResponse.statusText}`);
  }
  const zipBuffer = await zipResponse.arrayBuffer();
  const zipUint8 = new Uint8Array(zipBuffer);
  
  // Write zip to filesystem
  const zipPath = '/tmp/python_core.zip';
  pyInstance.FS.writeFile(zipPath, zipUint8);
  
  // Unzip using Python's zipfile module, skipping the top-level python_core directory
  await pyInstance.runPythonAsync(`
import zipfile
import os

zip_path = '${zipPath}'
extract_to = '${pyCorePath}'

os.makedirs(extract_to, exist_ok=True)

with zipfile.ZipFile(zip_path, 'r') as z:
    for item in z.infolist():
        # Skip the top-level directory and only extract actual files/subdirs
        parts = item.filename.split('/')
        if len(parts) > 1 and parts[0] == 'python_core':
            # Get the path without the 'python_core/' prefix
            subpath = '/'.join(parts[1:])
            if subpath and not subpath.endswith('/'):
                # Extract with correct target path
                z.extract(item, extract_to)
                # Move file to correct location (without python_core prefix)
                import shutil
                src = os.path.join(extract_to, item.filename)
                dst = os.path.join(extract_to, subpath)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(src):
                    shutil.move(src, dst)

# Clean up empty python_core directory if it exists
import shutil
python_core_dir = os.path.join(extract_to, 'python_core')
if os.path.exists(python_core_dir):
    shutil.rmtree(python_core_dir)

os.remove(zip_path)
  `);
}


async function installDeps(pyodide) {
  /* 1. Load Pyodide-native packages (+ their transitive deps) via loadPackage — served from /pyodide/.
     2. micropip.install pure-Python wheels from /wheels/ (no network calls). */

  const failedPackages = [];

  // Step 1: Pyodide-native packages (built for emscripten; must come from indexURL=/pyodide/)
  try {
    const pkgIndexRes = await fetch(buildResourceUrl('pyodide/pyodide_packages_index.json'));
    if (!pkgIndexRes.ok) throw new Error('pyodide_packages_index.json missing');
    const pkgNames = await pkgIndexRes.json();
    logger.debug('Loading Pyodide-native packages:', pkgNames);
    await pyodide.loadPackage(pkgNames);
  } catch (error) {
    logger.error('Failed to load Pyodide packages:', error.message || String(error));
    failedPackages.push('pyodide_packages_index');
  }

  // Step 2: Pure-Python wheels via micropip (hjson, json5, typer, tenacity, exrex, UA-Extract, etc.)
  const wheelsBaseUrl = buildResourceUrl(config.paths.wheels);
  try {
    const indexResponse = await fetch(wheelsBaseUrl + '/wheels_index.json?t=' + Date.now());
    if (!indexResponse.ok) throw new Error('wheels_index.json missing (' + indexResponse.status + ')');
    const wheelFiles = await indexResponse.json();
    const micropip = pyodide.pyimport('micropip');
    for (var j = 0; j < wheelFiles.length; j++) {
      var wheelUrl = wheelsBaseUrl + '/' + wheelFiles[j];
      logger.debug('Installing wheel:', wheelUrl);
      try {
        await micropip.install(wheelUrl);
      } catch (error) {
        logger.error('Failed to install ' + wheelFiles[j] + ':', error.message || String(error));
        failedPackages.push(wheelFiles[j]);
      }
    }
    logger.info('Installed ' + wheelFiles.length + ' Python wheels');
  } catch (error) {
    logger.error('Failed to fetch wheels_index.json:', error.message || String(error));
    failedPackages.push('wheels_index.json');
  }

  if (failedPackages.length > 0) {
    self.postMessage({ type: 'packageInstallFailure', packages: failedPackages });
  }
}

async function loadManifestOnDemand(platform) {
  const manifestsPath = config.paths.manifests;
  const targetFile = `${manifestsPath}/${platform}.yaml`;
  
  try {
    pyodide.FS.lookupPath(targetFile);
    return; // Already loaded
  } catch (e) {
    // Fetch if not present
  }

  const manifestsBaseUrl = buildResourceUrl(config.paths.manifests);
  const res = await fetch(`${manifestsBaseUrl}/${platform}.yaml`);
  if (res.ok) {
    const txt = await res.text();
    pyodide.FS.writeFile(targetFile, txt);
    logger.debug(`Loaded manifest for platform: ${platform}`);
  } else {
    throw new Error(`Failed to load manifest for platform ${platform}`);
  }
}






async function initPyodide() {
  try {
    logger.info('Starting initialization...');
    
    config = await loadConfig();
    if (config && config.LOG_LEVEL) {
      var upper = String(config.LOG_LEVEL).toUpperCase();
      if (LOG_LEVELS[upper] !== undefined) workerLogLevel = LOG_LEVELS[upper];
    }
    baseUrl = getBaseUrl();
    logger.debug(`Computed base URL: ${baseUrl}`);
    
    const pyodideInitStart = self.performance.now();
    pyodide = await loadPyodide({indexURL: buildResourceUrl('pyodide/')});
    logPerformanceMemory('pyodide_init', self.performance.now() - pyodideInitStart);

    // Cross-browser memory reading for performance.py's _MemorySampler — unlike
    // performance.memory (Chrome-only), WASM linear memory size is just an
    // ArrayBuffer.byteLength read, no fingerprint-guarded API involved.
    self.getWasmMemoryBytes = () => pyodide.HEAP8.buffer.byteLength;
    
    const pyCorePath = config.paths.python_core;
    await extractPythonCoreZip(pyodide, pyCorePath);
    
    const schemaUrl = buildResourceUrl(config.paths.schema);
    const schemaResponse = await fetch(schemaUrl);
    if (schemaResponse.ok) {
      const content = await schemaResponse.text();
      pyodide.FS.writeFile(config.paths.schema, content);
    } else {
      throw new Error(`Failed to fetch schema.sql from ${schemaUrl}: ${schemaResponse.statusText}`);
    }

    if (navigator.storage && navigator.storage.getDirectory) {
      const dbPathParts = config.database.db_path.split('/');
      const mountPoint = dbPathParts.slice(0, -1).join('/');
      opfsMountPoint = await setupOPFSMount(pyodide, mountPoint);
    }

    pyodide.runPython(`
import builtins

builtins.DB_PATH = "${config.database.db_path}"
builtins.SCHEMA_PATH = "${config.paths.schema}"
builtins.TEMP_ZIP_DATA_STORAGE = "${config.storage.temp_zip_storage}"
builtins.MANIFESTS_DIR = "${config.paths.manifests}"
builtins.PYTHON_CORE = "${config.paths.python_core}"
builtins.LOG_LEVEL = "${config.LOG_LEVEL || (typeof process !== 'undefined' && process.env && process.env.VUE_APP_LOG_LEVEL) || 'INFO'}"
builtins.IS_FIREFOX = ${isFirefox ? 'True' : 'False'}
builtins.IS_SAFARI = ${isSafari ? 'True' : 'False'}
builtins.PERFORMANCE_MEMORY_SAMPLING = ${config.performance?.memory_sampling_enabled ? 'True' : 'False'}
builtins.PERFORMANCE_MEMORY_SAMPLING_INTERVAL_MS = ${config.performance?.memory_sampling_interval_ms || 100}
    `);

    pyodide.FS.mkdir(config.paths.manifests);

    await installDeps(pyodide);


    await showPackages(pyodide);

   

    pyodide.runPython(`
import sys
sys.path.insert(0, '${config.paths.python_core}')
sys.path.insert(0, '/')
from runtime.pyodide_utils import init_pyodide
init_pyodide()
    `);
    
    logger.info('Initialization complete');
    return pyodide;
  } catch (error) {
    logger.error('FATAL initialization error:', error.message);
    logger.error('Stack trace:', error.stack);
    throw error;
  }
}





async function initPyodideWithRetry() {
  /* Retries initPyodide up to 3 times with 100/200/400ms exponential backoff; each attempt has a 30s timeout. */
  const MAX_RETRIES = 3;
  const INIT_TIMEOUT = 30000; // 30 seconds per attempt
  
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      // Race between init and timeout
      const result = await Promise.race([
        initPyodide(),
        new Promise((resolve, reject) =>
          setTimeout(
            () => reject(new Error('Pyodide initialization timeout')),
            INIT_TIMEOUT
          )
        )
      ]);
      return result;
    } catch (error) {
      const errorMsg = error.message || String(error);
      console.warn(
        `Pyodide init failed (attempt ${attempt}/${MAX_RETRIES}): ${errorMsg}`
      );
      
      if (attempt === MAX_RETRIES) {
        throw error;
      }
      const backoffMs = 100 * Math.pow(2, attempt - 1);
      await new Promise(resolve => setTimeout(resolve, backoffMs));
    }
  }
}

pyodideReadyPromise = initPyodideWithRetry();




async function flushOPFSDatabase() {
  /* Firefox/Safari: bypass Emscripten syncfs (crashes on stat()/BigInt) by manually writing DB bytes to OPFS via SyncAccessHandle. Chrome: standard FS.syncfs. */
  if (isFirefox || isSafari) {
    logger.debug('Firefox/Safari: manually syncing db to OPFS.');
    try {
      const dbBytes = pyodide.FS.readFile(config.database.db_path);
      const opfsRoot = await navigator.storage.getDirectory();
      const dbFileName = config.database.db_path.split('/').pop();
      const dbHandle = await opfsRoot.getFileHandle(dbFileName, { create: true });
      const accessHandle = await dbHandle.createSyncAccessHandle();
      accessHandle.truncate(0);
      accessHandle.write(dbBytes, { at: 0 });
      accessHandle.flush();
      accessHandle.close();
      return;
    } catch (e) {
      logger.error('Manual OPFS sync failed:', e);
      return;
    }
  }
  return new Promise((resolve, reject) => {
    pyodide.FS.syncfs(false, (err) => {
      if (err) {
        logger.error('sync to opfs failed:', err);
        reject(err);
      } else {
        logger.debug('database flushed to opfs');
        resolve();
      }
    });
  });
}


async function showPackages(pyodide) {
  try {
    const result = await pyodide.runPythonAsync(`
import micropip, json
json.dumps(list(micropip.list().keys()))
    `);
    logger.debug('Installed packages:', JSON.parse(result));
  } catch (e) {
    logger.warn('Could not list packages:', e);
  }
}


self.onmessage = async (event) => {
  const { id, command, args } = event.data;
  
  try {
    // Wait for Pyodide to be ready
    try {
      await Promise.race([
        pyodideReadyPromise,
        new Promise((resolve, reject) =>
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
        result = { status: 'warmup_complete' };
        break;
      }


      case 'run_pipeline': {
        const { platform, givenName } = args;
        logger.info(`run_pipeline called: platform=${platform}, givenName=${givenName}`);

        // The JSON pipeline summary (python_core/run.py) comes back as `result.performance_summary`
        // below rather than being scraped from console output — CSV building/download from it
        // happens in pyodide-client.js's executeUpload(), which runs on the main thread and has
        // DOM access (this worker doesn't).

        await loadManifestOnDemand(platform);

        if (opfsMountPoint) {
          logger.debug(`Remounting OPFS at ${opfsMountPoint}...`);
          try {
            await setupOPFSMount(pyodide, opfsMountPoint);
          } catch (e) {
            logger.error('OPFS remount failed:', e);
          }
        }

        // performance.mark/measure pairs show up in DevTools' Performance tab timeline.
        let lastStageMark = null;
        self.reportProgress = (stage, progress) => {
          const markName = 'pipeline:' + stage;
          self.performance.mark(markName);
          if (lastStageMark) {
            try {
              self.performance.measure('pipeline:' + lastStageMark.stage + '->' + stage, lastStageMark.name, markName);
            } catch (e) { /* ignore if a mark went missing */ }
          }
          lastStageMark = { stage, name: markName };
          // Fires when this stage is about to start, not when it finishes — the matching
          // `stage=<name> dur_ms=...` line from python_core/performance.py has the actual duration.
          logPerformanceMemory(stage + '_start', undefined, { progress });
          self.postMessage({ id, type: 'progress', stage, progress });
        };

        pyodide.globals.set('platform', platform);
        pyodide.globals.set('given_name', givenName);

        const pipelineStart = self.performance.now();
        result = await pyodide.runPythonAsync(`
import run
run.run(platform, given_name)
`);

        self.performance.mark('pipeline:complete');
        if (lastStageMark) {
          try {
            self.performance.measure('pipeline:' + lastStageMark.stage + '->complete', lastStageMark.name, 'pipeline:complete');
          } catch (e) { /* ignore if a mark went missing */ }
        }
        logPerformanceMemory('pipeline_total', self.performance.now() - pipelineStart);

        delete self.reportProgress;

        await flushOPFSDatabase();

        result = result.toJs({ dict_converter: Object.fromEntries });
        logger.debug(`run_pipeline result:`, result);
        break;
      }


      case 'get_whitelist': {
        // Returns file path patterns from the manifest for a given platform
        const { platform: wlPlatform } = args;
        await loadManifestOnDemand(wlPlatform);
        pyodide.globals.set('platform', wlPlatform);
        
        result = await pyodide.runPythonAsync(`
from manifest import Manifest
Manifest(platform=platform).file_paths()
`);
        result = result.toJs();
        break;
      }



      default:
        throw new Error(`Unknown command: ${command}`);
    }
    
    self.postMessage({ id, result, success: true });
    logger.debug(`Command '${command}' completed successfully`);
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
