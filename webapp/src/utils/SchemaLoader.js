// src/utils/SchemaLoader.js
// Loads and validates YAML schemas and data against schema_validation.yaml
import yaml from 'js-yaml';


export async function loadSchema(
  yamlString,
  validate = true,
  validationFile = '/schemas/schema_validation.yaml'
){
  const schema = yaml.load(yamlString);
  let errors = [];
  if (validate) {
    errors = await validateSchema(schema, validationFile);
  }
  if (errors.length > 0) {
    throw new Error('Fatal errors in schema validation: \n' + errors.join('\n'));
  }
  return schema;
}


// ---------------------------------------------------
function _missing(name, postfix=null){ 
  s = `Missing required field: ${name}`;
  if (postfix) {s += `in ${postfix}`;}
  return s;
}
function _invalidType(name, type){ return `Invalid type for field ${name}: expected ${type}`;}
// ---------------------------------------------------


async function validateSchema(schema, validationFile) {
  let errors = [];
  const validator = await fetch(validationFile).then(r => r.text()).then(text => yaml.load(text));
  const valid_categories = _flattenCategories(validator.categories);
  errors = _validateHelper(errors, schema, validator.top_level_fields);
  if (errors.length > 0) { return errors.concat(['fatal']); }

  for (const [i, dt] of (schema.data_types || []).entries()) {
    errors = _validateHelper(errors, dt, validator.data_type_fields, `data_types[${i}]`);
    if (errors.length > 0) { return errors.concat(['fatal']); }
    
    // check category
    if (!(dt.category in valid_categories)) {
      errors.push("Invalid value for in data_types[" + i + "].category");
    }

    // check temporal specific fields
    if (dt.temporal == "event"){
      for (const ef of validator.event_file_fields.required) {
        errors = _validateHelper(errors, dt, validator.event_file_fields, `data_types[${i}]`);
      }
    } else if (dt.temporal == "state"){
      for (const sf of validator.state_file_fields.required) {
        errors = _validateHelper(errors, dt, validator.state_file_fields, `data_types[${i}]`);
      }
    }

    // all other fields
    for (const [j, f] of (dt.files || []).entries()) {
      errors = _validateHelper(errors, f, validator.file_fields, `data_types[${i}].files[${j}]`);

      if ('identifiers' in f && typeof f.identifiers === 'object' && f.identifiers !== null) {
        for (const [k, id] of (f.identifiers || []).entries()) {
          errors = _validateHelper(errors, id, validator.identifier_fields, `data_types[${i}].files[${j}].identifiers[${k}]`);
        } // for identifier
      }
    } // for files
  } // for dt

  return errors;
} // end validate


function _flattenCategories(obj, prefix = '', result = []) {
  for (const key in obj) {
    const value = obj[key];
    const current = prefix ? `${prefix}.${key}` : key;
    result.push(current);
    if (Array.isArray(value)) {
      for (const item of value) {
        result.push(`${current}.${item}`);
      }
    } else if (typeof value === 'object' && value !== null) {
      _flattenCategories(value, current, result);
    }
  }
  return result;
}

function _validateHelper(errors, subSchema, subValidator, postfix=null){
  for (const f of subValidator.required) {
    const name = Object.keys(f)[0];
    const type = f[name];
    if (!(name in subSchema)) {
      errors.push(_missing(name, postfix));
    } else if (!validateField(subSchema[name], type)) {
      errors.push(_invalidType(name, type));
    }
  }
  for (const f of subValidator.optional) {
    const name = Object.keys(f)[0];
    const type = f[name];
    if (name in subSchema && !validateField(subSchema[name], type)) {
      errors.push(_invalidType(name, type));
    }
  }
  return errors;
}


export function validateField(value, type) {
  if (Array.isArray(type)) {
    return type.some(t => validateField(value, t));
  }
  if (type === 'string') return typeof value === 'string';
  if (type === 'integer') return Number.isInteger(value);
  if (type === 'date') return typeof value === 'string' && !isNaN(Date.parse(value));
  if (type === 'list') return Array.isArray(value);
  if (type === 'list(string)') return Array.isArray(value) && value.every(v => typeof v === 'string');
  if (type === 'dict') return typeof value === 'object' && value !== null && !Array.isArray(value);
  if (type === 'dict(string)') return typeof value === 'object' && value !== null && !Array.isArray(value) && Object.values(value).every(v => typeof v === 'string');
  if (type.startsWith('enum(')) {
    const allowed = type.slice(5, -1).split(',').map(s => s.trim());
    return allowed.includes(value);
  }
  return true; // fallback: accept anything
}
