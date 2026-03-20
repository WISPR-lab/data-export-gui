import json
import builtins
from device_grouping.computed_fields import compute_device_profile_fields
from db_session import DatabaseSession


def _get_config_value(name):
    if not hasattr(builtins, name):
        raise ValueError(f"Config value '{name}' not found in builtins.")
    return getattr(builtins, name)


def merge_device_profiles(src_profile_id: str, tgt_profile_id: str) -> dict:
    db_path = _get_config_value('DB_PATH')
    json_cols = {'attributes', 'origins', 'tags', 'labels', 'atomic_devices_ids'}
    
    with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
        try:
            src_profile = conn.execute(
                'SELECT * FROM device_profiles WHERE id = ?', (src_profile_id,)
            ).fetchone()
            tgt_profile = conn.execute(
                'SELECT * FROM device_profiles WHERE id = ?', (tgt_profile_id,)
            ).fetchone()
            
            if not src_profile:
                return {'status': 'error', 'message': f'Source profile {src_profile_id} not found'}
            if not tgt_profile:
                return {'status': 'error', 'message': f'Target profile {tgt_profile_id} not found'}
            
            all_atomics = conn.execute('SELECT * FROM atomic_devices').fetchall()
            atomic_dict = {a['id']: a for a in all_atomics}
            
            src_spec = src_profile.get('specificity', 1)
            tgt_spec = tgt_profile.get('specificity', 1)
            src_is_generic = src_profile.get('is_generic', 0)
            tgt_is_generic = tgt_profile.get('is_generic', 0)
            
            if src_spec >= 3 and tgt_spec >= 3:
                return {'status': 'ineligible', 'message': 'Cannot merge two profiles with incompatible deterministic identifiers (i.e., serial numbers)'}
            
            if src_is_generic and tgt_is_generic:
                return {'status': 'ineligible', 'message': 'Cannot merge two generic profiles (i.e., two iphones with no other details))'}
            
            src_atomics = src_profile.get('atomic_devices_ids', [])
            tgt_atomics = tgt_profile.get('atomic_devices_ids', [])
            merged_atomics = list(set(src_atomics + tgt_atomics))
            
            merged_profile = {
                'id': tgt_profile_id,
                'atomic_devices_ids': merged_atomics,
            }
            
            atomics_for_merge = [a for a in all_atomics if a['id'] in merged_atomics]
            computed = compute_device_profile_fields(merged_profile, atomics_for_merge)
            merged_profile.update(computed)
            
            merged_profile['created_at'] = tgt_profile.get('created_at')
            merged_profile['updated_at'] = tgt_profile.get('updated_at')
            merged_profile['user_label'] = tgt_profile.get('user_label')
            merged_profile['notes'] = tgt_profile.get('notes')
            merged_profile['tags'] = tgt_profile.get('tags', '[]')
            merged_profile['labels'] = tgt_profile.get('labels', '[]')
            merged_profile['system_soft_merge'] = tgt_profile.get('system_soft_merge', 0)
            
            conn.execute(
                '''UPDATE device_profiles 
                   SET atomic_devices_ids = ?, attributes = ?, specificity = ?, 
                       model = ?, manufacturer = ?, origins = ?, is_generic = ?
                   WHERE id = ?''',
                (
                    json.dumps(merged_profile['atomic_devices_ids']),
                    json.dumps(merged_profile['attributes']),
                    merged_profile['specificity'],
                    merged_profile['model'],
                    merged_profile['manufacturer'],
                    json.dumps(merged_profile['origins']),
                    merged_profile['is_generic'],
                    tgt_profile_id
                )
            )
            
            conn.execute('DELETE FROM device_profiles WHERE id = ?', (src_profile_id,))
            conn.commit()
            
            return {
                'status': 'ok',
                'message': f'Merged {src_profile_id} into {tgt_profile_id}',
                'merged_profile_id': tgt_profile_id
            }
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
