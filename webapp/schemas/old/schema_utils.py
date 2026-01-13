import yaml

# --------- SCHEMA VALIDATION --------- #

def validate_schema(schema_str, validation_str):
    # validate the schema against the validation rules provided in validation_str
    # returns {'fatal': bool, 'errors': [...] }

    errors = []
    try:
        schema = yaml.safe_load(schema_str)
        validator = yaml.safe_load(validation_str)
    except yaml.YAMLError as e:
        errors.append(f"YAML parsing error: {e}")
        return {"fatal": True, "errors": errors}

    valid_categories = _flatten_categories(validator['valid_categories'])
    errors += _validate_helper(errors, schema, validator['top_level_fields'])
    if errors:
        return {"fatal": True, "errors": errors}

    for i, dtype in enumerate(schema.get('data_types', [])):
        errors += _validate_helper(dtype, validator['data_type_fields'], f"data_types[{i}]")
        
        if errors:
            return {"fatal": True, "errors": errors}
        
        if dtype.get('category') not in valid_categories:
            errors.append(f"Invalid value for in data_types[{i}].category")
        
        for j, file in enumerate(dtype.get('files', [])):
            errors += _validate_helper(file, validator['file_fields'], f"data_types[{i}].files[{j}]")
            if dtype.get('temporal') == "event":
                errors += _validate_helper(file, validator['event_file_fields'], f"data_types[{i}].files[{j}]")
            elif dtype.get('temporal') == "state":
                errors += _validate_helper(file, validator['state_file_fields'], f"data_types[{i}].files[{j}]")

            if 'identifiers' in file.keys() \
                and isinstance(file['identifiers'], dict):

                req = validator['identifier_fields'].get('required')
                req = {} if req is None else req
                opt = validator['identifier_fields'].get('optional')
                opt = {} if opt is None else opt
                ok_id_fields = list(req.keys()) + list(opt.keys())

                for id, _ in file.get('identifiers', {}).items():
                    if id not in ok_id_fields:
                        errors.append(f"Unknown identifier field {id} in data_types[{i}].files[{j}].identifiers")
    
    return {"fatal": False, "errors": errors}


def _validate_helper(sub_schema, sub_validator, postfix=None):
    errors = []
    for name, type_ in sub_validator.get('required', {}).items():
        if name not in sub_schema:
            errors.append(_missing(name, postfix))
        elif not _validate_field(sub_schema[name], type_):
            errors.append(_invalid_type(name, type_))
    
    for name, type_ in sub_validator.get('optional', {}).items():
        if name in sub_schema and not _validate_field(sub_schema[name], type_):
            errors.append(_invalid_type(name, type_))
    return errors


def _validate_field(value, type_):
    if isinstance(type_, list):
        return any(_validate_field(value, t) for t in type_)
    if type_ == 'string':
        return isinstance(value, str)
    if type_ == 'integer':
        return isinstance(value, int)
    if type_ == 'date':
        # Simple check: string that parses as date
        from dateutil.parser import parse
        try:
            return isinstance(value, str) and parse(value)
        except Exception:
            return False
    if type_ == 'list':
        return isinstance(value, list)
    if type_ == 'list(string)':
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if type_ == 'dict':
        return isinstance(value, dict)
    if type_ == 'dict(string)':
        return isinstance(value, dict) and all(isinstance(v, str) for v in value.values())
    if type_.startswith('enum('):
        allowed = [s.strip() for s in type_[5:-1].split(',')]
        return value in allowed
    return True  # fallback


def _missing(name, postfix=None):
    s = f"Missing required field: {name}"
    if postfix:
        s += f" in {postfix}"
    return s

def _invalid_type(name, type_):
    return f"Invalid type for field {name}: expected {type_}"


def _flatten_categories(obj, prefix='', result=None):
    if result is None:
        result = []
    for key, value in obj.items():
        current = f"{prefix}.{key}" if prefix else key
        result.append(current)
        if isinstance(value, list):
            for item in value:
                result.append(f"{current}.{item}")
        elif isinstance(value, dict):
            _flatten_categories(value, current, result)
    return result





# --------- group by path --------- #
def group_by_path(schema_yaml):
    res = {} 
    for dtype in schema_yaml.get('data_types', []):
        for file in dtype.get('files', []):
            if not isinstance(file, dict):
                continue
            path = file.get('path')
            if path is None:
                continue
            if path not in res:
                res[path] = []
            info = {'temporal': dtype.get('temporal', ""), 'category': dtype.get('category', "")}
            info.update(file)
            res[path].append(info)
    return res




#------------ VALIDATE SCHEMA 2 ------------- #