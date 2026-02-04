import json as jsonlib
import hjson
import json5
import uuid
from base import BaseParser
from parseresult import ParseResult
from errors import FileLevelError, RecordLevelError, FieldLevelError
from time_utils import parse_date, unix_ms
from typing import Callable, Any, List

# Try to import demjson3 for extra-lenient parsing, but make it optional
try:
    import demjson3
    HAS_DEMJSON3 = True
except ImportError:
    HAS_DEMJSON3 = False
    demjson3 = None

class JSONParser(BaseParser):

    @classmethod
    def get(cls, row: Any, path: str, default: Any = "NULL") -> Any:
        if not path or row is None: return default
        if isinstance(row, dict) and path in row: return row[path] if row[path] is not None else default
        curr = row
        for part in path.split('.'):
            p = part[1:-1] if len(part) > 1 and part.startswith("'") and part.endswith("'") else part

            # handle array indexing: e.g., push_tokens[0]
            if "[" in p and p.endswith("]"):
                p, idx_str = p[:-1].split("[")
                try:
                    idx = int(idx_str)
                except ValueError:
                    return default
                curr = curr.get(p) if isinstance(curr, dict) else None
                if isinstance(curr, list) and len(curr) > idx:
                    curr = curr[idx]
                else:
                    return default
            elif isinstance(curr, dict):
                curr = curr.get(p)
            else:
                return default
                
        return curr if curr is not None else default

    @classmethod
    def parse(cls, s: str, filename: str, cfg: List[dict], default="", **kwargs):
        """
        example cfg: [
            { "temporal": "", "category": "",  "parser": { ... }, "fields": [ ... ] }, 
            ...
        ]
        """
        result = ParseResult()

        try:
            parsed = cls.str_to_json(s)
            # Handle both old (single return) and new (tuple with errors) formats
            if isinstance(parsed, tuple) and len(parsed) == 2:
                raw_json, str_to_json_errors = parsed
                for err in str_to_json_errors:
                    result.add_error(err)
            else:
                raw_json = parsed
        except Exception as e:
            result.add_error(FileLevelError(f"Failed to parse JSON: {str(e)}", 
                                          context={'filename': filename, 'error_type': type(e).__name__}))
            return result
        
        try:
            json_lst = cls._resolve_root(raw_json, cfg[0].get("parser", {}))  # assume all cfg share the same root
        except Exception as e:
            result.add_error(FileLevelError(f"Failed to resolve JSON root: {str(e)}", 
                                          context={'filename': filename}))
            return result
        
        if not json_lst:
            result.add_error(RecordLevelError(f"No records found after resolving root", 
                                            context={'filename': filename}))
            return result
        
        filters = cls.make_filter(cfg)
        result.stats['total_records_attempted'] = len(json_lst)

        for idx, e in enumerate(json_lst):
            try:
                in_category_i = [f(e) for f in filters]  # list of bools
                if len(in_category_i) > 1 and all(in_category_i):
                    result.add_error(RecordLevelError(f"Entry matches multiple categories",
                                                     context={'filename': filename, 'row_idx': idx}))
                    result.stats['records_failed'] += 1
                    continue
                
                category_idx = next((i for i, val in enumerate(in_category_i) if val), None)

                if category_idx is not None:
                    parser_cfg = cfg[category_idx]
                    try:
                        data = cls.map_fields(e, parser_cfg.get("fields", []), default)
                        result.stats['fields_extracted'] += len([f for f in parser_cfg.get("fields", []) if f.get("name") in data])
                        
                        data.update({
                            'id': uuid.uuid4().hex,
                            'sketch_id': kwargs.get('sketch_id', default),
                            'timeline_id': kwargs.get('timeline_id', default),
                            'source_file': filename,
                            'category': parser_cfg.get("category", "default"),
                            'original_record': str(e),
                            'created_at': kwargs.get('created_at', default),
                        })

                        if parser_cfg.get("temporal", "") == "event":
                            result.events.append(data)
                            result.stats['records_successful'] += 1
                        elif parser_cfg.get("temporal", "") == "state":
                            result.states.append(data)
                            result.stats['records_successful'] += 1
                    except Exception as e:
                        result.add_error(RecordLevelError(f"Failed to map fields: {str(e)}",
                                                         context={'filename': filename, 'row_idx': idx}))
                        result.stats['records_failed'] += 1
            except Exception as e:
                result.add_error(RecordLevelError(f"Failed to process record: {str(e)}",
                                                 context={'filename': filename, 'row_idx': idx}))
                result.stats['records_failed'] += 1
        
        return result

    
    @classmethod
    def _resolve_root(cls, raw_json: dict | list, parser_cfg: dict) -> dict | list:
        json_root = parser_cfg.get("json_root", None)
        if not json_root or json_root == "[]":
            return raw_json if isinstance(raw_json, list) else [raw_json]
        root = json_root[:-2] if json_root.endswith("[]") else json_root
        return cls.get(raw_json, root, default=[])

    @classmethod
    def str_to_json(cls, s: str) -> str:
        # differs between inherited classes
        return cls.basic_str_to_json(s)

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
    def make_filter(cls, parser_info: list[dict]) -> List[Callable]:
        filters = []
        for pinfo in parser_info:
            fcfg = pinfo.get("parser", {}).get("filter", None)
            """
            fcfg = EITHER 
                {source: "event", op: "==", value: "Email Added"} 
            OR
                {
                    logic: "all" or"any", 
                    conditions: [ {source: "event", op: "==", value: "Email Added"} , ...]
                }
            """
            if fcfg is None:
                filters.append(lambda row: True)
                continue
            logic = fcfg.get("logic")
            
            if logic is not None: # if fcfg is {logic: ..., conditions: [...]}
                child_conditions = [cls.filter_leaf(cond) for cond in fcfg.get("conditions", [])]
                if logic.lower() == "any":
                    filters.append(lambda row, c=child_conditions: any(cond(row) for cond in c))
                elif logic.lower() == "all":
                    filters.append(lambda row, c=child_conditions: all(cond(row) for cond in c))
            
            else: # fcfg is a single condition
                filters.append(cls.filter_leaf(fcfg))
        
        return filters      


    @classmethod 
    def filter_leaf(cls, cfg: dict) -> Callable:
        if not isinstance(cfg, dict): return lambda row: False
        field = cfg.get("field")
        op = cfg.get("op")
        value = cfg.get("value")
        if field is None or op is None or value is None:
            return lambda row: False
        value = str(value)
        if op in cls.op_mapping["eq"]:
            return lambda row: str(cls.get(row, field)) == value
        if op in cls.op_mapping["ne"]:
            return lambda row: str(cls.get(row, field)) != value
        if op in cls.op_mapping["contains"]:
            return lambda row: value in str(cls.get(row, field))
        if op in cls.op_mapping["startswith"]:
            return lambda row: str(cls.get(row, field)).startswith(value)
        if op in cls.op_mapping["endswith"]:
            return lambda row: str(cls.get(row, field)).endswith(value)
        return lambda row: False


            
    @classmethod
    def map_fields(cls, row: dict, fields: List[dict], default: Any = "") -> dict:
        res = {}
        for f in fields:
            # f['name'] is the clean/standardized key (see all_fields.yaml)
            # f['source'] is the JSON path
            name, source, ftype = f.get("name"), f.get("source"), f.get("type", "string")       
            
            # Handle coalesce (if source is a list)
            if isinstance(source, list):
                if f.get("transform", "").lower() == "coalesce":
                    val = next((cls.get(row, s) for s in source if cls.get(row, s) is not None), default)
                else:
                    val = cls.get(row, source[0], default)
            else:
                val = cls.get(row, source, default)

            if ftype in ["datetime", "timestamp", "date"]:
                val = unix_ms(parse_date(str(val)))

            res[name] = val
        return res     