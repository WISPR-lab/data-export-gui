import BrowserDB from './database';
import JSZip from 'jszip';
import { classifyError, ERROR_TYPES } from './errorTypes';
import { TIMELINE_STATUS } from './database';

// For computing file hashes
import crypto from 'crypto-js';

const DEBUG_LOGGING = true;

// Singleton: Create worker only once, reuse across all imports
let pyodideWorker = null;
function getPyodideWorker() {
  if (!pyodideWorker) {
    pyodideWorker = new Worker('/pyodideWorker.js');
    console.log('[UploadService] Created Pyodide worker (singleton)');
  }
  return pyodideWorker;
}

let workerMessageId = 0;


const UPLOAD_CONFIG = {
  JSONL_CHUNK_SIZE: 1000,
};


function log(...args) {
  if (DEBUG_LOGGING) { console.log('[UploadService]', ...args); }
}

function logError(...args) { console.error('[UploadService]', ...args); }

// Compute SHA-256 hash of file content
async function computeFileHash(content) {
  try {
    return crypto.SHA256(content).toString();
  } catch (error) {
    logError('Error computing hash:', error);
    return null;
  }
}

/**
 * sends a command to the Pyodide Worker
 * 
 * @returns {Promise<{result, errorType?, source?}>} Worker response
 */
function callWorker(command, args) {
  return new Promise((resolve, reject) => {
    const worker = getPyodideWorker(); // Get singleton worker
    const id = workerMessageId++;
    const handler = (event) => {
      if (event.data.id === id) {
        worker.removeEventListener('message', handler);
        if (event.data.success) {
          resolve(event.data.result);
        } else {
          const error = new Error(event.data.error); // error with type info attached for UI classification
          error.errorType = event.data.errorType || classifyError(event.data.error, event.data.source);
          error.source = event.data.source || 'worker';
          reject(error);
        }
      }
    };
    worker.addEventListener('message', handler);
    worker.postMessage({ id, command, args });
  });
}

// reads files from /public/schemas/  as text
async function readSchemaFile(filename) {
  try {
    const response = await fetch(`/schemas/${filename}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch ${filename}: ${response.statusText}`);
    }
    return await response.text();
  } catch (error) {
    logError(`Error reading schema file ${filename}:`, error);
    throw error;
  }
}

// is the uploaded file a valid zip?
async function validateZipFile(file) {
  try {
    const zip = new JSZip();
    await zip.loadAsync(file);
    return { valid: true, zip };
  } catch (error) {
    logError('Invalid zip file:', error);
    return { valid: false, errors: [error.message] };
  }
}

// processes a single file through the pyodide parser
async function processFileWithPyodide(fileContent, platformYaml, filename) {
  try {
    log(`Processing ${filename} with pyodide parser...`);
    const result = await callWorker('parse', { 
      schemaYaml: platformYaml, 
      fileContent, 
      filename 
    });
    return { valid: !result.fatal, errors: result.errors || [], data: result };
  } catch (error) {
    logError('Error processing file with pyodide:', error);
    throw error;
  }
}

// chunks JSONL content for processing large files
function chunkJSONL(content, chunkSize = UPLOAD_CONFIG.JSONL_CHUNK_SIZE) {
  const lines = content.split('\n').filter(line => line.trim());
  const chunks = [];
  for (let i = 0; i < lines.length; i += chunkSize) {
    chunks.push(lines.slice(i, i + chunkSize).join('\n'));
  }
  return chunks;
}

// chunks JSONL files
async function processLargeJSONLFile(fileContent, platformYaml, filename) {
  const chunks = chunkJSONL(fileContent);
  
  log(`Processing ${filename} in ${chunks.length} chunks...`);
  
  const allEvents = [];
  const allStates = [];
  const allErrors = [];
  
  for (let i = 0; i < chunks.length; i++) {
    try {
      const result = await processFileWithPyodide(chunks[i], platformYaml, filename);
      
      if (!result.valid) {
        allErrors.push(...result.errors.map(err => `${filename} (chunk ${i + 1}): ${err.msg || err}`));
      } else {
        allEvents.push(...(result.data.events || []));
        allStates.push(...(result.data.states || []));
      }
      
      log(`Processed chunk ${i + 1}/${chunks.length} of ${filename}`);
    } catch (error) {
      const errMsg = `Error processing chunk ${i + 1} of ${filename}: ${error.message}`;
      logError(errMsg);
      allErrors.push(errMsg);
    }
  }
  
  return {
    events: allEvents,
    states: allStates,
    errors: allErrors
  };
}

