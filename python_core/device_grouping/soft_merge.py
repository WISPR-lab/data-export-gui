#  SOFT MERGE
#  Merge atomics on manufacturer + model match, using pre-calculated specificity levels.
#  Model/manufacturer sourced from device_* or user_agent_device_* fields.
# 
#  Rules: (note spec = specificity)
#  - Both spec >= 2  →  exact model match required
#  - Mixed (one spec < 2) with Apple  →  no merge (UA masking)
#  - Mixed (one spec < 2) non-Apple  →  merge allowed
#  - Both spec < 2 with Apple  →  no merge (UA masking)
#  - Both spec < 2 non-Apple  →  merge allowed

import uuid
import json
from device_grouping.shared_utils import union_find
from device_grouping.computed_fields import best_model_attr, get_mfr, MFR_DO_NOT_MERGE_GENERIC, compute_device_profile_fields, merge_attrs



def _soft_match(attrs_a: dict, attrs_b: dict, spec_a: int, spec_b: int) -> bool:
    # Check if two atomics can be soft-merged based on model/mfr and specificity
    model_a = best_model_attr(attrs_a)
    model_b = best_model_attr(attrs_b)
    mfr_a = get_mfr(attrs_a)
    mfr_b = get_mfr(attrs_b)
    
    # missing fields, can't match
    if not model_a or not model_b or not mfr_a or not mfr_b:
        return False
    
    # different manufacturers, can't match
    if mfr_a != mfr_b:
        return False
    
    # both specific, exact model match required
    if spec_a >= 2 and spec_b >= 2:
        return model_a == model_b
    
    # at least one generic, Apple - no merge, others - merge
    if mfr_a in MFR_DO_NOT_MERGE_GENERIC or mfr_b in MFR_DO_NOT_MERGE_GENERIC:
        return False
    
    return True


def soft_merge_single_upload(records: list[dict]) -> list[dict]:
    # group atomics into profiles via soft-match union-find
    def match(a: dict, b: dict) -> bool:
        return _soft_match(
            a.get('attributes', {}), b.get('attributes', {}),
            a.get('specificity', 1), b.get('specificity', 1)
        )
    
    children = union_find(records, match)
    rows = []
    
    for parent_id, child_id_list in children.items():
        id_list = list(set([parent_id] + child_id_list))
        profile_row = {
            'id': str(uuid.uuid4()),
            'atomic_devices_ids': id_list,
            'system_soft_merge': 1 if len(id_list) > 1 else 0
        }
        computed = compute_device_profile_fields(profile_row, records)
        profile_row.update(computed)
        rows.append(profile_row)
    
    return rows


def soft_merge_multi_upload(new_atomic_device_rows: list[dict], 
                            old_device_profile_rows: list[dict], 
                            atomic_devices_rows: list[dict]) -> list[dict]:
    """Soft merge new atomics into existing profiles. Returns rows with computed fields."""
    atomic_device_dict = {r['id']: r for r in atomic_devices_rows}
    profiles_to_update = {}  # profile_id -> [atomic_ids_to_add]
    new_device_profile_rows = []
    
    for new_row in new_atomic_device_rows:
        matching_profile_ids = []
        for pf in old_device_profile_rows:
            for atomic_id in pf.get('atomic_devices_ids', []):
                existing_atomic = atomic_device_dict.get(atomic_id, {})
                if _soft_match(
                    new_row.get('attributes', {}), 
                    existing_atomic.get('attributes', {}),
                    new_row.get('specificity', 1), 
                    existing_atomic.get('specificity', 1)
                ):
                    matching_profile_ids.append(pf['id'])
                    break
        
        if len(matching_profile_ids) == 1:
            profile_id = matching_profile_ids[0]
            if profile_id not in profiles_to_update:
                profiles_to_update[profile_id] = []
            profiles_to_update[profile_id].append(new_row['id'])
        else:
            new_device_profile_rows.append({
                'id': str(uuid.uuid4()),
                'atomic_devices_ids': [new_row['id']],
                'system_soft_merge': 0,
            })
    
    final_rows = []
    for pf in old_device_profile_rows:
        if pf['id'] in profiles_to_update:
            merged_ids = list(set(pf.get('atomic_devices_ids', []) + profiles_to_update[pf['id']]))
            row = {**pf, 'atomic_devices_ids': merged_ids}
            row.update(compute_device_profile_fields(row, atomic_devices_rows))
            final_rows.append(row)
        else:
            final_rows.append(pf)
    
    for nf in new_device_profile_rows:
        nf.update(compute_device_profile_fields(nf, atomic_devices_rows))
    final_rows.extend(new_device_profile_rows)
    
    return final_rows




def format_rows(rows: list[dict]) -> list[dict]:
    formatted = []
    for row in rows:
        formatted.append({
            'id': row['id'],
            'atomic_devices_ids': json.dumps(row['atomic_devices_ids']),
            'attributes': json.dumps(row['attributes']),
            'specificity': row['specificity'],
            'model': row['model'],
            'manufacturer': row['manufacturer'],
            'origins': json.dumps(row['origins']),
            'system_soft_merge': row.get('system_soft_merge', 0),
            'is_generic': row['is_generic'],
            'user_label': None,
            'notes': None,
            'tags': json.dumps([]),
            'labels': json.dumps([]),
        })
    return formatted
