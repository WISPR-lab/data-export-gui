import json as jsonlib
import hjson
import json5
import demjson3
import uuid
from .base import BaseParser
from .time_utils import parse_date, unix_ms
from typing import Callable, Any, List

class JSONParser(BaseParser):

    @classmethod
    def get(row: Any, path: str, default: Any = "NULL") -> Any:
        if not path or row is None: return default
        if path in row: return row[path] if row[path] is not None else default
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
    def parse(cls, s: str, filename: str, cfg: list[dict], default="", **kwargs):
        """
        example cfg: [
            { "temporal": "", "category": "",  "parser": { ... }, "fields": [ ... ] }, 
            ...
        ]
        """
        errors = []
        events = []
        states = []

        raw_json = cls.str_to_json(s)
        json_lst = cls._resolve_root(raw_json, cfg[0].get("parser", {}))  # assume all cfg share the same root
        filters = cls.make_filter(cfg, cls.get)

        for e in json_lst:
            in_category_i = [f(e) for f in filters] # list of bools eq in length to cfg
            if len(in_category_i) > 1 and all(in_category_i):
                errors.append(f"entry matches multiple categories in {filename}: {str(e)}")
            category_idx = next((i for i, val in enumerate(in_category_i) if val), None)

            if category_idx is not None:
                parser_cfg = cfg[category_idx]
                data = cls.map_fields(e, parser_cfg.get("fields", []), default)
                data.update({
                    'id': uuid.uuid4().hex,
                    'sketch_id': kwargs.get('sketch_id', default),
                    'timeline_id': kwargs.get('timeline_id', default),
                    'source_file': filename,
                    'category': parser_cfg.get("category", "default"),
                    'raw_str': str(e),
                    'created_at': kwargs.get('created_at', default),
                })

                if parser_cfg.get("temporal", "") == "event":
                    events.append(data)
                elif parser_cfg.get("temporal", "") == "state":
                    states.append(data)
        return events, states, errors

    
    @classmethod
    def _resolve_root(cls, raw_json: dict | list, parser_cfg: dict) -> dict | list:
        json_root = parser_cfg.get("json_root", None)
        if not json_root or json_root == "[]":
            return raw_json if isinstance(raw_json, list) else [raw_json]
        root = json_root[:-2] if json_root.endswith("[]") else json_root
        return cls.json_get(raw_json, root, default=[])

    @classmethod
    def str_to_json(cls, s: str) -> str:
        # differs between inherited classes
        return cls.basic_str_to_json(s)

    @classmethod
    def basic_str_to_json(cls, s: str):
        # static, inherited
        robust_parsing_methods = [
            lambda st: jsonlib.loads(st),  # Standard JSON
            lambda st: jsonlib.loads(st.replace("'", '"')),  # Convert single quotes
            lambda st: demjson3.decode(st, strict=False, allow_trailing_comma=True),  # Lenient parsing
            lambda st: json5.loads(st),  # ES5-style parsing
            lambda st: hjson.loads(st, use_decimal=True, object_pairs_hook=dict)
        ]

        for _, method in enumerate(robust_parsing_methods):
            try:
                jsonobj = method(s)
                break
            except Exception as e:
                continue
        if jsonobj is None:
            raise RuntimeError("unable to parse") # TODO custom err
        return jsonobj
    


    @classmethod
    def make_filter(cls, parser_info: list[dict], get_fn: Callable) -> List[Callable]:
        filters = []

        for pinfo in parser_info:
            fcfg = pinfo.get("parser", {}).get("filter", None)
            if fcfg is None:
                filters.append(lambda row: True)
                continue
            logic = fcfg.get("logic")
            if logic is not None:
                child_conditions = [cls._filter_leaf(get_fn, cond) for cond in fcfg.get("conditions", [])]
                if logic.lower() == "any":
                    filters.append(lambda row, c=child_conditions: any(cond(row) for cond in c))
                elif logic.lower() == "all":
                    filters.append(lambda row, c=child_conditions: all(cond(row) for cond in c))
            else:
                filters.append(cls._filter_leaf(get_fn, fcfg))
        return filters      


    @classmethod 
    def _filter_leaf(cls, get_fn: Callable, cfg: dict) -> Callable:
        field = cfg.get("field")
        op = cfg.get("op")
        value = cfg.get("value")
        if field is None or op is None or value is None:
            return lambda row: False
        value = str(value)
        if op in cls.op_mapping["eq"]:
            return lambda row: str(get_fn(row, field)) == value
        if op in cls.op_mapping["ne"]:
            return lambda row: str(get_fn(row, field)) != value
        if op in cls.op_mapping["contains"]:
            return lambda row: value in str(get_fn(row, field))
        if op in cls.op_mapping["startswith"]:
            return lambda row: str(get_fn(row, field)).startswith(value)
        if op in cls.op_mapping["endswith"]:
            return lambda row: str(get_fn(row, field)).endswith(value)
        return lambda row: False


            
    @classmethod
    def map_fields(cls, row: dict, fields: List[dict], default: Any = "") -> dict:
        res = {}
        for f in fields:
            # f['name'] is the clean/standardized key (see all_fields.yaml)
            # f['source'] is the JSON path
            name, source, type = f.get("name"), f.get("source"), f.get("type", "string")       
            
            # Handle coalesce (if source is a list)
            if isinstance(source, list):
                if f.get("transform", "").lower() == "coalesce":
                    val = next((cls.get(row, s) for s in source if cls.get(row, s) is not None), default)
                else:
                    val = cls.get(row, source[0], default)
            else:
                val = cls.get(row, source, default)

            if type in ["datetime", "timestamp", "date"]:
                val = unix_ms(parse_date(str(val)))

            res[name] = val
        return res     