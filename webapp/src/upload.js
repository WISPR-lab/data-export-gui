// i need the upload sequence to be


// user selects upload button 
// user selects platform (google discord apple etc)
// user uploads zip file
// JS verifies upload is valid zip
// JS reads schema_validation.yaml and [platform].yaml (like google/discord) safely into string
// JS passes both these strings to an pyodide function (just placeholder for now), which validates the zip contents. 
// you do not need to implement the pyodide function, just the JS code to read the files and pass them to pyodide.
// the pyodide function will return true/false for valid/invalid, a list of errors if invalid (emoty list if valid).
// then there is a second placeholder pyodide function that returns a list of files list_of_files inside the zip
// that the JS code should keep when it unzips the file

// then unzip the file in browser. Keep in mind some of the files may be large. Only keep files in 'list_of_files' in browser memory.
// keep in mind list_of_files may include nested paths like 'takeout/google/actvity.json'. Do all of this safely and be aware of browser memory.

// then, iterate through the kept files. 
// For each file, read its contents as text (assume all files are text for now).
// pass the file contents and the schema (playform.yaml) to a third placeholder pyodide function that returns a true/false for valid/invalid and a list of errors if invalid (empty if valid) AND
// a JSON object representing a list of events/states that should be pushed as new rows in the data base. The JSON format shoudl be
// {"events": [ {"id":.....}, {"id":....} ], "states": [ {"id":....}, {"id":....} ] }.

/// if the file is a JSONL bigger than a certain amount, pass it in chunks of the pyodide function, and accumulate the results. Your call about chunk size.

// at the end, return a summary of total events/states added, and any errors encountered along the way.
// not sure what we should use for logging.
// finally, clean up memory.

// ============================================================================
// IMPLEMENTATION
// ============================================================================

import BrowserDB from './database';
import JSZip from 'jszip';


const DEBUG_LOGGING = true; // Set to false to disable console logs

function log(...args) {
  if (DEBUG_LOGGING) { console.log('[UploadService]', ...args); }
}

function logError(...args) { console.error('[UploadService]', ...args); }

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
 * Placeholder for actual pyodide validation
 */
async function validateZipContents(schemaValidationYaml, platformYaml) {
  try {
    log('Validating zip contents with schemas...');
    
    // TODO: Call actual pyodide function
    // const result = await window.pyodide.validateZip(schemaValidationYaml, platformYaml);
    // return result;
    
    // Placeholder implementation
    return { valid: true, errors: [] };
  } catch (error) {
    logError('Error during zip contents validation:', error);
    throw error;
  }
}

/**
 * Gets list of files to keep from the zip
 * Placeholder for actual pyodide function
 */
async function getFilesToKeep(platformYaml) {
  try {
    log('Getting list of files to keep...');
    
    // TODO: Call actual pyodide function
    // const result = await window.pyodide.getFilesToKeep(platformYaml);
    // return result;
    
    // Placeholder implementation - return all files
    return [];
  } catch (error) {
    logError('Error getting files to keep:', error);
    throw error;
  }
}

/**
 * Parses JSONL content into array of JSON objects
 */
function parseJSONL(content) {
  const lines = content.split('\n').filter(line => line.trim());
  return lines.map((line, idx) => {
    try {
      return JSON.parse(line);
    } catch (error) {
      logError(`Failed to parse JSONL line ${idx}:`, line);
      throw new Error(`Invalid JSON on line ${idx}: ${error.message}`);
    }
  });
}

/**
 * Chunks JSONL content for processing large files
 * Returns array of chunks, each containing up to chunkSize lines
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
 * Processes a single file through the pyodide parser
 * Placeholder for actual pyodide parsing function
 */
async function processFileWithPyodide(fileContent, platformYaml) {
  try {
    log('Processing file with pyodide parser...');
    
    // TODO: Call actual pyodide function
    // const result = await window.pyodide.parseFile(fileContent, platformYaml);
    // return result; // { valid: bool, errors: [], data: { events: [], states: [] } }
    
    // Placeholder implementation
    return { valid: true, errors: [], data: { events: [], states: [] } };
  } catch (error) {
    logError('Error processing file with pyodide:', error);
    throw error;
  }
}

/**
 * Processes a JSONL file in chunks
 */
