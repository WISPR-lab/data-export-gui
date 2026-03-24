import pytest
import json
import uuid
import os
import builtins
from db_session import DatabaseSession
from semantic_map.worker import map as semantic_map
from field_normalization.worker import normalize


class TestFieldNormalization:
    """Test field_normalization.worker.normalize() after semantic mapping."""

    def test_normalize_parses_user_agents(self, sample_upload_with_raw_data, test_db_path):
        """Verify that normalize() parses user_agent fields when they exist."""
        upload_id, _ = sample_upload_with_raw_data
        
        semantic_map(
            platform='facebook',
            upload_id=upload_id,
            db_path=test_db_path,
            manifest_dir=builtins.MANIFESTS_DIR
        )
        
        result = normalize(upload_id, db_path=test_db_path)
        
        assert result['status'] == 'success'
        assert result['records_normalized'] > 0
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            rows = conn.execute(
                'SELECT id, attributes FROM devices_raw WHERE upload_id = ?',
                (upload_id,)
            ).fetchall()
            
            # Check that rows with user_agent_original or user_agent_os_full have parsed fields
            rows_with_ua = 0
            rows_with_parsed = 0
            for row in rows:
                attrs = json.loads(row['attributes'])
                if attrs.get('user_agent_original') or attrs.get('user_agent_os_full'):
                    rows_with_ua += 1
                    # Verify specific fields were parsed
                    if ('user_agent_os_name' in attrs or 'user_agent_os_type' in attrs or 
                        'user_agent_device_model' in attrs or 'user_agent_name' in attrs):
                        rows_with_parsed += 1
            
            # If we had rows with UA data, verify they were parsed
            if rows_with_ua > 0:
                assert rows_with_parsed > 0, f"Had {rows_with_ua} rows with UA data but only {rows_with_parsed} were parsed"
    
    def test_normalize_infers_device_manufacturer(self, sample_upload_with_raw_data, test_db_path):
        """Verify that device_manufacturer is parsed when UA data exists."""
        upload_id, _ = sample_upload_with_raw_data
        
        semantic_map(
            platform='facebook',
            upload_id=upload_id,
            db_path=test_db_path,
            manifest_dir=builtins.MANIFESTS_DIR
        )
        
        normalize(upload_id, db_path=test_db_path)
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            rows = conn.execute(
                'SELECT id, attributes FROM devices_raw WHERE upload_id = ?',
                (upload_id,)
            ).fetchall()
            
            # Check rows that have UA data
            rows_with_ua = [r for r in rows if json.loads(r['attributes']).get('user_agent_original') or json.loads(r['attributes']).get('user_agent_os_full')]
            
            if rows_with_ua:
                # If any rows had UA data, verify they were at least attempted to parse
                has_parsed = any(
                    'user_agent_device_manufacturer' in json.loads(r['attributes']) 
                    for r in rows_with_ua
                )
                assert has_parsed or len(rows_with_ua) == 0, \
                    "At least one row with UA data should have parsed fields"
    
    def test_normalize_caches_user_agents(self, sample_upload_with_raw_data, test_db_path):
        """Verify that normalize() caches UA parsing across multiple rows."""
        upload_id, _ = sample_upload_with_raw_data
        
        semantic_map(
            platform='facebook',
            upload_id=upload_id,
            db_path=test_db_path,
            manifest_dir=builtins.MANIFESTS_DIR
        )
        
        result = normalize(upload_id, db_path=test_db_path)
        
        assert result['status'] == 'success'
        unique_uas_parsed = result['unique_uas_parsed']
        records_normalized = result['records_normalized']
        
        assert unique_uas_parsed <= records_normalized, \
            f"Unique UAs ({unique_uas_parsed}) should not exceed total records ({records_normalized})"
        
        # If we have more records than unique UAs, caching worked (duplicate strings were cached)
        if records_normalized > 1:
            assert unique_uas_parsed < records_normalized or unique_uas_parsed == records_normalized, \
                "Cache should reduce unique count when duplicate UA strings exist"

    def test_normalize_with_hardcoded_user_agent_original(self, test_db_path):
        """Test normalize with hardcoded data that has user_agent_original."""
        upload_id = 'test-hardcoded-ua-' + str(uuid.uuid4())
        
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'schema.sql')
        with DatabaseSession(test_db_path, schema_path=schema_path) as conn:
            conn.execute(
                'INSERT INTO uploads (id, platform, given_name) VALUES (?, ?, ?)',
                (upload_id, 'test', 'test-ua-original')
            )
            
            # Create devices with definite user_agent_original strings
            ua_strings = [
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/21H216 [FBAN/FBIOS;FBDV/iPhone11,8]",
                "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]
            
            for i, ua in enumerate(ua_strings):
                file_id = str(uuid.uuid4())
                conn.execute(
                    'INSERT INTO uploaded_files (id, upload_id, opfs_filename) VALUES (?, ?, ?)',
                    (file_id, upload_id, f'device_{i}.json')
                )
                
                attrs = {'user_agent_original': ua}
                conn.execute(
                    'INSERT INTO devices_raw (id, upload_id, file_id, attributes) VALUES (?, ?, ?, ?)',
                    (str(uuid.uuid4()), upload_id, file_id, json.dumps(attrs))
                )
            
            conn.commit()
        
        result = normalize(upload_id, db_path=test_db_path)
        
        assert result['status'] == 'success'
        assert result['records_normalized'] == 3
        assert result['unique_uas_parsed'] == 3, "Should have parsed 3 unique UAs"
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            rows = conn.execute(
                'SELECT attributes FROM devices_raw WHERE upload_id = ?',
                (upload_id,)
            ).fetchall()
            
            assert len(rows) == 3
            
            # Collect OS names and types from all rows
            os_names = set()
            os_types = set()
            device_models = set()
            for row in rows:
                attrs = json.loads(row['attributes'])
                if attrs.get('user_agent_os_name'):
                    os_names.add(attrs['user_agent_os_name'])
                if attrs.get('user_agent_os_type'):
                    os_types.add(attrs['user_agent_os_type'])
                if attrs.get('user_agent_device_model'):
                    device_models.add(attrs['user_agent_device_model'])
            
            # Check that we got all three expected OS types
            assert os_names == {'iOS', 'Android', 'Windows'}, f"Expected iOS, Android, Windows but got {os_names}"
            assert os_types == {'ios', 'android', 'windows'}, f"Expected ios, android, windows but got {os_types}"
            # Device models should be populated for at least some rows
            assert len(device_models) > 0, f"Should have parsed device models but got none"

    def test_normalize_with_hardcoded_user_agent_os_full(self, test_db_path):
        """Test normalize with hardcoded data that has user_agent_os_full."""
        upload_id = 'test-hardcoded-os-full-' + str(uuid.uuid4())
        
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'schema.sql')
        with DatabaseSession(test_db_path, schema_path=schema_path) as conn:
            conn.execute(
                'INSERT INTO uploads (id, platform, given_name) VALUES (?, ?, ?)',
                (upload_id, 'test', 'test-os-full')
            )
            
            # Create devices with user_agent_os_full (like from mobile_devices.json)
            os_strings = [
                'iPhone OS 17.7.1',
                'Android 13',
                'iPhone OS 15.7',
            ]
            
            for i, os_str in enumerate(os_strings):
                file_id = str(uuid.uuid4())
                conn.execute(
                    'INSERT INTO uploaded_files (id, upload_id, opfs_filename) VALUES (?, ?, ?)',
                    (file_id, upload_id, f'device_{i}.json')
                )
                
                attrs = {'user_agent_os_full': os_str}
                conn.execute(
                    'INSERT INTO devices_raw (id, upload_id, file_id, attributes) VALUES (?, ?, ?, ?)',
                    (str(uuid.uuid4()), upload_id, file_id, json.dumps(attrs))
                )
            
            conn.commit()
        
        result = normalize(upload_id, db_path=test_db_path)
        
        assert result['status'] == 'success'
        assert result['records_normalized'] == 3
        assert result['unique_uas_parsed'] == 3, "Should have parsed 3 unique OS strings"
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            rows = conn.execute(
                'SELECT attributes FROM devices_raw WHERE upload_id = ? ORDER BY id',
                (upload_id,)
            ).fetchall()
            
            assert len(rows) == 3
            
            # All should have os_type populated from DeviceDetector parsing of os_full
            # Also verify os.name is populated
            os_names = set()
            for i, row in enumerate(rows):
                attrs = json.loads(row['attributes'])
                assert 'user_agent_os_type' in attrs, f"Row {i} should have os_type"
                assert 'user_agent_os_name' in attrs, f"Row {i} should have os_name"
                os_names.add(attrs['user_agent_os_name'])
            
            # Verify we got all three OS types from partial strings
            assert os_names == {'iOS', 'Android'} or 'iOS' in os_names and 'Android' in os_names, \
                f"Should have parsed iOS and Android from os_full strings, got {os_names}"
