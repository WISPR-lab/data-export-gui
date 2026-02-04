import sys
import os
import yaml
import importlib

# virtual WASM filesystem root
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

_CACHED_SCHEMA_GROUPED = None
_CACHED_SCHEMA_STR = None

def test_environment():
    # checks if expected file structure exists in the WASM filesystem.
    expected_paths = [
        "base.py",
        "json_.py",
        "json_label_values.py",
        "jsonl_.py",
        "csv_multi.py",
        "csv_.py",
        "schema_utils.py",
        "time_utils.py"
    ]
    health = {}
    for path in expected_paths:
        health[path] = os.path.exists(path)
    try:
        from jsonl_ import JSONLParser
        health["import_test"] = True
    except Exception as e:
        health["import_test"] = False
        health["error"] = str(e)  
    return {"py_function": "test_environment", "health": health}


def validate_schema(schema_str, validation_str):
    # Optional: Implement if needed for pre-upload validation
    return {"py_function": "validate_schema", "valid": True, "errors": []}

def group_schema_by_path(schema_str: str):
    from schema_utils import group_by_file
    global _CACHED_SCHEMA_GROUPED, _CACHED_SCHEMA_STR
    
    if schema_str != _CACHED_SCHEMA_STR:
        grouped, errors = group_by_file(yaml.safe_load(schema_str))
        _CACHED_SCHEMA_GROUPED = grouped
        _CACHED_SCHEMA_STR = schema_str
    return {"py_function": "group_schema_by_path", "path_schemas": _CACHED_SCHEMA_GROUPED}

def parse(schema_str: str, file_content: str, filename: str):
    # the main entry point for JS --> pyodide. 
    # result = ParseResult.to_dict() 
    global _CACHED_SCHEMA_GROUPED, _CACHED_SCHEMA_STR

    try:
        if schema_str != _CACHED_SCHEMA_STR:
            group_schema_by_path(schema_str)

        grouped_schemas = _CACHED_SCHEMA_GROUPED.get(filename, [])
        if not grouped_schemas:
            base_filename = filename.split('/')[-1]
            grouped_schemas = _CACHED_SCHEMA_GROUPED.get(base_filename, [])
            
        if not grouped_schemas:
            from parseresult import ParseResult
            result = ParseResult()
            from errors import RecordLevelError
            result.add_error(RecordLevelError(f"No schema found for file: {filename}",
                                            context={'filename': filename}))
            return result.to_dict()

        # determine the parser type from the first dtype (they should match for same file)
        fmt = grouped_schemas[0].get('parser', {}).get('format', 'json').upper()
        
        handler = None
        if fmt == "JSON":
            from json_ import JSONParser
            handler = JSONParser
        elif fmt == "JSONL":
            from jsonl_ import JSONLParser
            handler = JSONLParser
        elif fmt == "CSV":
            from csv_ import CSVParser
            handler = CSVParser
        elif fmt == "JSON_LABEL_VALUES":
            from json_label_values import JSONLabelValuesParser
            handler = JSONLabelValuesParser
        elif fmt == "CSV_MULTI":
            from csv_multi import CSVMultiParser
            handler = CSVMultiParser
        else:
            from parseresult import ParseResult
            from errors import FileLevelError
            result = ParseResult()
            result.add_error(FileLevelError(f"Unsupported format: {fmt}", 
                                          context={'filename': filename}))
            return result.to_dict()

        # Parse using the handler (which now returns ParseResult)
        result = handler.parse(file_content, filename, grouped_schemas)
        
        return result.to_dict()

    except Exception as fatal_e:
        import traceback
        from parseresult import ParseResult
        from errors import FileLevelError
        
        result = ParseResult()
        result.add_error(FileLevelError(f"FATAL ERROR in parsing: {str(fatal_e)}", 
                                       context={'filename': filename, 'error_type': type(fatal_e).__name__}))
        # Include traceback in stats for debugging
        result.stats['traceback'] = traceback.format_exc()
        
        return result.to_dict()
