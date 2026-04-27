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
from device_grouping.computed_fields import best_model_attr, get_mfr, MFR_DO_NOT_MERGE_GENERIC, compute_device_profile_fields
from utils.merge_history import log_merge_event


def soft_match(a: dict, b: dict) -> bool:  
# check if two atomics match for soft merge based on rules above
    attrs_a = a.get('attributes', {})
    attrs_b = b.get('attributes', {})
    spec_a = a.get('specificity', 1)
    spec_b = b.get('specificity', 1)
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
    children = union_find(records, soft_match)
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
        
        if len(id_list) > 1:
            log_merge_event(
                profile_id=profile_row['id'],
                action='merge',
                atomic_ids=id_list,
                user_initiated=False,
                system_reason='soft_match' # TODO better reason
            )
    
    return rows


def soft_merge_multi_upload(new_atomic_device_rows: list[dict], 
                            old_device_profile_rows: list[dict], 
                            atomic_devices_rows: list[dict]) -> list[dict]:
    """Soft merge new atomics into existing profiles. Returns rows with computed fields."""
    
    new_profiles = soft_merge_single_upload(new_atomic_device_rows) # group new atomics in themselves
    
    atomic_device_dict = {r['id']: r for r in atomic_devices_rows}  # then match atomics to existing profiles
    profiles_to_update = {}  # profile_id -> [atomic_ids_to_add]
    new_device_profile_rows = []
    
    for new_pf in new_profiles:
        # new_pf: dict with 'id', 'atomic_devices_ids', 'system_soft_merge' (and computed fields)
        matching_profile_ids = []

        for new_atomic_id in new_pf.get('atomic_devices_ids', []):
            new_atomic = atomic_device_dict.get(new_atomic_id, {})
            # check if any atomic in the new profile matches an existing profile
            for old_pf in old_device_profile_rows:
                for old_atomic_id in old_pf.get('atomic_devices_ids', []):
                    existing_atomic = atomic_device_dict.get(old_atomic_id, {})
                    if soft_match(new_atomic, existing_atomic):
                        matching_profile_ids.append(old_pf['id'])
                        break

            if matching_profile_ids: break  # match found
        if matching_profile_ids: break

        if len(matching_profile_ids) > 1:
            #  TODO: if more than one profile matches
            print(f"Warning: Multiple matching profiles found for new profile {new_pf['id']}. Matching profiles: {matching_profile_ids}. This case is not currently handled and may lead to duplicates.")
        
        if len(matching_profile_ids) > 0:
            old_pf_id = matching_profile_ids[0]
            if old_pf_id not in profiles_to_update:
                profiles_to_update[old_pf_id] = []
            profiles_to_update[old_pf_id].append(new_pf.get('atomic_devices_ids', []))
        else:
            new_device_profile_rows.append(new_pf)

    
    final_rows = []
    for old_pf in old_device_profile_rows:
        if old_pf['id'] in profiles_to_update:
            merged_ids = list(set(old_pf.get('atomic_devices_ids', []) + profiles_to_update[old_pf['id']]))
            row = {**old_pf, 'atomic_devices_ids': merged_ids}
            row.update(compute_device_profile_fields(row, atomic_devices_rows))
            final_rows.append(row)
            
            new_atomics_added = [a for group in profiles_to_update[old_pf['id']] for a in group]
            if new_atomics_added:
                log_merge_event(
                    profile_id=old_pf['id'],
                    action='merge',
                    atomic_ids=new_atomics_added,
                    user_initiated=False,
                    system_reason='soft_match' # TODO better reason
                )
        else:
            final_rows.append(old_pf)
    
    for nf in new_device_profile_rows:
        nf.update(compute_device_profile_fields(nf, atomic_devices_rows))
        
        if len(nf.get('atomic_devices_ids', [])) > 1:
            log_merge_event(
                profile_id=nf['id'],
                action='merge',
                atomic_ids=nf.get('atomic_devices_ids', []),
                user_initiated=False,
                system_reason='soft_match' # TODO better reason
            )
    
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
            'user_label': row.get('user_label'),
            'notes': row.get('notes'),
            'tags': json.dumps([]),
            'labels': json.dumps([]),
        })
    return formatted
