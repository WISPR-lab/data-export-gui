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
            auth_devices_initial_count = conn.execute(
                'SELECT COUNT(*) as count FROM auth_devices_initial WHERE upload_id = ?',
                (upload_id,)
            ).fetchone()['count']
            
            # Verify we have different event types in the extracted data
            event_actions = conn.execute(
                'SELECT DISTINCT event_action FROM events WHERE upload_id = ?',
                (upload_id,)
            ).fetchall()
            event_actions = [e['event_action'] for e in event_actions if e['event_action']]
        
        assert auth_devices_initial_count > 0, \
            f"semantic_map should create auth_devices_initial rows, got {auth_devices_initial_count}"
        
        # Verify we extracted multiple event action types from the data
        assert len(event_actions) >= 2, \
            f"Should have at least 2 different event_action types, got {len(event_actions)}: {event_actions}"
        
        # STAGE 2: field_normalization
        norm_result = normalize(upload_id, db_path=test_db_path)
        
        assert norm_result['status'] == 'success'
        assert norm_result['records_normalized'] == auth_devices_initial_count
        
        # STAGE 3: device_grouping
        group(upload_id, db_path=test_db_path)
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            auth_devices_count = conn.execute(
                'SELECT COUNT(*) as count FROM auth_devices WHERE EXISTS '
                '(SELECT 1 FROM auth_devices_initial WHERE upload_id = ? AND 1=1)',
                (upload_id,)
            ).fetchone()['count']
            
            device_groups_count = conn.execute(
                'SELECT COUNT(*) as count FROM device_groups'
            ).fetchone()['count']
        
        assert auth_devices_count >= 1, \
            f"Hard merge should create at least 1 auth_device, got {auth_devices_count}"
        # Device groups should exist and be reasonable in count
        assert device_groups_count >= 1, \
            f"Soft merge should create at least 1 device_group, got {device_groups_count}"
        assert device_groups_count <= 5, \
            f"Device groups should be reasonable (<=5) for this test data, got {device_groups_count}"
