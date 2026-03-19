#  SOFT MERGE
#  Merge devices on manufacturer + model match, using pre-calculated specificity levels.
#  Model/manufacturer sourced from device_* or user_agent_device_* fields.
#  Rules: 
#  -  both specificity >= 2  -->  exact match
#  -  generic + specific  -->   no merge if either is Apple, else merge
#  -  generic + generic   -->  no merge if either is Apple, else merge

import re
from collections import defaultdict
import uuid
import json


MFR_DO_NOT_MERGE_GENERIC = {'apple'}


def _get_model_or_mfr(values: list[str]) -> str:
    # get first non-empty value from candidates
    candidates = [v.strip() for v in values if v and v.strip()]
    return candidates[0] if candidates else ''


def _soft_match(attrs_a: dict, attrs_b: dict, spec_a: int, spec_b: int) -> bool:
    model_a = _get_model_or_mfr([
        attrs_a.get('device_model_name', ''),
        attrs_a.get('user_agent_device_model', ''),
    ])
    model_b = _get_model_or_mfr([
        attrs_b.get('device_model_name', ''),
        attrs_b.get('user_agent_device_model', ''),
    ])
    
    mfr_a = _get_model_or_mfr([
        attrs_a.get('device_manufacturer', ''),
        attrs_a.get('user_agent_device_manufacturer', ''),
    ])
    mfr_b = _get_model_or_mfr([
        attrs_b.get('device_manufacturer', ''),
        attrs_b.get('user_agent_device_manufacturer', ''),
    ])
    
    if not model_a or not model_b or not mfr_a or not mfr_b:
        return False
    
    if mfr_a.lower() != mfr_b.lower():
        return False
    
    if spec_a >= 2 and spec_b >= 2:
        return model_a.lower() == model_b.lower()
    
    if mfr_a.lower() in MFR_DO_NOT_MERGE_GENERIC or mfr_b.lower() in MFR_DO_NOT_MERGE_GENERIC:
        return False
    
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
        spec_a = dct_a.get('specificity', 1)
        for dct_b in records[i + 1:]:
            id_b, attrs_b = dct_b.get('id'), dct_b.get('attributes', {})
            spec_b = dct_b.get('specificity', 1)
            if _soft_match(attrs_a, attrs_b, spec_a, spec_b):
                parent[_find(parent, id_a)] = _find(parent, id_b)

    children = defaultdict(list)
    for r in records:
        children[_find(parent, r.get("id"))].append(r.get("id"))

    rows = []
    for parent_id, child_id_list in children.items():
        id_list = sorted(list(set([parent_id] + child_id_list)))
        rows.append({
            'id': str(uuid.uuid4()),
            'atomic_devices_ids': json.dumps(id_list),
            'initial_soft_merge': 1 if len(id_list) > 1 else 0,
        })

    return rows
