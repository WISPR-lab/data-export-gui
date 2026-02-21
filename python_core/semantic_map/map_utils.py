import os
import sys
from utils.misc import clean_target, is_trivial
from utils.json_utils import get_value_at_path
from utils.filter_builder import make_filter
from utils.time_utils import parse_date, unix_ms
    



def static_fields(view: dict):
    if not isinstance(view, dict) or 'static' not in view:
        print(f"[MapUtils] No static fields defined in view: {view}")
        return {}
    return {clean_target(k): v for k,v in view.get("static", {}).items()}



def dynamic_fields(record: dict, view: dict, default=""):
    if not isinstance(view, dict) or 'fields' not in view:
        print(f"[MapUtils] No dynamic fields defined in view: {view}")
        return {}
    if not isinstance(record, dict):
        print(f"[MapUtils] Record is not a dict for dynamic field extraction: {record}")
        return {}
    
    fields = {}
    for f in view.get("fields", []):
        target, source, ftype = f.get("target"), f.get("source"), f.get("type", "string")
        
        if isinstance(source, list):
            if f.get("transform", "").lower() == "coalesce":
                val = next((get_value_at_path(record, s) for s in source \
                            if not is_trivial(get_value_at_path(record, s))), default)
            else:
                val = get_value_at_path(record, source[0], default)  # default to first source if no transform specified
        else:
            val = get_value_at_path(record, source, default)

        if ftype in ["datetime", "timestamp", "date"]:
            val = unix_ms(parse_date(str(val)))
        fields[clean_target(target)] = val
    return fields


def fields(record: dict, view: dict, default=""):
    static = static_fields(view)
    dynamic = dynamic_fields(record, view, default)
    return {**static, **dynamic}


def view_indexes_to_apply(record: dict, views: list):
    # record: raw data dict
    # view: list of views from manifest
    indexes = []
    for i, view in enumerate(views):
        where = view.get('where', {})
        if not where:
            indexes.append(i)
            continue
        f = make_filter(where)
        if f(record):
            indexes.append(i)
    if not indexes:
        print(f"[MapUtils] Record did not match any view filters: {record}")
    return indexes
    


