#  SOFT MERGE
#  Merge devices on manufacturer + model match, using pre-calculated specificity levels.
#  Model/manufacturer sourced from device_* or user_agent_device_* fields.
#  Rules: 
#  -  both specificity >= 2  -->  exact match
#  -  generic + specific  -->   no merge if either is Apple, else merge
#  -  generic + generic   -->  no merge if either is Apple, else merge

import uuid
import json
from device_grouping.shared_utils import union_find


MFR_DO_NOT_MERGE_GENERIC = {'apple'}


def _first_value(values: list[str]) -> str:
    candidates = [v.strip() for v in values if v and v.strip()]
    return candidates[0] if candidates else ''


def _soft_match(attrs_a: dict, attrs_b: dict, spec_a: int, spec_b: int) -> bool:
    model_a = _first_value([
        attrs_a.get('device_model_name', ''),
        attrs_a.get('user_agent_device_model', ''),
    ])
    model_b = _first_value([
        attrs_b.get('device_model_name', ''),
        attrs_b.get('user_agent_device_model', ''),
    ])
    
    mfr_a = _first_value([
        attrs_a.get('device_manufacturer', ''),
        attrs_a.get('user_agent_device_manufacturer', ''),
    ])
    mfr_b = _first_value([
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


def soft_merge(records: list[dict]) -> list[dict]:
    def match(a: dict, b: dict) -> bool:
        return _soft_match(
            a.get('attributes', {}), b.get('attributes', {}),
            a.get('specificity', 1), b.get('specificity', 1)
        )
    
    children = union_find(records, match)

    rows = []
    for parent_id, child_id_list in children.items():
        id_list = sorted(list(set([parent_id] + child_id_list)))
        rows.append({
            'id': str(uuid.uuid4()),
            'atomic_devices_ids': json.dumps(id_list),
            'initial_soft_merge': 1 if len(id_list) > 1 else 0,
        })

    return rows