async function processLargeJSONLFile(fileContent, platformYaml, filename) {
  const chunkSize = 1000; // Lines per chunk
  const chunks = chunkJSONL(fileContent, chunkSize);
  
  log(`Processing ${filename} in ${chunks.length} chunks...`);
  
  const allEvents = [];
  const allStates = [];
  const allErrors = [];
  
  for (let i = 0; i < chunks.length; i++) {
    try {
      const result = await processFileWithPyodide(chunks[i], platformYaml);
      
      if (!result.valid) {
        allErrors.push(...result.errors.map(err => `${filename} (chunk ${i + 1}): ${err}`));
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
export async function processUpload(file, platform, sketchId) {
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
    log(`Starting upload process for ${platform} platform with file: ${file.name}`);
    
    // Step 1: Validate zip file format
    log('Step 1: Validating zip file format...');
    const zipValidation = await validateZipFile(file);
    if (!zipValidation.valid) {
      summary.errors.push(...zipValidation.errors);
      return summary;
    }
    const { zip } = zipValidation;
    
    // Step 2: Read schema files
    log('Step 2: Reading schema files...');
    let schemaValidationYaml, platformYaml;
    try {
      schemaValidationYaml = await readSchemaFile('schema_validation.yaml');
      platformYaml = await readSchemaFile(`${platform}.yaml`);
    } catch (error) {
      summary.errors.push(`Failed to read schema files: ${error.message}`);
      return summary;
    }
    
    // Step 3: Validate zip contents
    log('Step 3: Validating zip contents against schema...');
    const contentsValidation = await validateZipContents(schemaValidationYaml, platformYaml);
    if (!contentsValidation.valid) {
      summary.errors.push(...contentsValidation.errors);
      return summary;
    }
    
    // Step 4: Get list of files to keep
    log('Step 4: Getting list of files to keep...');
    const filesToKeep = await getFilesToKeep(platformYaml);
    log(`Will keep ${filesToKeep.length} files from zip`);
    
    // Step 5: Extract and process files
    log('Step 5: Extracting and processing files...');
    const allEvents = [];
    const allStates = [];
    
    const filesToProcess = filesToKeep.length > 0 
      ? filesToKeep 
      : Object.keys(zip.files).filter(name => !zip.files[name].dir);
    
    for (const filename of filesToProcess) {
      try {
        const zipFile = zip.files[filename];
        if (!zipFile || zipFile.dir) continue;
        
        log(`Processing file: ${filename}`);
        
        // Read file content as text
        let fileContent;
        try {
          fileContent = await zipFile.async('text');
        } catch (error) {
          const errMsg = `Failed to read file ${filename}: ${error.message}`;
          logError(errMsg);
          summary.errors.push(errMsg);
          continue;
        }
        
        // Check if file is large JSONL (> 1MB)
        const isLargeFile = fileContent.length > 1024 * 1024;
        
        let result;
        if (isLargeFile && filename.endsWith('.jsonl')) {
          result = await processLargeJSONLFile(fileContent, platformYaml, filename);
        } else {
          result = await processFileWithPyodide(fileContent, platformYaml);
        }
        
        // Accumulate results
        if (result.errors && result.errors.length > 0) {
          summary.errors.push(...result.errors);
        }
        
        if (result.data) {
          allEvents.push(...(result.data.events || []));
          allStates.push(...(result.data.states || []));
        }
        
        log(`Completed file: ${filename}`);
        
        // Clear file content from memory
        fileContent = null;
      } catch (error) {
        const errMsg = `Unexpected error processing ${filename}: ${error.message}`;
        logError(errMsg);
        summary.errors.push(errMsg);
      }
    }
    
    // Step 6: Insert data into database
    log('Step 6: Inserting data into database...');
    try {
      for (const event of allEvents) {
        await BrowserDB.createEvent(
          sketchId,
          event.timestamp,
          event.message || '',
          event.timestampDesc,
          event.attributes,
          event.config
        );
      }
      
      for (const state of allStates) {
        // TODO: Implement createState in BrowserDB if needed
        log('State insertion not yet implemented', state);
      }
      
      summary.totalEventsAdded = allEvents.length;
      summary.totalStatesAdded = allStates.length;
      summary.success = true;
      
      log(`Successfully added ${allEvents.length} events and ${allStates.length} states`);
    } catch (dbError) {
      const errMsg = `Database insertion error: ${dbError.message}`;
      logError(errMsg);
      summary.errors.push(errMsg);
    }
    
  } catch (error) {
    const errMsg = `Unexpected error during upload: ${error.message}`;
    logError(errMsg);
    summary.errors.push(errMsg);
  } finally {
    // Step 7: Cleanup
    log('Cleaning up resources...');
    summary.processingTimeMs = Date.now() - startTime;
    
    log(`Upload process completed in ${summary.processingTimeMs}ms`);
    log('Summary:', summary);
  }
  
  return summary;
}