// pyodideWorker.js
// SOURCE: webapp/src/pyodideWorker.js
// NOTE: This file is automatically copied to public/ during build (npm run sync-assets).
// DO NOT EDIT the version in the public/ folder.

importScripts('https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js');

let pyodide;
let pyodideReadyPromise;

/**
 * Initializes Pyodide, installs dependencies, and mounts Python source files.
 */
async function initPyodide() {
  pyodide = await loadPyodide();
  
  // Load specialized Python libraries
  await pyodide.loadPackage(['pyyaml', 'pytz']);

  // Fetch and mount our custom Python parser logic
  const pythonFiles = [
    'pyodide.py',
    'base.py',
    'json_.py',
    'jsonl.py',
    'csv.py',
    'json_labelvalues.py',
    'csv_multi.py',
    'schema_utils.py',
    'time_utils.py'
  ];

  for (const file of pythonFiles) {
    const response = await fetch(`/pyparser/${file}`);
    if (!response.ok) {
      console.error(`Failed to fetch ${file}: ${response.statusText}`);
      continue;
    }
    const content = await response.text();
    pyodide.FS.writeFile(file, content);
  }

  // Import the bridge function
  pyodide.runPython('import pyodide as bridge');
  
  return pyodide;
}

pyodideReadyPromise = initPyodide();

/**
 * Message handler for main thread commands.
 */
self.onmessage = async (event) => {
  const { id, command, args } = event.data;
  
  try {
    await pyodideReadyPromise;
    
    let result;
    switch (command) {
      case 'test_environment':
        result = pyodide.runPython('bridge.test_environment()').toJs({ dict_converter: Object.fromEntries });
        break;
      
      case 'group_schema_by_path':
        const { schemaYaml } = args;
        self.pyodide.globals.set('schema_str', schemaYaml);
        result = pyodide.runPython('bridge.group_schema_by_path(schema_str)').toJs({ dict_converter: Object.fromEntries });
        break;
        
      case 'parse':
        const { schemaYaml: parseSchema, fileContent, filename } = args;
        // We use a global variable to pass large strings to avoid shell escaping issues with runPython
        self.pyodide.globals.set('schema_str', parseSchema);
        self.pyodide.globals.set('file_content', fileContent);
        self.pyodide.globals.set('filename', filename);
        
        result = pyodide.runPython('bridge.parse(schema_str, file_content, filename)').toJs({ dict_converter: Object.fromEntries });
        break;
        
      default:
        throw new Error(`Unknown command: ${command}`);
    }
    
    self.postMessage({ id, result, success: true });
  } catch (error) {
    self.postMessage({ id, error: error.message, success: false });
  }
};
