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
DEBUG = False

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
    
    if DEBUG: print(f"[SoftMerge] soft_merge_multi_upload: new_atomic_device_rows={len(new_atomic_device_rows)}, existing profiles={len(old_device_profile_rows)}")
    
    new_profiles = soft_merge_single_upload(new_atomic_device_rows) # group new atomics in themselves
    if DEBUG: print(f"[SoftMerge] Created {len(new_profiles)} new profiles from new atomics")
    
    atomic_device_dict = {r['id']: r for r in atomic_devices_rows}  # then match atomics to existing profiles
    profiles_to_update = {}  # profile_id -> [atomic_ids_to_add]
    new_device_profile_rows = []
    
    for new_pf in new_profiles:
        # new_pf: dict with 'id', 'atomic_devices_ids', 'system_soft_merge' (and computed fields)
        matching_profile_ids = []
        
        if DEBUG: print(f"[SoftMerge] Processing new profile {new_pf['id'][:8]}... with atomics: {new_pf.get('atomic_devices_ids', [])}")

        for new_atomic_id in new_pf.get('atomic_devices_ids', []):
            new_atomic = atomic_device_dict.get(new_atomic_id, {})
            if DEBUG: print(f"[SoftMerge]   Checking new atomic {new_atomic_id[:8]}...")
            # check if any atomic in the new profile matches an existing profile
            for old_pf in old_device_profile_rows:
                for old_atomic_id in old_pf.get('atomic_devices_ids', []):
                    existing_atomic = atomic_device_dict.get(old_atomic_id, {})
                    if soft_match(new_atomic, existing_atomic):
                        if DEBUG: print(f"[SoftMerge]     MATCH FOUND: new atomic {new_atomic_id[:8]}... matches existing atomic {old_atomic_id[:8]}... in profile {old_pf['id'][:8]}...")
                        matching_profile_ids.append(old_pf['id'])
                        break

            if matching_profile_ids: 
                if DEBUG: print(f"[SoftMerge]   Found match, exiting atomic check loop")
                break

        if len(matching_profile_ids) > 1:
            #  TODO: if more than one profile matches
            print(f"Warning: Multiple matching profiles found for new profile {new_pf['id']}. Matching profiles: {matching_profile_ids}. This case is not currently handled and may lead to duplicates.")
        
        if len(matching_profile_ids) > 0:
            old_pf_id = matching_profile_ids[0]
            new_atomic_ids_list = new_pf.get('atomic_devices_ids', [])
            if DEBUG: print(f"[SoftMerge] ADDING to profiles_to_update: profile {old_pf_id[:8]}... gets atomics {new_atomic_ids_list}")
            if old_pf_id not in profiles_to_update:
                profiles_to_update[old_pf_id] = []
            profiles_to_update[old_pf_id].extend(new_atomic_ids_list)
            if DEBUG: print(f"[SoftMerge]   profiles_to_update[{old_pf_id[:8]}...] is now: {profiles_to_update[old_pf_id]}")
        else:
            if DEBUG: print(f"[SoftMerge] No match found, adding as new profile: {new_pf['id'][:8]}...")
            new_device_profile_rows.append(new_pf)

    
    final_rows = []
    if DEBUG: 
        print(f"[SoftMerge] ===== FINAL MERGE PHASE =====")
        print(f"[SoftMerge] profiles_to_update contains {len(profiles_to_update)} profiles:")
        for pf_id, atomic_ids in profiles_to_update.items():
            print(f"[SoftMerge]   {pf_id[:8]}... -> {atomic_ids}")
        print(f"[SoftMerge] old_device_profile_rows has {len(old_device_profile_rows)} profiles")
    
    for old_pf in old_device_profile_rows:
        if DEBUG: print(f"[SoftMerge] Checking old profile {old_pf['id'][:8]}...")
        if old_pf['id'] in profiles_to_update:
            if DEBUG: print(f"[SoftMerge]   FOUND in profiles_to_update")
            old_ids = old_pf.get('atomic_devices_ids', [])
            # Safety: dict_factory might deserialize empty JSON as {}
            if isinstance(old_ids, dict):
                old_ids = []
            new_ids_to_add = profiles_to_update[old_pf['id']]
            merged_ids = list(set(old_ids + new_ids_to_add))
            if DEBUG: 
                print(f"[SoftMerge]   Old atomics: {old_ids}")
                print(f"[SoftMerge]   New atomics to add: {new_ids_to_add}")
                print(f"[SoftMerge]   Merged atomics: {merged_ids}")
            
            # Build fresh row with only essential fields to avoid stale cached data
            row = {
                'id': old_pf['id'],
                'atomic_devices_ids': merged_ids,
                'system_soft_merge': 1 if len(merged_ids) > 1 else old_pf.get('system_soft_merge', 0),
                'user_label': old_pf.get('user_label'),
                'notes': old_pf.get('notes'),
            }
            if DEBUG: print(f"[SoftMerge]   Built row with atomic_devices_ids: {row['atomic_devices_ids']}")
            
            computed = compute_device_profile_fields(row, atomic_devices_rows)
            if DEBUG: print(f"[SoftMerge]   Computed: origins={computed.get('origins')}, specificity={computed.get('specificity')}")
            row.update(computed)
            if DEBUG: print(f"[SoftMerge]   AFTER update: atomic_devices_ids={row.get('atomic_devices_ids')}, origins={row.get('origins')}")
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
            if DEBUG: print(f"[SoftMerge]   NOT in profiles_to_update, keeping original")
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
    
    if DEBUG: print(f"[SoftMerge] soft_merge_multi_upload returning {len(final_rows)} profiles")
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
