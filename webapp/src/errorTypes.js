/**
 * errorTypes.js
 * 
 * Defines error classifications for distinguishing user-fixable errors
 * from system/infrastructure errors.
 * 
 * This enables the UI to display different messages:
 * - USER errors: "Please check your file format..."
 * - SYSTEM errors: "Something went wrong on our end..."
 */

export const ERROR_TYPES = {
  // User-fixable errors (bad files, missing data, etc.)
  INVALID_ZIP: 'INVALID_ZIP',                   // ZIP is corrupted
  MISSING_FILES: 'MISSING_FILES',               // Required files not in ZIP
  INVALID_JSON: 'INVALID_JSON',                 // JSON parsing failed
  INVALID_CSV: 'INVALID_CSV',                   // CSV parsing failed
  SCHEMA_MISMATCH: 'SCHEMA_MISMATCH',           // File doesn't match schema
  MISSING_REQUIRED_FIELDS: 'MISSING_REQUIRED_FIELDS', // Required field not found
  EMPTY_EXPORT: 'EMPTY_EXPORT',                 // No valid data in export

  // System/Infrastructure errors (our problem, not theirs)
  PYODIDE_INIT_FAILED: 'PYODIDE_INIT_FAILED',   // Pyodide WASM failed to load
  WORKER_TIMEOUT: 'WORKER_TIMEOUT',             // Worker didn't respond
  WORKER_CRASHED: 'WORKER_CRASHED',             // Worker died
  PARSER_ERROR: 'PARSER_ERROR',                 // Parsing logic error
  DATABASE_ERROR: 'DATABASE_ERROR',             // IndexedDB error
  NETWORK_ERROR: 'NETWORK_ERROR',               // Failed to fetch schemas/files
  UNKNOWN_ERROR: 'UNKNOWN_ERROR',               // Uncategorized error
};

/**
 * classify an error into a type for UI display.
 * 
 * @param {string} message - error message from worker or parser
 * @param {string} source - where error came from ('worker', 'database', 'parser')
 * @returns {string} ERROR_TYPES value
 */
export function classifyError(message = '', source = '') {
  const msg = String(message).toLowerCase();

  if (msg.includes('pyodide') || msg.includes('wasm')) {
    return ERROR_TYPES.PYODIDE_INIT_FAILED;
  }
  if (msg.includes('timeout')) {
    return ERROR_TYPES.WORKER_TIMEOUT;
  }
  if (msg.includes('worker') || msg.includes('crashed')) {
    return ERROR_TYPES.WORKER_CRASHED;
  }

  if (msg.includes('fetch') || msg.includes('network')) {
    return ERROR_TYPES.NETWORK_ERROR;
  }

  if (msg.includes('json') || msg.includes('parse')) {
    return ERROR_TYPES.INVALID_JSON;
  }
  if (msg.includes('csv')) {
    return ERROR_TYPES.INVALID_CSV;
  }
  if (msg.includes('zip')) {
    return ERROR_TYPES.INVALID_ZIP;
  }

  if (msg.includes('schema') || msg.includes('no schema found')) {
    return ERROR_TYPES.SCHEMA_MISMATCH;
  }
  if (msg.includes('field') || msg.includes('missing')) {
    return ERROR_TYPES.MISSING_REQUIRED_FIELDS;
  }

  if (msg.includes('database') || msg.includes('indexeddb') || msg.includes('dexie')) {
    return ERROR_TYPES.DATABASE_ERROR;
  }

  // Default
  if (source === 'worker') return ERROR_TYPES.PARSER_ERROR;
  if (source === 'database') return ERROR_TYPES.DATABASE_ERROR;

  return ERROR_TYPES.UNKNOWN_ERROR;
}

// is this error likely fixable by user action?
export function isUserError(errorType) {
  const userErrors = [
    ERROR_TYPES.INVALID_ZIP,
    ERROR_TYPES.MISSING_FILES,
    ERROR_TYPES.INVALID_JSON,
    ERROR_TYPES.INVALID_CSV,
    ERROR_TYPES.SCHEMA_MISMATCH,
    ERROR_TYPES.MISSING_REQUIRED_FIELDS,
    ERROR_TYPES.EMPTY_EXPORT,
  ];
  return userErrors.includes(errorType);
}

/**
 * Get user-facing message based on error type
 * (Can expand this as UI requirements solidify)
 * 
 * @param {string} errorType - One of ERROR_TYPES values
 * @returns {string} User-friendly message
 */
export function getErrorMessage(errorType) {
  const messages = {
    [ERROR_TYPES.INVALID_ZIP]: 'The uploaded file is not a valid ZIP archive.',
    [ERROR_TYPES.MISSING_FILES]: 'Required files are missing from the export.',
    [ERROR_TYPES.INVALID_JSON]: 'JSON data could not be parsed. The file may be corrupted.',
    [ERROR_TYPES.INVALID_CSV]: 'CSV data could not be parsed. Please check the file format.',
    [ERROR_TYPES.SCHEMA_MISMATCH]: 'The file format does not match the expected schema.',
    [ERROR_TYPES.MISSING_REQUIRED_FIELDS]: 'Required data fields are missing from the export.',
    [ERROR_TYPES.EMPTY_EXPORT]: 'No valid data found in the export.',
    [ERROR_TYPES.PYODIDE_INIT_FAILED]: 'Failed to initialize the parsing engine. Please try again.',
    [ERROR_TYPES.WORKER_TIMEOUT]: 'The parser is taking too long. Please try a smaller file.',
    [ERROR_TYPES.WORKER_CRASHED]: 'The parser encountered an unexpected error. Please try again.',
    [ERROR_TYPES.PARSER_ERROR]: 'An error occurred while parsing the data.',
    [ERROR_TYPES.DATABASE_ERROR]: 'Failed to save data. Please try again.',
    [ERROR_TYPES.NETWORK_ERROR]: 'Failed to fetch required resources. Please check your connection.',
    [ERROR_TYPES.UNKNOWN_ERROR]: 'An unexpected error occurred.',
  };

  return messages[errorType] || 'An error occurred.';
}
