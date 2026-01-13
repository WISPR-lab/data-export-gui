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
        "formats/format_handler",
        "formats/json_.py",
        "formats/json_labelvalues.py",
        "formats/jsonl.py",
        "formats/csv_multi.py",
        "formats/csv.py",
        "schema.py",
        "timeutils.py"
    ]
    health = {}
    for path in expected_paths:
        health[path] = os.path.exists(path)
    try:
        from formats.jsonl import JSONLHandler
        health["import_test"] = True
    except Exception as e:
        health["import_test"] = False
        health["error"] = str(e)  
    return {"py_function": "test_environment", "health": health}


def validate_schema(schema_str, validation_str):
    from schema_utils import validate_schema
    return {"py_function": "validate_schema"}.update(validate_schema(schema_str, validation_str))

def group_schema_by_path(schema_str: str):
    from schema_utils import group_by_path
    global _CACHED_SCHEMA_GROUPED, _CACHED_SCHEMA_STR
    
    if schema_str != _CACHED_SCHEMA_STR:
        _CACHED_SCHEMA_GROUPED = group_by_path(yaml.safe_load(schema_str))
        _CACHED_SCHEMA_STR = schema_str
    return {"py_function": "group_schema_by_path", "path_schemas": _CACHED_SCHEMA_GROUPED}

def parse(schema_str: str, file_content: str, filename: str):
    # the main entry point for JS --> pyodide. 
    # result = { "rows": [...], "errors": [...] }
    global _CACHED_SCHEMA_GROUPED, _CACHED_SCHEMA_STR
    errors = []

    handler_map


    
    try:
        if schema_str != _CACHED_SCHEMA_STR:
            group_schema_by_path(schema_str)

        path_schema = _CACHED_SCHEMA_GROUPED.get(filename, None)
        if path_schema is None:
            return {
                "rows": [],
                "fatal": True,
                "errors": [{"msg": f"No schema found for file: {filename}"}]
            }
        for dtype in path_schema:
            fmt = dtype.get('parser', {}).get('format', None).upper()
            if fmt == 


        
        # 2. Dynamic Handler Selection
        # We import inside the function or at top level; 
        # inside allows the test_environment to run even if imports are broken.
        try:
            if handler_type.upper() == "JSONL":
                from formats.jsonl import JSONLHandler
                handler = JSONLHandler
            elif handler_type.upper() == "CSV":
                from formats.csv import CSVHandler
                handler = CSVHandler
            else:
                raise ValueError(f"Unsupported handler: {handler_type}")
        except ImportError as e:
            return {"rows": [], "errors": [{"msg": f"Module import failed: {str(e)}"}]}

        # 3. Execution
        # We pass the error list to be populated by the @classmethods
        rows = handler.parse(file_content, _CACHED_SCHEMA, errors)
        
        return {
            "rows": rows,
            "errors": errors
        }

    except Exception as fatal_e:
        return {
            "rows": [],
            "errors": [{"msg": f"FATAL ERROR: {str(fatal_e)}"}]
        }