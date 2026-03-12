#  SOFT MERGE
#  Merge devices on manufacturer + model match, accounting for specificity levels.
#  Model/manufacturer sourced from device_* or user_agent_device_* fields (picks most specific).
#  Specificity: 0=generic (brand only), 1=specific (has version/variant).
#  Rules: both specific→exact match; generic+specific→merge except Apple (UA masking); generic+generic→merge except Apple.

import re
from utils.device_lookup import VARIANT_SUFFIXES
from collections import defaultdict
import uuid
import json


GENERIC = {'other', 'unknown', 'phone', 'smartphone', 'tablet', 'android', 'iphone', 'ipad', ''}
UA_MASKING_BLACKLIST = {'apple'}


def _specificity(name: str) -> int:
    if not name:
        return -1
    name = name.strip()
    if not name or name.lower() in GENERIC:
        return 0
    words = {w.lower().rstrip('.,') for w in name.split()}
    if words & VARIANT_SUFFIXES:
        return 1
    if any(c.isdigit() for c in name):
        return 1
    return 0


def _best_value(values: list[str]) -> str:
    candidates = [v.strip() for v in values if v and v.strip()]
    if not candidates:
        return ''
    return max(candidates, key=_specificity)


def _soft_match(attrs_a: dict, attrs_b: dict) -> bool:
    model_a = _best_value([
        attrs_a.get('device_model_name', ''),
        attrs_a.get('user_agent_device_model', ''),
    ])
    model_b = _best_value([
        attrs_b.get('device_model_name', ''),
        attrs_b.get('user_agent_device_model', ''),
    ])
    
    mfr_a = _best_value([
        attrs_a.get('device_manufacturer', ''),
        attrs_a.get('user_agent_device_manufacturer', ''),
    ])
    mfr_b = _best_value([
        attrs_b.get('device_manufacturer', ''),
        attrs_b.get('user_agent_device_manufacturer', ''),
    ])
    
    if not model_a or not model_b or not mfr_a or not mfr_b:
        return False
    

    if mfr_a.lower() != mfr_b.lower():
        return False
    
    spec_a = _specificity(model_a)
    spec_b = _specificity(model_b)
    
    # print(f"[SOFT_MERGE] Comparing: '{model_a}' (spec={spec_a}) vs '{model_b}' (spec={spec_b}) | Mfr: {mfr_a}")
    
    if spec_a >= 1 and spec_b >= 1:
        res = model_a.lower() == model_b.lower()
        # print(f"[SOFT_MERGE] Both specific. Match: {res}")
        return res
    
    if mfr_a.lower() in UA_MASKING_BLACKLIST or mfr_b.lower() in UA_MASKING_BLACKLIST:
        # print(f"[SOFT_MERGE] Apple masking check... No merge for generic/specific mix.")
        return False
    
    # print(f"[SOFT_MERGE] Generic fallback merge enabled.")
    return True


def _merge_attrs_pairwise(attrs_a: dict, attrs_b: dict) -> dict:
    merged = {}
    for k in set(attrs_a) | set(attrs_b):
        v_a, v_b = attrs_a.get(k), attrs_b.get(k)
        merged[k] = v_a if (v_a and v_a != '') else v_b
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




def soft_merge(records: list[dict]) -> list[dict]:
    parent = {r.get("id"): r.get("id") for r in records}
    
    for i, dct_a in enumerate(records):
        id_a, attrs_a = dct_a.get('id'), dct_a.get('attributes', {})
        for dct_b in records[i + 1:]:
            id_b, attrs_b = dct_b.get('id'), dct_b.get('attributes', {})
            if _soft_match(attrs_a, attrs_b):
                parent[_find(parent, id_a)] = _find(parent, id_b)

    children = defaultdict(list)
    for r in records:
        children[_find(parent, r.get("id"))].append(r.get("id"))

    rows = []
    for parent_id, child_id_list in children.items():
        id_list = sorted(list(set([parent_id] + child_id_list)))
        rows.append({
            'id': str(uuid.uuid4()),
            'auth_devices_ids': json.dumps(id_list),
            'initial_soft_merge': 1 if len(id_list) > 1 else 0,
        })

    return rows
