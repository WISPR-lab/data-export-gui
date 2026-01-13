import yaml



class Schema:
    def __init__(self, schema_yaml_str: str, validation_str: str = "", validate = False):
        
        self.schema = yaml.safe_load(schema_yaml_str)
        self.errors = []
        self.healthy = True

        if validate:
            if not validation_str:
                raise RuntimeError("validation string required for schema validation")
            self.errors = self.validate_schema(validation_str)



    def validate_schema(self, validation_str):
        validator = yaml.safe_load(validation_str)
        errors = []
        valid_categories = self._flatten_categories(validator['valid_categories'])
        errors = self._validate_helper(errors, self.schema, validator['top_level_fields'])
        if errors:
            self.healthy = False
            return errors + ['fatal']

        for i, dtype in enumerate(self.schema.get('data_types', [])):
            errors += self._validate_helper(dtype, validator['data_type_fields'], f"data_types[{i}]")
            if errors:
                self.healthy = False
                return errors + ['fatal']
            if dtype.get('category') not in valid_categories:
                errors.append(f"Invalid value for in data_types[{i}].category")
            
            for j, file in enumerate(dtype.get('files', [])):
                errors += self._validate_helper(file, validator['file_fields'], f"data_types[{i}].files[{j}]")
                if dtype.get('temporal') == "event":
                    errors += self._validate_helper(file, validator['event_file_fields'], f"data_types[{i}].files[{j}]")
                elif dtype.get('temporal') == "state":
                    errors += self._validate_helper(file, validator['state_file_fields'], f"data_types[{i}].files[{j}]")

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
        return errors
    

    def _validate_helper(self, sub_schema, sub_validator, postfix=None):
        errors = []
        for name, type_ in sub_validator.get('required', {}).items():
            if name not in sub_schema:
                errors.append(self._missing(name, postfix))
            elif not self._validate_field(sub_schema[name], type_):
                errors.append(self._invalid_type(name, type_))
        
        for name, type_ in sub_validator.get('optional', {}).items():
            if name in sub_schema and not self._validate_field(sub_schema[name], type_):
                errors.append(self._invalid_type(name, type_))
        return errors
    

    def _validate_field(self, value, type_):
        if isinstance(type_, list):
            return any(self._validate_field(value, t) for t in type_)
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


    @staticmethod
    def _missing(name, postfix=None):
        s = f"Missing required field: {name}"
        if postfix:
            s += f" in {postfix}"
        return s

    @staticmethod
    def _invalid_type(name, type_):
        return f"Invalid type for field {name}: expected {type_}"


    def _flatten_categories(self, obj, prefix='', result=None):
        if result is None:
            result = []
        for key, value in obj.items():
            current = f"{prefix}.{key}" if prefix else key
            result.append(current)
            if isinstance(value, list):
                for item in value:
                    result.append(f"{current}.{item}")
            elif isinstance(value, dict):
                self._flatten_categories(value, current, result)
        return result


