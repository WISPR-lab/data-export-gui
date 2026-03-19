#  HARD MERGE
#  merge devices if they have the same deterministic, unique identifier
#  this is done by the system, user cannot unmerge

import re
from utils.redaction_utils import compare_redacted_vals, get_unredacted_val
from collections import defaultdict
import uuid
import json

HARD_KEYS = {
    "device_id", # anything in this family
    "device_serial_number",
    "device_imei",
    "device_meid"
}

IS_HARD_KEY = lambda k: any(k == hk or k.startswith(hk) for hk in HARD_KEYS)



def hard_match(attrs_a: dict, attrs_b: dict) -> bool:
    keys_a = {k for k in attrs_a if IS_HARD_KEY(k)}
    keys_b = {k for k in attrs_b if IS_HARD_KEY(k)}
    for k in keys_a & keys_b:
        if compare_redacted_vals(attrs_a[k], attrs_b[k]):
            return True
    return False


def _merge_attrs_pairwise(attrs_a: dict, attrs_b: dict) -> dict:
    merged = {}
    for k in set(attrs_a) | set(attrs_b):
        v_a, v_b = attrs_a.get(k), attrs_b.get(k)
        if k in HARD_KEYS:
            merged[k] = get_unredacted_val(v_a, v_b)[0] or v_a or v_b
        else:
            merged[k] = v_a if (v_a and v_a != '') else v_b
        # TODO add more granularity
    return merged

def merge_attrs(attrs_list: list[dict]) -> dict:
    if not attrs_list:
        return {}
    merged = attrs_list[0].copy()
    for attrs in attrs_list[1:]:
        merged = _merge_attrs_pairwise(merged, attrs)
    return merged


def _find(parent: dict, x: str) -> str:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def hard_merge(records: list[dict]) -> list[dict]:
    parent = {r.get("id"): r.get("id") for r in records}
    
    for i, dct_a in enumerate(records):
        id_a, attrs_a = dct_a.get('id'), dct_a.get('attributes', {})
        for dct_b in records[i + 1:]:
            id_b, attrs_b = dct_b.get('id'), dct_b.get('attributes', {})
            # TODO have some kind of guardrail here to make sure not merging records
            # with obviously different attributes (i.e. different OS types)
            if hard_match(attrs_a, attrs_b):
                parent[_find(parent, id_a)] = _find(parent, id_b)

    children = defaultdict(list)
    for r in records:
        children[_find(parent, r.get("id"))].append(r.get("id"))
    # children[parent] = [list, of, child, ids]

    rows = []
    record_map = {r.get("id"): r for r in records}
    for parent_id, child_id_list in children.items():
        id_list = sorted(list(set([parent_id] + child_id_list)))
        child_records = [record_map[id] for id in set(id_list)] 
        attrs = merge_attrs([r.get("attributes", {}) for r in child_records])
        origins = [r.get("origin") for r in child_records if r.get("origin")]
        origins = sorted(list(set(origins)))

        rows.append({
            'id': str(uuid.uuid4()),
            'upload_ids': json.dumps([r.get("upload_id") for r in child_records]),
            'file_ids': json.dumps([r.get("file_id") for r in child_records]),
            'devices_raw_ids': json.dumps(id_list),
            'attributes': json.dumps(attrs),
            'origins': json.dumps(origins),
        })

    return rows
