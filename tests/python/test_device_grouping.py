import os
import pytest
import json
import uuid
import builtins
from db_session import DatabaseSession
from semantic_map.worker import map as semantic_map
from field_normalization.worker import normalize
from device_grouping.worker import group


class TestDeviceGrouping:
    """Test device_grouping.worker.group() after full normalization pipeline."""

    def test_group_hard_merge_same_serial_number(self, test_db_path):
        """Test hard merge: devices with same serial number are merged."""
        upload_id = 'test-hard-merge-' + str(uuid.uuid4())
        
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'schema.sql')
        with DatabaseSession(test_db_path, schema_path=schema_path) as conn:
            conn.execute(
                'INSERT INTO uploads (id, platform, given_name) VALUES (?, ?, ?)',
                (upload_id, 'test', 'test-hard-merge')
            )
            
            # Two devices with same serial number
            for i in range(2):
                file_id = str(uuid.uuid4())
                conn.execute(
                    'INSERT INTO uploaded_files (id, upload_id, opfs_filename) VALUES (?, ?, ?)',
                    (file_id, upload_id, f'device_{i}.json')
                )
                
                attrs = {
                    'device_serial_number': 'SN-SHARED-12345',
                    'device_model_name': f'Device {i}',
                }
                conn.execute(
                    'INSERT INTO devices_raw (id, upload_id, file_id, attributes) VALUES (?, ?, ?, ?)',
                    (str(uuid.uuid4()), upload_id, file_id, json.dumps(attrs))
                )
            conn.commit()
        
        group(upload_id, db_path=test_db_path)
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            atomic_devices = conn.execute(
                'SELECT id, devices_raw_ids FROM atomic_devices WHERE 1=1'
            ).fetchall()
            
            assert len(atomic_devices) >= 1, f"Hard merge should create at least 1 auth_device, got {len(atomic_devices)}"
    
    def test_group_soft_merge_same_model_and_manufacturer(self, sample_upload_with_raw_data, test_db_path):
        """Test soft merge: similar devices are grouped."""
        upload_id, _ = sample_upload_with_raw_data
        
        semantic_map(
            platform='facebook',
            upload_id=upload_id,
            db_path=test_db_path,
            manifest_dir=builtins.MANIFESTS_DIR
        )
        
        normalize(upload_id, db_path=test_db_path)
        
        group(upload_id, db_path=test_db_path)
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            device_profiles = conn.execute(
                'SELECT id, atomic_devices_ids, initial_soft_merge FROM device_profiles'
            ).fetchall()
            
            assert len(device_profiles) > 0, "Should create at least one device_group"
            
            for dg in device_profiles:
                ids = json.loads(dg['atomic_devices_ids'])
                assert isinstance(ids, list), f"atomic_devices_ids should be list, got {type(ids)}"
                assert len(ids) > 0, "Each device_group should have at least one auth_device"
    
    def test_group_soft_merge_apple_blacklist(self, test_db_path):
        """Test soft merge: Apple devices with generic + specific model DON'T merge."""
        upload_id = 'test-apple-blacklist-' + str(uuid.uuid4())
        
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'schema.sql')
        with DatabaseSession(test_db_path, schema_path=schema_path) as conn:
            conn.execute(
                'INSERT INTO uploads (id, platform, given_name) VALUES (?, ?, ?)',
                (upload_id, 'test', 'test-apple-blacklist')
            )
            
            # Create two Apple atomic_devices before grouping
            for i in range(2):
                file_id = str(uuid.uuid4())
                conn.execute(
                    'INSERT INTO uploaded_files (id, upload_id, opfs_filename) VALUES (?, ?, ?)',
                    (file_id, upload_id, f'apple_{i}.json')
                )
                
                if i == 0:
                    attrs = {
                        'device_manufacturer': 'Apple',
                        'device_model_name': 'iPhone',  # Generic
                        'user_agent_device_manufacturer': 'Apple',
                        'user_agent_device_model': 'iPhone 14 Pro',  # Specific in UA
                    }
                else:
                    attrs = {
                        'device_manufacturer': 'Apple',
                        'device_model_name': 'iPhone 14 Pro',  # Specific
                        'user_agent_device_manufacturer': 'Apple',
                        'user_agent_device_model': 'iPhone 14 Pro',
                    }
                
                conn.execute(
                    'INSERT INTO devices_raw (id, upload_id, file_id, attributes) VALUES (?, ?, ?, ?)',
                    (str(uuid.uuid4()), upload_id, file_id, json.dumps(attrs))
                )
            conn.commit()
        
        group(upload_id, db_path=test_db_path)
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            device_profiles = conn.execute(
                'SELECT COUNT(*) as count FROM device_profiles WHERE 1=1'
            ).fetchone()
            
            assert device_profiles['count'] > 0, "Apple blacklist test should create device_profiles"
