import pytest
import json
import uuid
import builtins
from db_session import DatabaseSession
from semantic_map.worker import map as semantic_map
from field_normalization.worker import normalize
from device_grouping.worker import group


class TestE2EPipeline:
    """Full end-to-end integration test: extraction → semantic_map → normalize → group."""

    def test_full_pipeline_facebook_data(self, sample_upload_with_raw_data, test_db_path):
        """Execute the complete pipeline on real facebook.zip data."""
        upload_id, raw_data_count = sample_upload_with_raw_data
        
        assert raw_data_count > 0, "Sample data should have loaded raw_data"
        assert raw_data_count == 118, f"Expected 118 raw_data records, got {raw_data_count}"
        
        # STAGE 1: semantic_map
        semantic_map(
            platform='facebook',
            upload_id=upload_id,
            db_path=test_db_path,
            manifest_dir=builtins.MANIFESTS_DIR
        )
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            devices_raw_count = conn.execute(
                'SELECT COUNT(*) as count FROM devices_raw WHERE upload_id = ?',
                (upload_id,)
            ).fetchone()['count']
            
            # Verify we have different event types in the extracted data
            event_actions = conn.execute(
                'SELECT DISTINCT event_action FROM events WHERE upload_id = ?',
                (upload_id,)
            ).fetchall()
            event_actions = [e['event_action'] for e in event_actions if e['event_action']]
        
        assert devices_raw_count > 0, \
            f"semantic_map should create devices_raw rows, got {devices_raw_count}"
        
        # Verify we extracted multiple event action types from the data
        assert len(event_actions) >= 2, \
            f"Should have at least 2 different event_action types, got {len(event_actions)}: {event_actions}"
        
        # STAGE 2: field_normalization
        norm_result = normalize(upload_id, db_path=test_db_path)
        
        assert norm_result['status'] == 'success'
        assert norm_result['records_normalized'] == devices_raw_count
        
        # STAGE 3: device_grouping
        group(upload_id, db_path=test_db_path)
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            atomic_devices_count = conn.execute(
                'SELECT COUNT(*) as count FROM atomic_devices WHERE EXISTS '
                '(SELECT 1 FROM devices_raw WHERE upload_id = ? AND 1=1)',
                (upload_id,)
            ).fetchone()['count']
            
            # device_profiles_count = conn.execute(
            #     'SELECT COUNT(*) as count FROM device_profiles'
            # ).fetchone()['count']
            device_profiles_all = conn.execute(
                'SELECT * FROM v_device_profiles'
            ).fetchall()

            device_profiles_all = [{k: json.loads(v) if k in ('attributes', 'origins', 'specificity') and isinstance(v, str) else v for k, v in p.items()} for p in device_profiles_all]
            device_profiles_count = len(device_profiles_all)

        
        assert atomic_devices_count >= 1, \
            f"Hard merge should create at least 1 atomic device, got {atomic_devices_count}"
        # Device profiles should exist and be reasonable in count
        assert device_profiles_count >= 1, \
            f"Soft merge should create at least 1 device_group, got {device_profiles_count}"
        assert device_profiles_count == 4, \
            f"Device profiles should be 4 for the facebook test data, got {device_profiles_count}."
        
        print(f"\n[E2E Test] Device Profiles ({device_profiles_count}):")
        print(json.dumps(device_profiles_all, indent=2))
