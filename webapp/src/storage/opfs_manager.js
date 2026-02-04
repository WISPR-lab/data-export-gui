import { Unzip } from 'fflate';
import { ConfigLoader } from '../data/schema_registry';

export class OPFSManager {
  constructor() {
    this.configLoader = new ConfigLoader();
    this.opfsRoot = null;
    this.bronzeDir = null;
    this.isInitialized = false;
  }

  async init() {
    if (this.isInitialized) return;
    
    await this.configLoader.loadSchemas();
    this.opfsRoot = await navigator.storage.getDirectory();
    // Create bronze directory for raw file storage
    this.bronzeDir = await this.opfsRoot.getDirectoryHandle('bronze', { create: true });
    
    console.log('[OPFSManager] Initialized. Bronze layer ready at /bronze');
    this.isInitialized = true;
  }

  /**
   * Flattens a path to be file-system safe (replaces / with ___)
   */
  flattenPath(path) {
    return path.replace(/\//g, '___');
  }

  /**
   * Processes a ZIP file stream, filtering and saving directly to OPFS
   * @param {File} zipFile 
   */
  async processZipUpload(zipFile) {
    await this.init();
    console.log(`[OPFSManager] Processing upload: ${zipFile.name}`);

    return new Promise((resolve, reject) => {
      const unzipStream = new Unzip((file) => {
        // Filter: Only process whitelisted files
        if (this.configLoader.isWhitelisted(file.name)) {
          console.log(`[OPFSManager] Found valid file: ${file.name}`);
          
          const safeName = this.flattenPath(file.name);
          
          // Determine createWritable options based on browser support
          // This must be async, so we trigger it and handle the stream
          this._saveFileEntry(safeName, file).catch(err => {
             console.error(`[OPFSManager] Error saving ${file.name}:`, err);
          });
          
        } else {
          // Pass null to skip file processing in fflate
          // file.start(); // Not needed if we don't start it? 
          // fflate docs: "You must call file.start() to begin processing the file"
          // If we don't care, we might just ignore it. But to advance stream we might need to consume it?
          // The Unzip parser emits files encountered in the Central Directory or local headers.
          // If we ignore it, fflate continues to next file?
          // Actually, passing nothing usually means skip. 
          // Let's verify fflate behavior. 
          // If we don't consume the data, fflate might hang if we don't register a handler? 
          // "If you do not call file.start(), the file will be skipped" - fflate docs.
        }
      });

      unzipStream.onerror = (e) => reject(e);
      // summary: when zip is fully processed
      // NOTE: fflate Unzip doesn't have an explicit 'finish' event for the whole zip on the instance level 
      // other than reacting to the input stream end?
      // Actually we just feed it data.

      // Stream the zip file into fflate
      const reader = zipFile.stream().getReader();
      
      const pump = async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            unzipStream.push(new Uint8Array(0), true);
            resolve(); // Finished
            break;
          }
          unzipStream.push(value);
        }
      };
      
      pump().catch(reject);
    });
  }

  /**
   * Internal helper to write a single file entry to OPFS
   */
  async _saveFileEntry(filename, fflateFile) {
    // 1. Get handle
    const fileHandle = await this.bronzeDir.getFileHandle(filename, { create: true });
    
    // 2. Create writable stream
    const writable = await fileHandle.createWritable();
    
    // 3. Pipe data
    fflateFile.ondatabuffer = (chunk, final) => {
      writable.write(chunk);
      if (final) {
        writable.close();
        console.log(`[OPFSManager] Wrote ${filename}`);
      }
    };
    
    // 4. Start processing this file in the zip stream
    fflateFile.start();
  }
}
