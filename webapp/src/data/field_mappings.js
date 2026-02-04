/**
 * Field mapping utility
 * Loads field definitions from all_fields.yaml and actual database columns
 * Returns standardized field mappings for meta.mappings
 */

import yaml from 'js-yaml'
import BrowserDB from '../database.js'

/**
 * Load and parse all_fields.yaml schema
 * @returns {Promise<Object>} parsed YAML with time_fields, device_id_fields, misc_fields
 */
async function loadFieldDefinitions() {
  try {
    const response = await fetch('/schemas/all_fields.yaml')
    const text = await response.text()
    const doc = yaml.load(text)
    return {
      timeFields: doc.time_fields || [],
      deviceIdFields: doc.device_id_fields || [],
      miscFields: doc.misc_fields || [],
    }
  } catch (error) {
    console.error('Error loading field definitions from YAML:', error)
    return {
      timeFields: [],
      deviceIdFields: [],
      miscFields: [],
    }
  }
}

/**
 * Get actual column names from events and states tables (optional)
 * Only fetches if data exists; gracefully degrades if no data
 * @param {number} sketchId - sketch ID to query
 * @returns {Promise<Set>} set of unique column names from both tables
 */
async function getActualDatabaseColumns(sketchId) {
  const columns = new Set()
  
  try {
    // Query first event to get column names
    const events = await BrowserDB.getEvents(sketchId, { limit: 1 })
    
    if (events && events.length > 0) {
      const event = events[0]
      Object.keys(event).forEach(key => {
        // Skip internal fields (starting with __)
        if (!key.startsWith('__')) {
          columns.add(key)
        }
      })
    }
  } catch (error) {
    console.debug('No data available yet to determine actual columns (this is OK on first load):', error.message)
  }
  
  return columns
}

/**
 * Determine field type based on schema and naming conventions
 * @param {string} fieldName - the field name
 * @param {Set} timeFields - set of time field names
 * @param {Set} deviceIdFields - set of device ID field names
 * @param {Set} miscFields - set of misc field names
 * @returns {string} type: "timestamp", "device_id", "misc", "category", or "meta"
 */
function getFieldType(fieldName, timeFields, deviceIdFields, miscFields) {
  // Check for category field
  if (fieldName === 'category') {
    return 'category'
  }
  
  // Check if field name contains "timestamp"
  if (fieldName.includes('timestamp')) {
    return 'timestamp'
  }
  
  // Check against schema lists
  if (timeFields.has(fieldName)) {
    return 'timestamp'
  }
  if (deviceIdFields.has(fieldName)) {
    return 'device_id'
  }
  if (miscFields.has(fieldName)) {
    return 'misc'
  }
  
  // Everything else is metadata
  return 'meta'
}

/**
 * Build complete field mappings from YAML schema and actual database columns
 * 
 * @param {number} sketchId - sketch ID
 * @returns {Promise<Array>} array of {field: string, type: string} objects
 */
export async function generateFieldMappings(sketchId) {
  const definitions = await loadFieldDefinitions()
  const dbColumns = await getActualDatabaseColumns(sketchId)
  
  // Convert arrays to Sets for fast lookup
  const timeFieldsSet = new Set(definitions.timeFields)
  const deviceIdFieldsSet = new Set(definitions.deviceIdFields)
  const miscFieldsSet = new Set(definitions.miscFields)
  
  // Combine all schema fields + actual DB columns
  const allFields = new Set([
    ...definitions.timeFields,
    ...definitions.deviceIdFields,
    ...definitions.miscFields,
    ...dbColumns
  ])
  
  // Build mappings with types
  const mappings = Array.from(allFields)
    .sort() // Alphabetical for consistency
    .map(fieldName => ({
      field: fieldName,
      type: getFieldType(fieldName, timeFieldsSet, deviceIdFieldsSet, miscFieldsSet)
    }))
  
  return mappings
}

export default {
  generateFieldMappings
}
