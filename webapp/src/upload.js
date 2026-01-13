import BrowserDB from './database';
import JSZip from 'jszip';

const DEBUG_LOGGING = true;
const pyodideWorker = new Worker('/pyodideWorker.js');
let workerMessageId = 0;

function log(...args) {
  if (DEBUG_LOGGING) { console.log('[UploadService]', ...args); }
}

function logError(...args) { console.error('[UploadService]', ...args); }

/**
 * Sends a command to the Pyodide Worker and returns a promise.
 */
function callWorker(command, args) {
  return new Promise((resolve, reject) => {
    const id = workerMessageId++;
    const handler = (event) => {
      if (event.data.id === id) {
        pyodideWorker.removeEventListener('message', handler);
        if (event.data.success) {
          resolve(event.data.result);
        } else {
          reject(new Error(event.data.error));
        }
      }
    };
    pyodideWorker.addEventListener('message', handler);
    pyodideWorker.postMessage({ id, command, args });
  });
}

/**
 * Reads a file from the public schemas directory as text
 */
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

/**
 * Validates that the uploaded file is a valid zip
 */
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

/**
 * Validates the zip contents using pyodide validation function
 */
async function validateZipContents(schemaValidationYaml, platformYaml) {
  try {
    log('Validating zip contents with schemas...');
    // We'll pass the manifest to worker to ensure it's valid
    const result = await callWorker('group_schema_by_path', { schemaYaml: platformYaml });
    return { valid: true, errors: [], path_schemas: result.path_schemas };
  } catch (error) {
    logError('Error during zip contents validation:', error);
    return { valid: false, errors: [error.message] };
  }
}

/**
 * Processes a single file through the pyodide parser
 */
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

/**
 * Chunks JSONL content for processing large files
 */
function chunkJSONL(content, chunkSize = 1000) {
  const lines = content.split('\n').filter(line => line.trim());
  const chunks = [];
  for (let i = 0; i < lines.length; i += chunkSize) {
    chunks.push(lines.slice(i, i + chunkSize).join('\n'));
  }
  return chunks;
}

/**
 * Processes a JSONL file in chunks
 */
async function processLargeJSONLFile(fileContent, platformYaml, filename) {
  const chunkSize = 1000;
  const chunks = chunkJSONL(fileContent, chunkSize);
  
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
 */
export async function processUpload(file, platform, sketchId, store) {
  const startTime = Date.now();
  const summary = {
    success: false,
    platform,
    totalEventsAdded: 0,
    totalStatesAdded: 0,
    errors: [],
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
      const timelineResponse = await BrowserDB.createTimeline({
        sketch_id: sketchId,
        name: `${platform} - ${new Date().toLocaleString()}`,
        platform_name: platform,
        status: 'processing'
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
        
        fileContent = null; 
      } catch (error) {
        summary.errors.push(`Error processing ${zipFilename}: ${error.message}`);
      }
    }
    
    // Step 6: Insert into database
    log(`Step 6: Inserting ${allEvents.length} events and ${allStates.length} states into database...`);
    if (store) store.commit('UPDATE_UPLOAD_PROGRESS', { status: 'inserting', progress: 80 });

    try {
      if (allEvents.length > 0 || allStates.length > 0) {
        await BrowserDB.bulkInsert(sketchId, timelineId, allEvents, allStates);
      }
      
      summary.totalEventsAdded = allEvents.length;
      summary.totalStatesAdded = allStates.length;
      summary.success = true;
      
      // Mark timeline as ready
      await BrowserDB.saveSketchTimeline(sketchId, timelineId, undefined, undefined, undefined, 'ready');
      
      if (store) {
        store.commit('COMPLETE_UPLOAD');
        // Refresh timelines in store
        const timelines = await BrowserDB.getTimelines(sketchId);
        store.commit('SET_TIMELINES', timelines.data);
      }
      
      log('Database insertion complete');
    } catch (dbError) {
      summary.errors.push(`Database error: ${dbError.message}`);
      if (store) store.commit('FAIL_UPLOAD', dbError.message);
    }
    
  } catch (error) {
    summary.errors.push(`Unexpected error: ${error.message}`);
    if (store) store.commit('FAIL_UPLOAD', error.message);
  } finally {
    summary.processingTimeMs = Date.now() - startTime;
    log(`Upload process completed in ${summary.processingTimeMs}ms`);
  }
  
  return summary;
}
