from device_grouping.computed_fields import specificity, best_model_attr, get_mfr
from device_grouping.hard_merge import hard_match
from device_grouping.soft_merge import _soft_match
from utils.redaction_utils import compare_redacted_vals


def associate_events_to_devices(events_rows: list[dict], 
                                atomic_devices_rows: list[dict]) -> list[dict]:
    associations = []
    
    for event in events_rows:
        event_attrs = event.get('attributes', {})
        event_upload_id = event.get('upload_id')
        event_id = event.get('id')
        
        event_specificity = specificity(event_attrs)
        
        for atomic_device in atomic_devices_rows:
            atomic_device_attrs = atomic_device.get('attributes', {})
            atomic_device_upload_ids = atomic_device.get('upload_ids', [])
            atomic_device_id = atomic_device.get('id')
            atomic_device_specificity = atomic_device.get('specificity', 1)
            
            if event_upload_id not in atomic_device_upload_ids:
                continue
            
            match_reason = None
            
            if hard_match(event_attrs, atomic_device_attrs):
                match_reason = 'hard_id_match'
            
            if not match_reason:
                event_ua_original = event_attrs.get('user_agent_original', '').strip()
                atomic_device_ua_original = atomic_device_attrs.get('user_agent_original', '').strip()
                if event_ua_original and atomic_device_ua_original and event_ua_original == atomic_device_ua_original:
                    match_reason = 'user_agent_original_exact'
            
            if not match_reason:
                if _soft_match(event_attrs, atomic_device_attrs, event_specificity, atomic_device_specificity):
                    match_reason = 'user_agent_parsed_model_mfr'
            
            if match_reason:
                associations.append({
                    'event_id': event_id,
                    'atomic_device_id': atomic_device_id,
                    'match_reason': match_reason,
                    'event_specificity': event_specificity,
                })
    
    return associations
