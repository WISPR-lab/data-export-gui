import json as jsonlib
import hjson
import json5
from typing import List, Dict, Any, Optional
from .base import BaseParser
try:
    from python_core.utils.json_utils import get_value_at_path
except ImportError:
    from ..utils.json_utils import get_value_at_path
from errors import FileLevelError, RecordLevelError, FieldLevelError

# Try to import demjson3 for extra-lenient parsing, but make it optional
try:
    import demjson3
    HAS_DEMJSON3 = True
except ImportError:
    HAS_DEMJSON3 = False
    demjson3 = None

class JSONParser(BaseParser):  

    @classmethod      
    def extract(cls, content: str, config: Optional[Dict] = None) -> List[Dict[str, Any]]:
        config = config or {}
        try:
            data = cls.basic_str_to_json(content)
            root_data = cls._resolve_root(data, config)
            
            if isinstance(root_data, list):
                return [x for x in root_data if isinstance(x, dict)]
            elif isinstance(root_data, dict):
                return [root_data]
            return []
        except Exception: #TODO ERROR HANDLING
            return []


    @classmethod
    def basic_str_to_json(cls, s: str):
        # static, inherited
        robust_parsing_methods = [
            ('Standard JSON', lambda st: jsonlib.loads(st)),
            ('Single-quote conversion', lambda st: jsonlib.loads(st.replace("'", '"'))),
        ]
        
        # Add demjson3 if available (lenient parsing for malformed data)
        if HAS_DEMJSON3:
            robust_parsing_methods.append(('demjson3 lenient', lambda st: demjson3.decode(st, strict=False, allow_trailing_comma=True)))
        
        # Add other robust parsers
        robust_parsing_methods.extend([
            ('json5 ES5-style', lambda st: json5.loads(st)),
            ('hjson', lambda st: hjson.loads(st, use_decimal=True, object_pairs_hook=dict))
        ])

        errors_encountered = []
        jsonobj = None
        
        for name, method in robust_parsing_methods:
            try:
                jsonobj = method(s)
                break
            except Exception as e:
                errors_encountered.append(f"{name}: {type(e).__name__}: {str(e)}")
                continue
        
        if jsonobj is None:
            raise FileLevelError(f"Unable to parse JSON with any method. Attempts: {'; '.join(errors_encountered)}")
        
        return jsonobj


        
    @classmethod
    def _resolve_root(cls, raw_json: dict | list, parser_cfg: dict) -> dict | list:
        json_root = parser_cfg.get("json_root", None)
        
        if not json_root:
            return raw_json if isinstance(raw_json, list) else [raw_json]
            
        if json_root == "[]":
            return raw_json if isinstance(raw_json, list) else [raw_json]
        
        # Use centralized utility for traversal
        # Clean up empty brackets first if they imply list assertion
        clean_path = json_root.replace('[]', '')
        root = get_value_at_path(raw_json, clean_path)
        
        if root is None:
            return []
            
        return root
        