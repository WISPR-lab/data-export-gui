import { Unzip, UnzipInflate, unzipSync } from 'fflate';
import jsyaml from 'js-yaml';
import { callPyodideWorker } from '@/pyodide/pyodide-client.js';
import EventBus from '@/event-bus.js';
import { getLogger } from '@/utils/logger';

const logger = getLogger('OPFSManager');
const MAX_NESTED_ZIP_DEPTH = 5; // Apple splits large exports into zips-within-zips

export class OPFSManager {
  constructor() {
    this.opfsRoot = null;
    this.storageDir = null;
    this.dbFilename = null;  // e.g. "userdata.db" – populated during init()
    this.whitelistPatterns = [];
    this.isInitialized = false;
  }

  async init(platform) {
    /* Resolves OPFS subdirectory from config.yaml, verifies it's not root (safety), and loads glob whitelist from Python manifest if platform given. */
    if (this.isInitialized) return;

    try {
      if (!navigator.storage || !navigator.storage.getDirectory) {
        throw new Error('[OPFSManager] OPFS storage.getDirectory is not available');
      }

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
      this.dbFilename = dbPathParts[dbPathParts.length - 1]; // e.g. "userdata.db"
      const mountPrefix = '/' + dbPathParts.slice(0, -1).join('/'); // e.g. "/mnt/data"
      const relativePath = storagePath.startsWith(mountPrefix)
        ? storagePath.slice(mountPrefix.length)
        : storagePath;

      logger.debug(`Config: db_path=${dbPath}, temp_zip_storage=${storagePath}`);
      logger.debug(`Mount prefix: "${mountPrefix}", relative storage path: "${relativePath}"`);

      this.opfsRoot = await navigator.storage.getDirectory();
      const segments = relativePath.split('/').filter(Boolean);
      let currentDir = this.opfsRoot;
      for (const segment of segments) {
        currentDir = await currentDir.getDirectoryHandle(segment, { create: true });
        logger.debug(`Created/opened OPFS dir segment: "${segment}"`);
      }
      this.storageDir = currentDir;

      const rootEntries = [];
      for await (const [name] of this.opfsRoot.entries()) rootEntries.push(name);
      logger.debug(`OPFS root contents at init:`, rootEntries);
      logger.debug(`Initialized. storageDir=[${segments.join('/')}], dbFilename=${this.dbFilename}`);
    } catch (err) {
      logger.error('Init failed:', err);
      EventBus.$emit('opfsUnavailable');
      throw err;
    }
    
    // SAFETY: Verify storageDir is not the root
    if (this.storageDir === this.opfsRoot) {
      logger.error('ERROR: storageDir is pointing to OPFS root! This would delete the database on cleanup.');
      throw new Error('OPFSManager storageDir misconfiguration: pointing to OPFS root');
    }


    if (platform) {
      try {
        const paths = await callPyodideWorker('get_whitelist', { platform });
        console.debug(`[WHITELIST] Received paths from Python:`, paths);
        this.whitelistPatterns = (paths || []).map((p) => {
          // simple glob-to-regex converter. Escapes regex special chars (including * and ?) before replacing glob wildcards.
          const escaped = p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          const withWildcard = escaped.replace(/\\\*/g, '.*').replace(/\\\?/g, '.');
          const regex = new RegExp(`(^|/)${withWildcard}$`, 'i');
          // console.log(`[WHITELIST] Pattern: "${p}" -> Regex: ${regex}`);
          return regex;
        });
      } catch (err) {
        logger.warn('Failed to load whitelist – accepting all files:', err);
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
    /* Streams zip via fflate into OPFS, recursing into any nested .zip entries first; only whitelist-matching leaf entries are saved. Rejects if any write fails or storageDir is empty after writes report success. */
    await this.init(platform);
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
        if (/\.zip$/i.test(file.name)) {
          totalAccepted++; // counts the nested zip itself, not its individual leaf files
          const p = this._bufferFileEntry(file)
            .then((bytes) => this._extractNestedZipBuffer(bytes, 1))
            .then(() => { writeSuccesses++; })
            .catch((err) => {
              writeFailures++;
              logger.error(`Nested zip extraction FAILED for ${file.name}:`, err);
            });
          savedPromises.push(p);
        } else if (this.isWhitelisted(file.name)) {
          totalAccepted++;
          // console.log(`[WHITELIST ACCEPTED] ${file.name}`);
          const safeName = this.flattenPath(file.name);
          const p = this._saveFileEntry(safeName, file)
            .then(() => { writeSuccesses++; })
            .catch((err) => {
              writeFailures++;
              logger.error(`WRITE FAILED for ${safeName}:`, err);
            });
          savedPromises.push(p);
        } else {
          // console.log(`[WHITELIST REJECTED] ${file.name}`);
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

            logger.debug(`ZIP done: ${totalSeen} scanned, ${totalAccepted} accepted, ${writeSuccesses} written, ${writeFailures} failed.`);
            const verifyNames = [];
            for await (const [name] of storageDir.entries()) {
              verifyNames.push(name);
            }
            logger.debug(`VERIFICATION: storageDir contains ${verifyNames.length} file(s):`, verifyNames);

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
    /* Deletes all entries in the temp storage subdirectory only; refuses to operate if storageDir points to OPFS root. */
    try {
      if (!this.isInitialized) {
        await this.init(); // no platform -> skips whitelist, just resolves dirs
      }
      
      // SAFETY: delete temp subdirectory
      if (!this.storageDir || this.storageDir === this.opfsRoot) {
        logger.warn('Safety check: storageDir is root or null, aborting cleanup');
        return;
      }
      
      for await (const [name] of this.storageDir.entries()) {
        // console.log(`[OPFSManager] Removing temp file: ${name}`);
        await this.storageDir.removeEntry(name, { recursive: true });
      }
      // [OPFSManager] Temp cleared
    } catch (error) {
      console.error('[OPFSManager] Failed to clear temp storage:', error);
      throw error;
    }
  }


  async clearDatabase() {
    /* Removes the main DB file plus WAL/SHM journals from OPFS root; ignores NotFoundError for missing journals. */
    try {
      if (!this.isInitialized) {
        await this.init();
      }
      const filesToRemove = [
        this.dbFilename,
        `${this.dbFilename}-wal`,
        `${this.dbFilename}-shm`,
      ];
      for (const name of filesToRemove) {
        try {
          await this.opfsRoot.removeEntry(name);
          // [OPFSManager] Removed file
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
    // Recursively deletes everything in OPFS root and resets all instance state 
    try {
      const root = await navigator.storage.getDirectory();
      const entries = [];
      for await (const [name] of root.entries()) entries.push(name);

      const failures = [];
      for (const name of entries) {
        try {
          await root.removeEntry(name, { recursive: true });
        } catch (removeErr) {
          logger.error(`Failed to remove "${name}" during nukeAll:`, removeErr);
          failures.push(name);
        }
      }

      const remaining = [];
      for await (const [name] of root.entries()) remaining.push(name);

      this.opfsRoot = null;
      this.storageDir = null;
      this.dbFilename = null;
      this.isInitialized = false;

      if (remaining.length > 0) {
        throw new Error(
          `OPFS nuke incomplete — ${remaining.length} entr${remaining.length === 1 ? 'y' : 'ies'} still present after wipe: ${remaining.join(', ')}`
        );
      }
    } catch (error) {
      logger.error('Failed to nuke OPFS:', error);
      EventBus.$emit('opfsUnavailable');
      throw error;
    }
  }


  
  async _saveFileEntry(filename, fflateFile) {

    let fileHandle;
    try {
      fileHandle = await this.storageDir.getFileHandle(filename, { create: true });

    } catch (e) {
      logger.error(`getFileHandle FAILED for ${filename}:`, e);
      throw e;
    }

    let writable;
    try {
      writable = await fileHandle.createWritable();
    } catch (e) {
      logger.error(`createWritable FAILED for ${filename}:`, e);
      throw e;
    }

    return new Promise((resolve, reject) => {
      let writeChain = Promise.resolve();
      let totalBytes = 0;
      let chunkCount = 0;
      let gotFinal = false;

      let timeout; // Safety timeout — if fflate never calls ondata with final=true
      const resetTimeout = () => {
        if (timeout) clearTimeout(timeout);
        timeout = setTimeout(() => {
          if (!gotFinal) {
            const msg = `[OPFSManager] TIMEOUT: ${filename} stalled (${chunkCount} chunks, ${totalBytes} bytes)`;
            logger.error(msg);
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

      fflateFile.start();
    });
  }

  async _bufferFileEntry(fflateFile) {
    /* Drains an fflate entry into memory instead of OPFS — needed to unzipSync() a nested zip, which requires the complete bytes. */
    return new Promise((resolve, reject) => {
      const chunks = [];
      let totalBytes = 0;
      fflateFile.ondata = (err, data, final) => {
        if (err) return reject(err);
        if (data) { chunks.push(data); totalBytes += data.byteLength; }
        if (final) {
          const buffer = new Uint8Array(totalBytes);
          let offset = 0;
          for (const chunk of chunks) { buffer.set(chunk, offset); offset += chunk.byteLength; }
          resolve(buffer);
        }
      };
      fflateFile.start();
    });
  }

  async _extractNestedZipBuffer(buffer, depth) {
    /* Apple splits large exports into zips-within-zips — recurse until we hit real files, then whitelist-filter and save them same as the top-level stream. */
    if (depth > MAX_NESTED_ZIP_DEPTH) {
      logger.warn(`Nested zip depth exceeded ${MAX_NESTED_ZIP_DEPTH}, stopping recursion`);
      return;
    }
    const entries = unzipSync(buffer);
    await Promise.all(Object.entries(entries).map(([name, data]) => {
      if (name.endsWith('/')) return null;
      if (/\.zip$/i.test(name)) return this._extractNestedZipBuffer(data, depth + 1);
      if (this.isWhitelisted(name)) return this._saveBytes(this.flattenPath(name), data);
      return null;
    }));
  }

  async _saveBytes(filename, bytes) {
    const fileHandle = await this.storageDir.getFileHandle(filename, { create: true });
    const writable = await fileHandle.createWritable();
    await writable.write(bytes);
    await writable.close();
  }
}
