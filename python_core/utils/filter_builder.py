from typing import Callable, List
from json_utils import get_value_at_path  # nested json traversal


OP_MAPPING = {
    "eq": ["==", "===", "=", "eq"],
    "ne": ["!=", "!==", "ne", "neq"],
    "contains": ["contains", "includes"],
    "startswith": ["startswith", "starts_with"],
    "endswith": ["endswith", "ends_with"]
}


def _filter_leaf(source:str, op:str, value:str, default=True) -> Callable:
    
    if source is None or not isinstance(source, str):
        print(f"Filter condition missing 'source' or value is not a string: {where}")
        return lambda dct: default

    if value is None:
        print(f"Filter condition missing 'value': {where}. Defaulting to empty string.")
        value = ""
    else:
        value = str(value)
    
    if op is None:
        print(f"Filter condition missing 'op': {where}. Defaulting to equality check.")
        op = "=="

    if op in OP_MAPPING["eq"]:
        return lambda dct: str(get_value_at_path(dct, source)) == value
    if op in OP_MAPPING["ne"]:
        return lambda dct: str(get_value_at_path(dct, source)) != value
    if op in OP_MAPPING["contains"]:
        return lambda dct: value in str(get_value_at_path(dct, source))
    if op in OP_MAPPING["startswith"]:
        return lambda dct: str(get_value_at_path(dct, source)).startswith(value)
    if op in OP_MAPPING["endswith"]:
        return lambda dct: str(get_value_at_path(dct, source)).endswith(value)
    
    print(f"Unsupported operator in filter config: {op}")
    return lambda dct: default




def make_filter(where: dict, default=True) -> List[Callable]:
    """
    where = EITHER 
        {field: "event", op: "==", value: "Email Added"} 
    OR
        {
            logic: "all" or"any", 
            conditions: [ {field: "event", op: "==", value: "Email Added"} , ...]
        }
    """

    if where is None or where is not isinstance(where, dict):
        print(f"Invalid filter config: {where}.")
        return lambda dct: default

    if all(k in where.keys() for k in ["source", "op", "value"]):
        return _filter_leaf(where['source'], where['op'], where['value'], default=default)
 
    if "logic" in where.keys() and "conditions" in where.keys():
        if not all( \
            isinstance(cond, dict) and \
            (k in cond.keys() for k in ["source", "op", "value"]) \
            for cond in where.get("conditions", [])):
            
            print(f"Invalid filter config: {where}. 'conditions' should be a list of dicts, each with keys 'source', 'op', and 'value'.")
            return lambda dct: default 
        
        child_conditions = [_filter_leaf(cond, default=default) for cond in where.get("conditions", [])]
        if where['logic'].lower() == "any":
            return lambda dct, c=child_conditions: any(cond(dct) for cond in c)
        elif where['logic'].lower() == "all":
            return lambda dct, c=child_conditions: all(cond(dct) for cond in c)
    
    print(f"Invalid filter config: {where}.")
    return lambda dct: default


