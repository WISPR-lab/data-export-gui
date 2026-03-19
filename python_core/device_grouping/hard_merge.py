#  HARD MERGE
#  merge devices if they have the same deterministic, unique identifier
#  this is done by the system, user cannot unmerge

import uuid
import json
from utils.redaction_utils import compare_redacted_vals, get_unredacted_val
from device_grouping.shared_utils import union_find, merge_attrs, deduplicate_origins, HARD_KEYS

IS_HARD_KEY = lambda k: any(k == hk or k.startswith(hk) for hk in HARD_KEYS)


def hard_match(attrs_a: dict, attrs_b: dict) -> bool:
    keys_a = {k for k in attrs_a if IS_HARD_KEY(k)}
    keys_b = {k for k in attrs_b if IS_HARD_KEY(k)}
    for k in keys_a & keys_b:
        if compare_redacted_vals(attrs_a[k], attrs_b[k]):
            return True
    return False



def hard_merge_one_upload(records: list[dict]) -> list[dict]:
    def match(a: dict, b: dict) -> bool:
        return hard_match(a.get('attributes', {}), b.get('attributes', {}))
    
    children = union_find(records, match)

    rows = []
    record_map = {r.get("id"): r for r in records}
    for parent_id, child_id_list in children.items():
        id_list = sorted(list(set([parent_id] + child_id_list)))
        child_records = [record_map[id] for id in set(id_list)] 
        attrs = merge_attrs([r.get("attributes", {}) for r in child_records], mode='hard')
        
        origins = [{
            "origin": r.get("origin"),
            "upload_id": r.get("upload_id")
        } for r in child_records if r.get("origin")]
        origins = deduplicate_origins(origins)
        origins = sorted(origins, key=lambda x: (x["origin"], x["upload_id"]))

        rows.append({
            'id': str(uuid.uuid4()),
            'upload_ids': json.dumps([r.get("upload_id") for r in child_records]),
            'file_ids': json.dumps([r.get("file_id") for r in child_records]),
            'devices_raw_ids': json.dumps(id_list),
            'attributes': json.dumps(attrs),
            'origins': json.dumps(origins),
        })

    return rows


def _find_match(attrs: dict, existing_atomics: list[dict]) -> dict | None:
    hard_values = {k: v for k, v in attrs.items() if IS_HARD_KEY(k) and v}
    
    if not hard_values:
        return None
    
    for existing in existing_atomics:
        existing_attrs = json.loads(existing.get('attributes', '{}'))
        for hard_key, hard_value in hard_values.items():
            existing_hard_value = existing_attrs.get(hard_key)
            if existing_hard_value and compare_redacted_vals(hard_value, existing_hard_value):
                return existing
    
    return None


def split(new_atomics: list[dict], existing_atomics: list[dict]) -> tuple[list[dict], list[dict]]:
    to_insert = []
    to_update = []
    
    for new in new_atomics:
        attrs = json.loads(new.get('attributes', '{}'))
        match = _find_match(attrs, existing_atomics)
        
        if match:
            to_update.append({'new': new, 'existing': match})
        else:
            to_insert.append(new)
    
    return to_insert, to_update