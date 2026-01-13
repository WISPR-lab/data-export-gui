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
        "json_labelvalues.py",
        "jsonl.py",
        "csv_multi.py",
        "csv.py",
        "schema_utils.py",
        "time_utils.py"
    ]
    health = {}
    for path in expected_paths:
        health[path] = os.path.exists(path)
    try:
        from jsonl import JSONLParser
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
    # result = { "events": [...], "states": [...], "errors": [...] }
    global _CACHED_SCHEMA_GROUPED, _CACHED_SCHEMA_STR

    try:
        if schema_str != _CACHED_SCHEMA_STR:
            group_schema_by_path(schema_str)

        path_schemas = _CACHED_SCHEMA_GROUPED.get(filename, [])
        if not path_schemas:
            # Try matching with filename without leading paths in case the zip structure differs
            base_filename = filename.split('/')[-1]
            path_schemas = _CACHED_SCHEMA_GROUPED.get(base_filename, [])
            
        if not path_schemas:
            return {
                "events": [],
                "states": [],
                "fatal": False,
                "errors": [{"msg": f"No schema found for file: {filename}"}]
            }

        # determine the parser type from the first dtype (they should match for same file)
        fmt = path_schemas[0].get('parser', {}).get('format', 'json').upper()
        
        handler = None
        if fmt == "JSON":
            from json_ import JSONParser
            handler = JSONParser
        elif fmt == "JSONL":
            from jsonl import JSONLParser
            handler = JSONLParser
        elif fmt == "CSV":
            from csv import CSVParser
            handler = CSVParser
        elif fmt == "JSON_LABEL_VALUES":
            from json_labelvalues import JSONLabelValuesParser
            handler = JSONLabelValuesParser
        elif fmt == "CSV_MULTI":
            from csv_multi import CSVMultiParser
            handler = CSVMultiParser
        else:
            return {
                "events": [],
                "states": [],
                "fatal": True,
                "errors": [{"msg": f"Unsupported format: {fmt} for file {filename}"}]
            }

        events, states, parser_errors = handler.parse(file_content, filename, path_schemas)
        
        return {
            "events": events,
            "states": states,
            "errors": parser_errors
        }

    except Exception as fatal_e:
        import traceback
        return {
            "events": [],
            "states": [],
            "fatal": True,
            "errors": [{"msg": f"FATAL ERROR in pyodide parse: {str(fatal_e)}", "traceback": traceback.format_exc()}]
        }
