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
let baseUrl = null; // e.g. "https://.../data-export-gui/"
let opfsMountPoint = null; // e.g. "/mnt/data" — Emscripten path where OPFS root is mounted
const isFirefox = navigator.userAgent.toLowerCase().includes('firefox');

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




async function loadRequirements(pyInstance, pyCorePath) {
  try {
    const requirementsPath = `${pyCorePath}/requirements.txt`;
    const content = pyInstance.FS.readFile(requirementsPath, { encoding: 'utf8' });
    return content
      .split('\n')
      .map(line => line.split('#')[0].trim())
      .filter(line => line && !line.startsWith('-'));
  } catch (error) {
    console.error(`[Pyodide Worker] Failed to load requirements.txt: ${error.message}`);
    return [];
  }
}



async function installDeps(pyodide, pyCorePath) {
  /* Loads builtins first, then micropip-installs remaining requirements.txt entries; posts packageInstallFailure for any that fail. */
  const builtinModules = ['pyyaml', 'pytz', 'pandas', 'sqlite3', 'regex', 'aiohttp', 'micropip'];
  await pyodide.loadPackage(builtinModules);
  const micropip = pyodide.pyimport('micropip');
  const requirements = await loadRequirements(pyodide, pyCorePath);
  const failedPackages = [];
  for (const pkg of requirements) {
    if (!builtinModules.includes(pkg)) {
      try {
        await micropip.install(pkg);
      } catch (error) {
        console.error(`[Pyodide Worker] Failed to install ${pkg}:`, error.message || String(error));
        failedPackages.push(pkg);
      }
    }
  }
  if (failedPackages.length > 0) {
    self.postMessage({ type: 'packageInstallFailure', packages: failedPackages });
  }
}

async function installUAExtract(pyodide) {
  /* Fetches wheel filename from latest_wheel.txt pointer file, then micropip-installs the wheel by absolute URL. */
  try {
    console.log(`[Pyodide Worker] installing local ua-extract wheel`);
    const micropip = pyodide.pyimport('micropip');
    const wheelsBaseUrl = buildResourceUrl(config.paths.wheels);
    const pointerUrl = `${wheelsBaseUrl}/latest_wheel.txt?t=${Date.now()}`;
    const response = await fetch(pointerUrl);
      if (!response.ok) {
        throw new Error(`Pointer file missing at ${pointerUrl} (${response.status})`);
    }
    const wheelFilename = (await response.text()).trim();
    if (!wheelFilename) throw new Error("latest_wheel.txt was empty");
    
    const wheelUrl = `${wheelsBaseUrl}/${wheelFilename}`;
    console.log(`[Pyodide Worker] Installing from absolute URL: ${wheelUrl}`);
    await micropip.install(wheelUrl);
//   const vsfWheelPath = `/tmp/${wheelsPath.split('/').pop()}`;
//   const wheelsResponse = await fetch(wheelsBaseUrl);
//   if (!wheelsResponse.ok) {
//     console.error(`[Pyodide Worker] Failed to fetch wheels directory: ${wheelsResponse.statusText}`);
//     self.postMessage({ type: 'packageInstallFailure', packages: ['ua-extract'] });
//     return;
//   }
//   const wheelsBuffer = await wheelsResponse.arrayBuffer();
//   try {
//     pyodide.FS.writeFile(vsfWheelPath, new Uint8Array(wheelsBuffer));
//     await pyodide.runPythonAsync(`
// import micropip
// await micropip.install("emfs:${vsfWheelPath}")
//       `);
    console.log("[Pyodide Worker] ua-extract installed successfully.");
    // pyodide.FS.unlink(vsfWheelPath);
  } catch (error) {
    console.error(`[Pyodide Worker] Failed to install ua-extract wheel:`, error.message || String(error));
    self.postMessage({ type: 'packageInstallFailure', packages: ['ua-extract'] });
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
    console.log(`[Pyodide Worker] Loaded manifest for platform: ${platform}`);
  } else {
    throw new Error(`Failed to load manifest for platform ${platform}`);
  }
}






async function initPyodide() {
  try {
    console.log('[Pyodide Worker] Starting initialization...');
    
    config = await loadConfig();
    baseUrl = getBaseUrl();
    console.log(`[Pyodide Worker] Computed base URL: ${baseUrl}`);
    
    pyodide = await loadPyodide();
    
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
builtins.IS_FIREFOX = ${isFirefox? 'True' : 'False'}
    `);

    pyodide.FS.mkdir(config.paths.manifests);

    await installDeps(pyodide, pyCorePath);
    await installUAExtract(pyodide);

    await showPackages(pyodide);

   

    pyodide.runPython(`
import sys
sys.path.insert(0, '${config.paths.python_core}')
sys.path.insert(0, '/')
from utils.pyodide_utils import init_pyodide
init_pyodide()
    `);
    
    console.log('[Pyodide Worker] Initialization complete');
    return pyodide;
  } catch (error) {
    console.error('[Pyodide Worker] FATAL initialization error:', error.message);
    console.error('[Pyodide Worker] Stack trace:', error.stack);
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
        new Promise((_, reject) =>
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
  /* Firefox: bypasses Emscripten syncfs (crashes on stat()) by manually reading DB bytes and writing them to OPFS via SyncAccessHandle. Chrome: uses standard FS.syncfs. */
  if (isFirefox) {
    // Python already manually flushed the bytes to OPFS safely.
    console.log("[Pyodide Worker] Firefox detected: manually syncing db to opfs without calling syncfs() to avoid Firefox stat() crash.");
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


async function showPackages(pyodide) {
  const packages = await pyodide.runPythonAsync(`
      import micropip
      packages = micropip.list()
      packages
  `);
  if (packages && packages.toJs) {
    console.log(`[Pyodide Worker] Installed packages:`, packages.toJs({ dict_converter: Object.fromEntries }));
  } else {
    console.warn('[Pyodide Worker] Could not retrieve installed packages list');
  }
};


self.onmessage = async (event) => {
  const { id, command, args } = event.data;
  console.log(`[PyodideWorker] Received message: command='${command}', id=${id}`);
  
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
        result = { status: 'warmup_complete' };
        break;
      }


      case 'run_pipeline': {
        const { platform, givenName } = args;
        console.log(`[Pyodide Worker] run_pipeline called: platform=${platform}, givenName=${givenName}`);

        await loadManifestOnDemand(platform);

        if (opfsMountPoint) {
          console.log(`[Pyodide Worker] Remounting OPFS at ${opfsMountPoint}...`);
          try {
            await setupOPFSMount(pyodide, opfsMountPoint);
          } catch (e) {
            console.error('[Pyodide Worker] OPFS remount failed:', e);
          }
        }

        self.reportProgress = (stage, progress) => {
          self.postMessage({ id, type: 'progress', stage, progress });
        };

        pyodide.globals.set('platform', platform);
        pyodide.globals.set('given_name', givenName);

        result = await pyodide.runPythonAsync(`
import run
run.run(platform, given_name)
`);

        delete self.reportProgress;

        await flushOPFSDatabase();

        result = result.toJs({ dict_converter: Object.fromEntries });
        console.log(`[Pyodide Worker] run_pipeline result:`, result);
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
