import uuid
import json
import builtins
from device_grouping.computed_fields import compute_device_profile_fields
from db_session import DatabaseSession


def _get_config_value(name):
    if not hasattr(builtins, name):
        raise ValueError(f"Config value '{name}' not found in builtins.")
    return getattr(builtins, name)


def unmerge_device_profiles(profile_id: str, atomic_id: str) -> dict:
    db_path = _get_config_value('DB_PATH')
    json_cols = {'attributes', 'origins', 'tags', 'labels', 'atomic_devices_ids'}
    
    with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
        # Extract an atomic from a profile into a new singleton profile.
        # Returns: {'status': 'ok'|'error', 'message': str, 'new_profile_id': str, 'updated_profile_id': str}
        try:
            profile = conn.execute(
                'SELECT * FROM device_profiles WHERE id = ?', (profile_id,)
            ).fetchone()
            
            if not profile:
                return {'status': 'error', 'message': f'Profile {profile_id} not found'}
            
            all_atomics = conn.execute('SELECT * FROM atomic_devices').fetchall()
            atomic_dict = {a['id']: a for a in all_atomics}
            
            profile_atomics = profile.get('atomic_devices_ids', [])
            
            if len(profile_atomics) < 2:
                return {'status': 'ineligible', 'message': 'Cannot unmerge: profile has only 1 atomic'}
            
            if atomic_id not in profile_atomics:
                return {'status': 'error', 'message': f'Atomic {atomic_id} not in profile {profile_id}'}
            
            spec = profile.get('specificity', 1)
            if spec >= 3:
                return {'status': 'ineligible', 'message': 'Cannot unmerge hard-merged profiles'}
            
            new_profile_id = str(uuid.uuid4())
            new_profile = {
                'id': new_profile_id,
                'atomic_devices_ids': [atomic_id],
                'system_soft_merge': 0,
            }
            
            # Compute fields for new profile
            new_atomics = [a for a in all_atomics if a['id'] == atomic_id]
            new_computed = compute_device_profile_fields(new_profile, new_atomics)
            new_profile.update(new_computed)
            new_profile['created_at'] = profile.get('created_at')
            new_profile['updated_at'] = profile.get('updated_at')
            new_profile['user_label'] = None
            new_profile['notes'] = None
            new_profile['tags'] = '[]'
            new_profile['labels'] = '[]'
            
            remaining_atomics = [a for a in profile_atomics if a != atomic_id]
            updated_profile = {
                'id': profile_id,
                'atomic_devices_ids': remaining_atomics,
            }
            
            updated_atomics = [a for a in all_atomics if a['id'] in remaining_atomics]
            updated_computed = compute_device_profile_fields(updated_profile, updated_atomics)
            updated_profile.update(updated_computed)
            
            updated_profile['created_at'] = profile.get('created_at')
            updated_profile['updated_at'] = profile.get('updated_at')
            updated_profile['user_label'] = profile.get('user_label')
            updated_profile['notes'] = profile.get('notes')
            updated_profile['tags'] = profile.get('tags', '[]')
            updated_profile['labels'] = profile.get('labels', '[]')
            updated_profile['system_soft_merge'] = profile.get('system_soft_merge', 0)
            
            conn.execute(
                '''INSERT INTO device_profiles
                   (id, atomic_devices_ids, attributes, specificity, model, manufacturer, 
                    origins, system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    new_profile['id'],
                    json.dumps(new_profile['atomic_devices_ids']),
                    json.dumps(new_profile['attributes']),
                    new_profile['specificity'],
                    new_profile['model'],
                    new_profile['manufacturer'],
                    json.dumps(new_profile['origins']),
                    new_profile['system_soft_merge'],
                    new_profile['is_generic'],
                    new_profile['user_label'],
                    new_profile['notes'],
                    new_profile['tags'],
                    new_profile['labels'],
                    new_profile['created_at'],
                    new_profile['updated_at'],
                )
            )
            
            conn.execute(
                '''UPDATE device_profiles 
                   SET atomic_devices_ids = ?, attributes = ?, specificity = ?, 
                       model = ?, manufacturer = ?, origins = ?, is_generic = ?
                   WHERE id = ?''',
                (
                    json.dumps(updated_profile['atomic_devices_ids']),
                    json.dumps(updated_profile['attributes']),
                    updated_profile['specificity'],
                    updated_profile['model'],
                    updated_profile['manufacturer'],
                    json.dumps(updated_profile['origins']),
                    updated_profile['is_generic'],
                    profile_id
                )
            )
            
            conn.commit()
            
            # Verify unmerge actually happened
            new_check = conn.execute('SELECT * FROM device_profiles WHERE id = ?', (new_profile_id,)).fetchone()
            if not new_check:
                return {'status': 'error', 'message': f'Unmerge failed: new profile {new_profile_id} not found after insert'}
            
            updated_check = conn.execute('SELECT * FROM device_profiles WHERE id = ?', (profile_id,)).fetchone()
            if not updated_check:
                return {'status': 'error', 'message': f'Unmerge failed: updated profile {profile_id} not found after update'}
            
            if atomic_id in updated_check.get('atomic_devices_ids', []):
                return {'status': 'error', 'message': f'Unmerge failed: atomic {atomic_id} still in profile {profile_id}'}
            
            return {
                'status': 'ok',
                'message': f'Extracted {atomic_id} from {profile_id}',
                'new_profile_id': new_profile_id,
                'updated_profile_id': profile_id
            }
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
