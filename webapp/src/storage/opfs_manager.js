import { Unzip, UnzipInflate } from 'fflate';
import jsyaml from 'js-yaml';
import { callPyodideWorker } from '@/pyodide/pyodide-client.js';

export class OPFSManager {
  constructor() {
    this.opfsRoot = null;
    this.storageDir = null;
    this.dbFilename = null;  // e.g. "timeline.db" – populated during init()
    this.whitelistPatterns = [];
    this.isInitialized = false;
  }




  async init(platform) {
    if (this.isInitialized) return;

    // 1. Read config and resolve OPFS storage path
    const configResp = await fetch('./config.yaml');
    if (!configResp.ok) throw new Error('[OPFSManager] Failed to fetch config.yaml');
    const config = jsyaml.load(await configResp.text());

    const storagePath = (config.storage || {}).temp_zip_storage;
    if (!storagePath) {
      throw new Error('[OPFSManager] storage.temp_zip_storage missing from config.yaml');
    }

    const dbPath = ((config.database || {}).db_path || '');
    const dbPathParts = dbPath.split('/').filter(Boolean);
    this.dbFilename = dbPathParts[dbPathParts.length - 1]; // e.g. "timeline.db"
    const mountPrefix = '/' + dbPathParts.slice(0, -1).join('/'); // e.g. "/mnt/data"
    const relativePath = storagePath.startsWith(mountPrefix)
      ? storagePath.slice(mountPrefix.length)
      : storagePath;

    console.log(`[OPFSManager] Config: db_path=${dbPath}, temp_zip_storage=${storagePath}`);
    console.log(`[OPFSManager] Mount prefix: "${mountPrefix}", relative storage path: "${relativePath}"`);

    this.opfsRoot = await navigator.storage.getDirectory();
    const segments = relativePath.split('/').filter(Boolean);
    let currentDir = this.opfsRoot;
    for (const segment of segments) {
      currentDir = await currentDir.getDirectoryHandle(segment, { create: true });
      console.log(`[OPFSManager] Created/opened OPFS dir segment: "${segment}"`);
    }
    this.storageDir = currentDir;


    const rootEntries = [];
    for await (const [name] of this.opfsRoot.entries()) rootEntries.push(name);
    console.log(`[OPFSManager] OPFS root contents at init:`, rootEntries);
    console.log(`[OPFSManager] Initialized. storageDir=[${segments.join('/')}], dbFilename=${this.dbFilename}`);
    
    // SAFETY: Verify storageDir is not the root
    if (this.storageDir === this.opfsRoot) {
      console.error('[OPFSManager] ERROR: storageDir is pointing to OPFS root! This would delete the database on cleanup.');
      throw new Error('OPFSManager storageDir misconfiguration: pointing to OPFS root');
    }


    if (platform) {
      try {
        const paths = await callPyodideWorker('get_whitelist', { platform });
        console.log(`[WHITELIST] Received paths from Python:`, paths);
        this.whitelistPatterns = (paths || []).map((p) => {
          // Escape special chars first, then convert glob * to regex .*
          const escaped = p.replace(/[.+?^${}()|[\]\\]/g, '\\$&');
          const withWildcard = escaped.replace(/\\\*/g, '.*');
          const regex = new RegExp(`(^|/)${withWildcard}$`, 'i');
          console.log(`[WHITELIST] Pattern: "${p}" -> Regex: ${regex}`);
          return regex;
        });
      } catch (err) {
        console.warn('[OPFSManager] Failed to load whitelist – accepting all files:', err);
        this.whitelistPatterns = [];
      }
    }

    this.isInitialized = true;
  }





  isWhitelisted(filename) {
    if (this.whitelistPatterns.length === 0) return true;
    const normalised = filename.replace(/\\/g, '/');
    return this.whitelistPatterns.some((re) => re.test(normalised));
  }


