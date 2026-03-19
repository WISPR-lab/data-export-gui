import pytest
import json
import sqlite3
import tempfile
import os
from pathlib import Path

from db_session import DatabaseSession
from device_grouping.worker import group


@pytest.fixture
def temp_db():
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'schema.sql')
    with DatabaseSession(db_path, schema_path=schema_path) as conn:
        conn.commit()
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


def test_multi_upload_same_imei_merges(temp_db):
    """
    Test: Device with same IMEI across two uploads gets merged into one atomic.
    
    Upload 1: iPhone 7 with IMEI 123456
    Upload 2: iPhone 7 with IMEI 123456
    
    Expected: One atomic_device with two origins
    """
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        # Upload 1: Insert raw device with IMEI
        conn.execute("""
            INSERT INTO devices_raw (id, upload_id, file_id, origin, attributes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'raw_1',
            'upload_1',
            'file_1',
            'apple/web',
            json.dumps({
                'device_imei': '123456',
                'device_model_name': 'iPhone 7',
                'device_manufacturer': 'Apple'
            })
        ))
        
        # Run grouping for upload 1
        group('upload_1', temp_db)
        
        # Upload 2: Insert same device (same IMEI)
        conn.execute("""
            INSERT INTO devices_raw (id, upload_id, file_id, origin, attributes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'raw_2',
            'upload_2',
            'file_2',
            'google/web',
            json.dumps({
                'device_imei': '123456',
                'device_model_name': 'iPhone 7',
                'device_manufacturer': 'Apple'
            })
        ))
        
        # Run grouping for upload 2
        group('upload_2', temp_db)
        
        # Check: Only one atomic (merged)
        atomics = conn.execute('SELECT * FROM atomic_devices').fetchall()
        assert len(atomics) == 1, f"Expected 1 atomic, got {len(atomics)}"
        
        atomic = atomics[0]
        origins = json.loads(atomic['origins'])
        
        # Check origins from both uploads
        assert len(origins) == 2, f"Expected 2 origins, got {len(origins)}"
        origin_strs = {o['origin'] for o in origins}
        assert origin_strs == {'apple/web', 'google/web'}
        
        # Check devices_raw_ids includes both
        devices_raw_ids = json.loads(atomic['devices_raw_ids'])
        assert set(devices_raw_ids) == {'raw_1', 'raw_2'}
        
        # Check specificity is 3 (hard key IMEI)
        assert atomic['specificity'] == 3


def test_multi_upload_different_devices(temp_db):
    """
    Test: Different devices across two uploads create separate atomics.
    
    Upload 1: iPhone 7 with IMEI 123456
    Upload 2: iPhone 13 with IMEI 789012
    
    Expected: Two atomic_devices
    """
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        # Upload 1
        conn.execute("""
            INSERT INTO devices_raw (id, upload_id, file_id, origin, attributes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'raw_1',
            'upload_1',
            'file_1',
            'apple/web',
            json.dumps({
                'device_imei': '123456',
                'device_model_name': 'iPhone 7',
                'device_manufacturer': 'Apple'
            })
        ))
        
        group('upload_1', temp_db)
        
        # Upload 2: Different device
        conn.execute("""
            INSERT INTO devices_raw (id, upload_id, file_id, origin, attributes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'raw_2',
            'upload_2',
            'file_2',
            'google/web',
            json.dumps({
                'device_imei': '789012',
                'device_model_name': 'iPhone 13',
                'device_manufacturer': 'Apple'
            })
        ))
        
        group('upload_2', temp_db)
        
        # Check: Two atomics (no merge)
        atomics = conn.execute('SELECT * FROM atomic_devices').fetchall()
        assert len(atomics) == 2, f"Expected 2 atomics, got {len(atomics)}"
        
        # Each should have one origin
        for atomic in atomics:
            origins = json.loads(atomic['origins'])
            assert len(origins) == 1


def test_multi_upload_mixed_devices(temp_db):
    """
    Test: Upload 2 has one device matching upload 1 and one new device.
    
    Upload 1: Device A (IMEI 111) + Device B (IMEI 222)
    Upload 2: Device A (IMEI 111) + Device C (IMEI 333)
    
    Expected: 3 atomics total (A merged, B and C separate)
    """
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        # Upload 1: Two devices
        conn.execute("""
            INSERT INTO devices_raw (id, upload_id, file_id, origin, attributes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'raw_1a',
            'upload_1',
            'file_1',
            'apple/web',
            json.dumps({'device_imei': '111', 'device_model_name': 'iPhone 7'})
        ))
        conn.execute("""
            INSERT INTO devices_raw (id, upload_id, file_id, origin, attributes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'raw_1b',
            'upload_1',
            'file_1',
            'apple/web',
            json.dumps({'device_imei': '222', 'device_model_name': 'iPhone 8'})
        ))
        
        group('upload_1', temp_db)
        
        # Upload 2: Device A (matches 111) + Device C (new)
        conn.execute("""
            INSERT INTO devices_raw (id, upload_id, file_id, origin, attributes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'raw_2a',
            'upload_2',
            'file_2',
            'google/web',
            json.dumps({'device_imei': '111', 'device_model_name': 'iPhone 7'})
        ))
        conn.execute("""
            INSERT INTO devices_raw (id, upload_id, file_id, origin, attributes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'raw_2c',
            'upload_2',
            'file_2',
            'google/web',
            json.dumps({'device_imei': '333', 'device_model_name': 'Pixel 6'})
        ))
        
        group('upload_2', temp_db)
        
        # Check: 3 atomics
        atomics = conn.execute('SELECT * FROM atomic_devices ORDER BY id').fetchall()
        assert len(atomics) == 3, f"Expected 3 atomics, got {len(atomics)}"
        
        # Find the merged atomic (has 2 origins and 2 devices_raw_ids)
        merged_atomic = None
        for atomic in atomics:
            devices_raw_ids = json.loads(atomic['devices_raw_ids'])
            if len(devices_raw_ids) == 2:
                merged_atomic = atomic
                break
        
        assert merged_atomic is not None, "Should have one merged atomic with 2 raw devices"
        
        origins = json.loads(merged_atomic['origins'])
        assert len(origins) == 2, "Merged atomic should have 2 origins"
        origin_set = {o['origin'] for o in origins}
        assert 'apple/web' in origin_set and 'google/web' in origin_set


def test_origins_structure(temp_db):
    """Test that origins have correct structure {origin, upload_id}."""
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        # Upload 1
        conn.execute("""
            INSERT INTO devices_raw (id, upload_id, file_id, origin, attributes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'raw_1',
            'upload_1',
            'file_1',
            'facebook/web',
            json.dumps({'device_imei': '555', 'device_model_name': 'Samsung S20'})
        ))
        
        group('upload_1', temp_db)
        
        # Upload 2: Same device
        conn.execute("""
            INSERT INTO devices_raw (id, upload_id, file_id, origin, attributes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'raw_2',
            'upload_2',
            'file_2',
            'twitter/api',
            json.dumps({'device_imei': '555', 'device_model_name': 'Samsung S20'})
        ))
        
        group('upload_2', temp_db)
        
        # Check origin structure
        atomic = conn.execute('SELECT origins FROM atomic_devices').fetchone()
        origins = json.loads(atomic['origins'])
        
        for origin_obj in origins:
            assert 'origin' in origin_obj, "Origin object missing 'origin' field"
            assert 'upload_id' in origin_obj, "Origin object missing 'upload_id' field"
            assert origin_obj['upload_id'] in ['upload_1', 'upload_2']