/**
 * Main upload and processing function
 * 
 * returns summary with optional errorType field for UI classification:
 * - errorType: string (one of ERROR_TYPES) - helps UI show appropriate message
 * - errors: array of strings - individual errors encountered
 */
export async function processUpload(file, platform, sketchId, store) {
  const startTime = Date.now();
  const summary = {
    success: false,
    platform,
    totalEventsAdded: 0,
    totalStatesAdded: 0,
    errors: [],
    errorType: null,  // Will be set on first fatal error
    warnings: [],
    processingTimeMs: 0
  };

  try {
    if (store) {
      store.commit('START_UPLOAD', file.name);
    }
    
    log(`Starting upload process for ${platform} platform with file: ${file.name}`);
    
    // Step 1: Validate zip file format
    log('Step 1: Validating zip file format...');
    if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'validating', progress: 10 });
    
    const zipValidation = await validateZipFile(file);
    if (!zipValidation.valid) {
      summary.errors.push(...zipValidation.errors);
      if (store) store.commit('FAIL_UPLOAD', summary.errors[0]);
      return summary;
    }
    const { zip } = zipValidation;
    
    // Step 2: Read manifest
    log('Step 2: Reading platform manifest...');
    let platformYaml;
    try {
      platformYaml = await readSchemaFile(`${platform}.yaml`);
    } catch (error) {
      const msg = `Failed to read manifest for ${platform}: ${error.message}`;
      summary.errors.push(msg);
      if (store) store.commit('FAIL_UPLOAD', msg);
      return summary;
    }
    
    // Step 3: Get file mappings from manifest
    log('Step 3: Finding matching files in zip...');
    if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'parsing', progress: 20 });
    
    const result = await callWorker('group_schema_by_path', { schemaYaml: platformYaml });
    const pathSchemas = result.path_schemas;
    const pathsToMatch = Object.keys(pathSchemas);
    
    // Step 4: Create a new timeline for this upload
    log('Step 4: Creating new timeline...');
    let timelineId;
    try {
      const timelineName = await BrowserDB.generateTimelineName(sketchId, platform);
      const timelineResponse = await BrowserDB.createTimeline({
        sketch_id: sketchId,
        name: timelineName,
        platform_name: platform,
        status: TIMELINE_STATUS.PROCESSING
      });
      timelineId = timelineResponse.data.objects[0].id;
    } catch (error) {
      const msg = `Failed to create timeline: ${error.message}`;
      summary.errors.push(msg);
      if (store) store.commit('FAIL_UPLOAD', msg);
      return summary;
    }

    // Step 5: Extract and process matched files
    log('Step 5: Extracting and processing files...');
    const allEvents = [];
    const allStates = [];
    const fileMetadata = []; // Track metadata for each file
    
    const zipEntries = Object.keys(zip.files);
    let processedCount = 0;
    
    for (const targetPath of pathsToMatch) {
      // Find the entry that matches exactly or ends with the target path (ignoring leading dirs)
      const zipFilename = zipEntries.find(name => name === targetPath || name.endsWith('/' + targetPath));
      
      processedCount++;
      const currentProgress = 20 + Math.floor((processedCount / pathsToMatch.length) * 50);
      if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'parsing', progress: currentProgress });

      if (!zipFilename) {
        log(`Warning: ${targetPath} not found in ZIP`);
        summary.warnings.push(`File defined in manifest not found in ZIP: ${targetPath}`);
        continue;
      }

      try {
        const zipFile = zip.files[zipFilename];
        if (zipFile.dir) continue;
        
        log(`Processing file: ${zipFilename}`);
        let fileContent = await zipFile.async('text');
        
        // Compute file hash for duplicate detection
        const fileHash = await computeFileHash(fileContent);
        log(`File hash: ${fileHash}`);
        
        // Check for duplicates
        let isDuplicate = false;
        let duplicateMetadata = null;
        if (fileHash) {
          const existingResponse = await BrowserDB.getDocumentMetadataByHash(sketchId, fileHash);
          if (existingResponse.data.objects && existingResponse.data.objects.length > 0) {
            duplicateMetadata = existingResponse.data.objects[0];
            isDuplicate = true;
            const msg = `Duplicate detected: ${targetPath} matches previously uploaded ${duplicateMetadata.path}`;
            log(`WARNING: ${msg}`);
            summary.warnings.push(msg);
            // For now, continue processing. In future, could prompt user for choice.
          }
        }
        
        // Chunk large JSONL files (> 1MB)
        let parseResult;
        if (fileContent.length > 1024 * 1024 && zipFilename.toLowerCase().endsWith('.jsonl')) {
          parseResult = await processLargeJSONLFile(fileContent, platformYaml, targetPath);
        } else {
          parseResult = await processFileWithPyodide(fileContent, platformYaml, targetPath);
        }
        
        if (parseResult.errors && parseResult.errors.length > 0) {
          summary.errors.push(...parseResult.errors.map(e => `${zipFilename}: ${e.msg || e}`));
        }
        
        if (parseResult.data || (parseResult.events || parseResult.states)) {
          const events = (parseResult.data && parseResult.data.events) || parseResult.events || [];
          const states = (parseResult.data && parseResult.data.states) || parseResult.states || [];
          allEvents.push(...events);
          allStates.push(...states);
        }
        
        // Track metadata for this file
        fileMetadata.push({
          path: targetPath,
          file_name: zipFilename.split('/').pop(),
          size_bytes: fileContent.length,
          mime_type: zipFilename.endsWith('.json') || zipFilename.endsWith('.jsonl') ? 'application/json' : 'text/plain',
          hash_sha256: fileHash,
          rows_parsed: ((parseResult.data && parseResult.data.events) ? parseResult.data.events.length : 0) + ((parseResult.data && parseResult.data.states) ? parseResult.data.states.length : 0),
          parse_error_message: parseResult.errors && parseResult.errors.length > 0 ? parseResult.errors[0] : null,
          labels: isDuplicate ? ['duplicate'] : [],
        });
        
        fileContent = null; 
      } catch (error) {
        // Preserve error type information from worker
        const errorMsg = `Error processing ${zipFilename}: ${error.message}`;
        summary.errors.push(errorMsg);
        
        // Set error type on first fatal error (only if not already set)
        if (!summary.errorType && error.errorType) {
          summary.errorType = error.errorType;
        }
      }
    }
    
    // Step 6: Insert into database
    log(`Step 6: Inserting ${allEvents.length} events and ${allStates.length} states into database...`);
    if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'inserting', progress: 80 });

    try {
      if (allEvents.length > 0 || allStates.length > 0) {
        await BrowserDB.bulkInsert(sketchId, timelineId, allEvents, allStates);
      }
      
      // Step 7: Create document metadata for each processed file
      log(`Step 7: Creating document metadata for ${fileMetadata.length} files...`);
      for (const metadata of fileMetadata) {
        try {
          await BrowserDB.createDocumentMetadata({
            sketch_id: sketchId,
            timeline_id: timelineId,
            platform_name: platform,
            ...metadata,
            source_config: {
              uploadedAt: new Date().toISOString(),
              parse_status: metadata.parse_error_message ? 'error' : 'success',
            }
          });
        } catch (metadataError) {
          logError(`Failed to create metadata for ${metadata.path}:`, metadataError);
        }
      }
      
      summary.totalEventsAdded = allEvents.length;
      summary.totalStatesAdded = allStates.length;
      summary.success = true;
      
      // Mark timeline as ready
      await BrowserDB.saveSketchTimeline(sketchId, timelineId, undefined, undefined, undefined, TIMELINE_STATUS.READY);
      
      if (store) {
        store.commit('COMPLETE_UPLOAD', summary);
        // Reload full sketch to update sketch.timelines (triggers UI re-render)
        const sketchResponse = await BrowserDB.getSketch(sketchId);
        const sketch = sketchResponse.data.objects[0];
        const timelinesResponse = await BrowserDB.getTimelines(sketchId);
        sketch.timelines = timelinesResponse.data.objects || [];
        store.commit('SET_SKETCH', { objects: [sketch], meta: sketchResponse.data.meta || {} });
      }
      
      log('Database insertion complete');
    } catch (dbError) {
      summary.errors.push(`Database error: ${dbError.message}`);
      if (!summary.errorType) {
        summary.errorType = ERROR_TYPES.DATABASE_ERROR;
      }
      
      // Mark timeline as error state
      try {
        await BrowserDB.saveSketchTimeline(sketchId, timelineId, undefined, undefined, undefined, TIMELINE_STATUS.ERROR);
      } catch (updateError) {
        logError(`Failed to mark timeline as error:`, updateError);
      }
      
      if (store) store.commit('FAIL_UPLOAD', summary);
    }
    
  } catch (error) {
    summary.errors.push(`Unexpected error: ${error.message}`);
    if (!summary.errorType) {
      summary.errorType = error.errorType || ERROR_TYPES.UNKNOWN_ERROR;
    }
    if (store) store.commit('FAIL_UPLOAD', error.message);
  } finally {
    summary.processingTimeMs = Date.now() - startTime;
    log(`Upload process completed in ${summary.processingTimeMs}ms`);
  }
  
  return summary;
}