  flattenPath(path) {
    return path.replace(/\//g, '___');
  }

  async processZipUpload(zipFile, platform) {
    await this.init(platform);
    // [OPFSManager] Processing upload

    return new Promise((resolve, reject) => {
      const savedPromises = [];
      let totalSeen = 0;
      let totalAccepted = 0;
      let writeSuccesses = 0;
      let writeFailures = 0;
      const rejectedFiles = [];

      const unzipStream = new Unzip((file) => {
        // Guard: skip directory entries – they carry no data and cause
        // "no stream handler" errors in fflate when started.
        if (file.name.endsWith('/')) return;

        totalSeen++;
        if (this.isWhitelisted(file.name)) {
          totalAccepted++;
          console.log(`[WHITELIST ACCEPTED] ${file.name}`);
          const safeName = this.flattenPath(file.name);
          const p = this._saveFileEntry(safeName, file)
            .then(() => { writeSuccesses++; })
            .catch((err) => {
              writeFailures++;
              console.error(`[OPFSManager] WRITE FAILED for ${safeName}:`, err);
            });
          savedPromises.push(p);
        } else {
          console.log(`[WHITELIST REJECTED] ${file.name}`);
          rejectedFiles.push(file.name);
        }
        // Files whose .start() is never called are automatically skipped by fflate
      });

      // Register DEFLATE decompressor – required in fflate 0.8.x.
      // Without this, fflate tries `new undefined()` for compressed entries
      // and throws "ctr is not a constructor".
      unzipStream.register(UnzipInflate);

      unzipStream.onerror = (e) => reject(e);

      // Stream the zip file into fflate
      const reader = zipFile.stream().getReader();
      const storageDir = this.storageDir;

      const pump = async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            unzipStream.push(new Uint8Array(0), true);
            await Promise.all(savedPromises);

            console.log(`[OPFSManager] ZIP done: ${totalSeen} scanned, ${totalAccepted} accepted, ${writeSuccesses} written, ${writeFailures} failed.`);
            const verifyNames = [];
            for await (const [name] of storageDir.entries()) {
              verifyNames.push(name);
            }
            console.log(`[OPFSManager] VERIFICATION: storageDir contains ${verifyNames.length} file(s):`, verifyNames);

            if (writeFailures > 0) {
              reject(new Error(`${writeFailures} of ${totalAccepted} OPFS writes failed — check console for details.`));
            } else if (verifyNames.length === 0 && totalAccepted > 0) {
              reject(new Error(`Writes reported success but storageDir is empty — OPFS may not be persisting.`));
            } else {
              resolve();
            }
            break;
          }
          unzipStream.push(value);
        }
      };

      pump().catch(reject);
    });
  }



  async clearTempStorage() {
    try {
      if (!this.isInitialized) {
        await this.init(); // no platform -> skips whitelist, just resolves dirs
      }
      
      // SAFETY: delete temp subdirectory
      if (!this.storageDir || this.storageDir === this.opfsRoot) {
        console.warn('[OPFSManager] Safety check: storageDir is root or null, aborting cleanup');
        return;
      }
      
      let count = 0;
      for await (const [name] of this.storageDir.entries()) {
        // console.log(`[OPFSManager] Removing temp file: ${name}`);
        await this.storageDir.removeEntry(name, { recursive: true });
        count++;
      }
      // [OPFSManager] Temp cleared
    } catch (error) {
      console.error('[OPFSManager] Failed to clear temp storage:', error);
      throw error;
    }
  }


  async clearDatabase() {
    try {
      if (!this.isInitialized) {
        await this.init();
      }
      const filesToRemove = [
        this.dbFilename,
        `${this.dbFilename}-wal`,
        `${this.dbFilename}-shm`,
      ];
      let count = 0;
      for (const name of filesToRemove) {
        try {
          await this.opfsRoot.removeEntry(name);
          // [OPFSManager] Removed file
          count++;
        } catch (e) {
          if (e.name !== 'NotFoundError') throw e;
          // WAL/SHM may not exist – that's fine
        }
      }
      // [OPFSManager] DB cleared
    } catch (error) {
      console.error('[OPFSManager] Failed to clear database:', error);
      throw error;
    }
  }

  async nukeAll() {
    try {
      const root = await navigator.storage.getDirectory();
      const entries = [];
      for await (const [name] of root.entries()) entries.push(name);
      // [OPFSManager] Nuking OPFS
      for (const name of entries) {
        await root.removeEntry(name, { recursive: true });
      }
      this.opfsRoot = null;
      this.storageDir = null;
      this.dbFilename = null;
      this.isInitialized = false;
      // [OPFSManager] OPFS cleared
    } catch (error) {
      console.error('[OPFSManager] Failed to nuke OPFS:', error);
      throw error;
    }
  }


  
  async _saveFileEntry(filename, fflateFile) {
    console.log(`[OPFSManager] _saveFileEntry START: ${filename}`);

    let fileHandle;
    try {
      fileHandle = await this.storageDir.getFileHandle(filename, { create: true });
      console.log(`[OPFSManager] Got file handle for: ${filename}`);
    } catch (e) {
      console.error(`[OPFSManager] getFileHandle FAILED for ${filename}:`, e);
      throw e;
    }

    let writable;
    try {
      writable = await fileHandle.createWritable();
      // console.log(`[OPFSManager] Opened writable stream for: ${filename}`);
    } catch (e) {
      console.error(`[OPFSManager] createWritable FAILED for ${filename}:`, e);
      throw e;
    }

    return new Promise((resolve, reject) => {
      let writeChain = Promise.resolve();
      let totalBytes = 0;
      let chunkCount = 0;
      let gotFinal = false;

      // Safety timeout — if fflate never calls ondata with final=true

      let timeout;
      const resetTimeout = () => {
        if (timeout) clearTimeout(timeout);
        timeout = setTimeout(() => {
          if (!gotFinal) {
            const msg = `[OPFSManager] TIMEOUT: ${filename} stalled (${chunkCount} chunks, ${totalBytes} bytes)`;
            console.error(msg);
            writable.close().catch(() => {});
            reject(new Error(msg));
          }
        }, 10000); // 10 seconds of pure silence = stall
      };

      resetTimeout(); // Start the clock

      fflateFile.ondata = (err, data, final) => {
        resetTimeout(); // Reset the clock because we got data!
        if (err) {
          clearTimeout(timeout);
          console.error(`[OPFSManager] fflate ondata error for ${filename}:`, err);
          writeChain = writeChain
            .then(() => writable.close())
            .catch(() => {})
            .then(() => reject(err));
          return;
        }

        chunkCount++;
        totalBytes += data.byteLength;
        writeChain = writeChain.then(() => writable.write(data));

        if (final) {
          gotFinal = true;
          clearTimeout(timeout);
          writeChain = writeChain
            .then(() => writable.close())
            .then(async () => {
              // Verify the file actually persisted
              const verifyFile = await fileHandle.getFile();
              // [OPFSManager] File write complete
              if (verifyFile.size === 0 && totalBytes > 0) {
                console.error(`[OPFSManager] FILE IS EMPTY ON DISK despite writing ${totalBytes} bytes!`);
              }
              resolve();
            })
            .catch((writeErr) => {
              console.error(`[OPFSManager] write/close FAILED for ${filename}:`, writeErr);
              reject(writeErr);
            });
        }
      };

      // console.log(`[OPFSManager] Starting fflate decompression for: ${filename}`);
      fflateFile.start();
    });
  }
}
