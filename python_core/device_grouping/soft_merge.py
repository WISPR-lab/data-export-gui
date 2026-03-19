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


MFR_DO_NOT_MERGE_GENERIC = {'apple'}


def _extract_model(attrs: dict) -> str:
    # extract model name from device or UA fields, return first non-empty
    for key in ['device_model_name', 'user_agent_device_model']:
        val = attrs.get(key, '').strip()
        if val:
            return val
    return ''


def _extract_manufacturer(attrs: dict) -> str:
    # extract manufacturer from device or UA fields, return first non-empty field
    for key in ['device_manufacturer', 'user_agent_device_manufacturer']:
        val = attrs.get(key, '').strip()
        if val:
            return val
    return ''


def _compute_is_generic(atomic_record: dict) -> int:
    attrs = atomic_record.get('attributes', {})
    mfr = attrs.get('device_manufacturer', '').lower()
    return 1 if (atomic_record.get('specificity', 1) < 2 and mfr in {'apple'}) else 0


def _soft_match(attrs_a: dict, attrs_b: dict, spec_a: int, spec_b: int) -> bool:
    # Check if two atomics can be soft-merged based on model/mfr and specificity
    model_a = _extract_model(attrs_a)
    model_b = _extract_model(attrs_b)
    mfr_a = _extract_manufacturer(attrs_a)
    mfr_b = _extract_manufacturer(attrs_b)
    
    # missing fields, can't match
    if not model_a or not model_b or not mfr_a or not mfr_b:
        return False
    
    # different manufacturers,  can't match
    if mfr_a.lower() != mfr_b.lower():
        return False
    
    # both specific,  exact model match required
    if spec_a >= 2 and spec_b >= 2:
        return model_a.lower() == model_b.lower()
    
    # at least one generic,  Apple - no merge, others - merge
    if mfr_a.lower() in MFR_DO_NOT_MERGE_GENERIC or mfr_b.lower() in MFR_DO_NOT_MERGE_GENERIC:
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
        id_list = sorted(list(set([parent_id] + child_id_list)))
        first_atomic = next((r for r in records if r['id'] == parent_id), None)
        
        
        rows.append({
            'id': str(uuid.uuid4()),
            'atomic_devices_ids': id_list,
            'system_soft_merge': 1 if len(id_list) > 1 else 0,
            'is_generic': _compute_is_generic(first_atomic) if first_atomic else 0,
        })
    
    return rows


def soft_merge_multi_upload_increment(new_atomics: list[dict], existing_profiles: list[dict], all_atomics: dict) -> list[dict]:
    # For each new atomic, find soft-match candidates in existing profiles
    # If exactly 1 match: add to that profile (system-matched soft-merge)
    # If 0 matches: create new profile
    # If >1 matches: create new profile (user will disambiguate via UI)
    
    profiles_to_update = {}  # profile_id -> new atomic_ids to add
    new_profiles = []
    
    for new_atomic in new_atomics:
        matching_profile_ids = []
        for profile in existing_profiles:
            for atomic_id in profile.get('atomic_devices_ids', []):
                existing_atomic = all_atomics.get(atomic_id, {})
                if _soft_match(
                    new_atomic.get('attributes', {}), 
                    existing_atomic.get('attributes', {}),
                    new_atomic.get('specificity', 1), 
                    existing_atomic.get('specificity', 1)
                ):
                    matching_profile_ids.append(profile['id'])
                    break
        
        if len(matching_profile_ids) == 1:
            # System-matched: add to this profile
            profile_id = matching_profile_ids[0]
            if profile_id not in profiles_to_update:
                profiles_to_update[profile_id] = []
            profiles_to_update[profile_id].append(new_atomic['id'])
        
        elif len(matching_profile_ids) == 0:
            # No match: create new single-atomic profile
            is_generic = _compute_is_generic(new_atomic)
            new_profiles.append({
                'id': str(uuid.uuid4()),
                'atomic_devices_ids': [new_atomic['id']],
                'system_soft_merge': 0,  # Created as single-atomic
                'is_generic': is_generic,
            })
        
        else:
            # >1 matches: create new single-atomic profile, user will merge manually
            is_generic = _compute_is_generic(new_atomic)
            new_profiles.append({
                'id': str(uuid.uuid4()),
                'atomic_devices_ids': [new_atomic['id']],
                'system_soft_merge': 0,
                'is_generic': is_generic,
            })
    
    return {
        'profiles_to_update': profiles_to_update,  # {profile_id: [new_atomic_ids]}
        'new_profiles': new_profiles
    }


def format_rows(rows: list[dict]) -> list[dict]:
    formatted = []
    for row in rows:
        formatted.append({
            'id': row['id'],
            'atomic_devices_ids': json.dumps(row['atomic_devices_ids']),
            'system_soft_merge': row.get('system_soft_merge', 0),
            'is_generic': row.get('is_generic', 0),
            'user_label': None,
            'notes': None,
            'tags': json.dumps([]),
            'labels': json.dumps([]),
        })
    return formatted
