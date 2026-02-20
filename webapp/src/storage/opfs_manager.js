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

  // ── Initialisation ─────────────────────────────────────────────────

  /**
   * Initialise the manager:
   *  1. Read storage.temp_zip_storage from config.yaml and create nested OPFS dirs
   *  2. Fetch whitelist patterns from Pyodide and cache as RegExp[]
   *
   * @param {string} [platform] – manifest id (e.g. "facebook") for whitelist lookup
   */
  async init(platform) {
    if (this.isInitialized) return;

    // 1. Read config and resolve OPFS storage path
    const configResp = await fetch('/config.yaml');
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

    // Walk each relative path segment and create directories iteratively
    this.opfsRoot = await navigator.storage.getDirectory();
    const segments = relativePath.split('/').filter(Boolean);
    let currentDir = this.opfsRoot;
    for (const segment of segments) {
      currentDir = await currentDir.getDirectoryHandle(segment, { create: true });
      console.log(`[OPFSManager] Created/opened OPFS dir segment: "${segment}"`);
    }
    this.storageDir = currentDir;

    // Log what already exists in OPFS root for diagnostics
    const rootEntries = [];
    for await (const [name] of this.opfsRoot.entries()) rootEntries.push(name);
    console.log(`[OPFSManager] OPFS root contents at init:`, rootEntries);
    console.log(`[OPFSManager] Initialized. storageDir=[${segments.join('/')}], dbFilename=${this.dbFilename}`);
    
    // SAFETY: Verify storageDir is not the root
    if (this.storageDir === this.opfsRoot) {
      console.error('[OPFSManager] ERROR: storageDir is pointing to OPFS root! This would delete the database on cleanup.');
      throw new Error('OPFSManager storageDir misconfiguration: pointing to OPFS root');
    }

    // 2. Load whitelist file-path patterns from Pyodide manifest
    if (platform) {
      try {
        const paths = await callPyodideWorker('get_whitelist', { platform });
        this.whitelistPatterns = (paths || []).map((p) => {
          // Escape regex-special chars then build a suffix-match pattern so
          // ZIP entries like "facebook-JohnDoe/security/file.json" still match
          // the manifest path "security/file.json".
          const escaped = p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          return new RegExp(`(^|/)${escaped}$`, 'i');
        });
        console.log(`[OPFSManager] Loaded ${this.whitelistPatterns.length} whitelist patterns`);
      } catch (err) {
        console.warn('[OPFSManager] Failed to load whitelist – accepting all files:', err);
        this.whitelistPatterns = [];
      }
    }

    this.isInitialized = true;
  }

  // ── Whitelist check ────────────────────────────────────────────────

  /**
   * Returns true when the filename matches at least one manifest path
   * pattern.  If no patterns were loaded, accepts everything (fallback).
   */
  isWhitelisted(filename) {
    if (this.whitelistPatterns.length === 0) return true;
    const normalised = filename.replace(/\\/g, '/');
    return this.whitelistPatterns.some((re) => re.test(normalised));
  }

  // ── Helpers ────────────────────────────────────────────────────────

  /**
   * Flattens a path to be file-system safe (replaces / with ___)
   */
  flattenPath(path) {
    return path.replace(/\//g, '___');
  }

  // ── ZIP Processing ─────────────────────────────────────────────────

  /**
   * Processes a ZIP file stream, filtering and saving directly to OPFS
   * @param {File} zipFile
   * @param {string} [platform] – manifest id used for whitelist lookup
   */
  async processZipUpload(zipFile, platform) {
    await this.init(platform);
    console.log(`[OPFSManager] Processing upload: ${zipFile.name}`);

    return new Promise((resolve, reject) => {
      const savedPromises = [];
      let totalSeen = 0;
      let totalAccepted = 0;
      let writeSuccesses = 0;
      let writeFailures = 0;

      const unzipStream = new Unzip((file) => {
        // Guard: skip directory entries – they carry no data and cause
        // "no stream handler" errors in fflate when started.
        if (file.name.endsWith('/')) return;

        totalSeen++;
        // Only process files that appear in the platform manifest
        if (this.isWhitelisted(file.name)) {
          totalAccepted++;
          const safeName = this.flattenPath(file.name);
          console.log(`[OPFSManager] Accepted [${totalAccepted}]: ${file.name}  →  ${safeName}`);
          const p = this._saveFileEntry(safeName, file)
            .then(() => { writeSuccesses++; })
            .catch((err) => {
              writeFailures++;
              console.error(`[OPFSManager] WRITE FAILED for ${safeName}:`, err);
            });
          savedPromises.push(p);
        } else {
          // console.debug(`[OPFSManager] Skipped (not in manifest): ${file.name}`);
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
            // Wait for every in-flight OPFS write to complete
            await Promise.all(savedPromises);

            console.log(`[OPFSManager] ZIP done: ${totalSeen} scanned, ${totalAccepted} accepted, ${writeSuccesses} written, ${writeFailures} failed.`);

            // Verification: enumerate what actually landed in storageDir
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

  // ── OPFS cleanup ───────────────────────────────────────────────────

  /**
   * Removes only the contents of the temp ZIP storage directory (tmpstore).
   * Safe to call right after extraction; does NOT touch the SQLite database.
   */
  async clearTempStorage() {
    try {
      if (!this.isInitialized) {
        await this.init(); // no platform → skips whitelist, just resolves dirs
      }
      
      // SAFETY: Ensure we're deleting tmpstore subdirectory, NOT OPFS root
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
      console.log(`[OPFSManager] Temp storage cleared (${count} entries removed).`);
    } catch (error) {
      console.error('[OPFSManager] Failed to clear temp storage:', error);
      throw error;
    }
  }

  /**
   * Removes the SQLite database file(s) from OPFS root.
   * Also removes WAL/SHM sidecar files if present.
   * Does NOT touch the temp storage directory.
   */
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
          console.log(`[OPFSManager] Removed DB file: ${name}`);
          count++;
        } catch (e) {
          if (e.name !== 'NotFoundError') throw e;
          // WAL/SHM may not exist – that's fine
        }
      }
      console.log(`[OPFSManager] Database cleared (${count} file(s) removed).`);
    } catch (error) {
      console.error('[OPFSManager] Failed to clear database:', error);
      throw error;
    }
  }

  /**
   * Nuclear option: wipes the entire OPFS origin (temp files + database).
   * Use for full reset / "start over". Resets init state so next call
   * to init() recreates everything cleanly.
   */
  async nukeAll() {
    try {
      const root = await navigator.storage.getDirectory();
      const entries = [];
      for await (const [name] of root.entries()) entries.push(name);
      console.log(`[OPFSManager] Nuking OPFS root (${entries.length} entries):`, entries);
      for (const name of entries) {
        await root.removeEntry(name, { recursive: true });
      }
      // Reset so next init() recreates dirs cleanly
      this.opfsRoot = null;
      this.storageDir = null;
      this.dbFilename = null;
      this.isInitialized = false;
      console.log(`[OPFSManager] OPFS nuked – ${entries.length} top-level entries removed.`);
    } catch (error) {
      console.error('[OPFSManager] Failed to nuke OPFS:', error);
      throw error;
    }
  }

  // ── File writing with queued async writes ──────────────────────────

  /**
   * Saves one fflate file entry to OPFS.
   *
   * fflate pushes chunks *synchronously* via `ondata` while
   * `writable.write()` is asynchronous.  Without queuing the writes
   * the browser will exhaust memory on large files.  We chain every
   * `write()` behind the previous one and only `close()` the writable
   * after the final queued chunk has been flushed.
   */
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
              console.log(`[OPFSManager] Wrote ${filename}: ${chunkCount} chunks, ${(totalBytes / 1024).toFixed(1)} KB sent, ${(verifyFile.size / 1024).toFixed(1)} KB on disk`);
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
