import pytest
import json
import uuid
import os
import tempfile
import shutil

from db_session import DatabaseSession
from device_grouping.worker import group


@pytest.fixture(scope="function")
def temp_db():
    """Create a fresh test database in tests/tmp_outputs."""
    tmpdir = os.path.join(os.path.dirname(__file__), 'tmp_outputs')
    os.makedirs(tmpdir, exist_ok=True)
    
    db_path = os.path.join(tmpdir, f'test_multi_{uuid.uuid4()}.db')
    schema_path = os.path.join(os.path.dirname(__file__), '..', '..', 'schema.sql')
    
    with DatabaseSession(db_path, schema_path=schema_path) as conn:
        conn.commit()
    
    yield db_path
    
    if os.path.exists(db_path):
        os.remove(db_path)


def insert_upload_and_file(conn, upload_id, file_id=None):
    """Helper to insert an upload and file."""
    if file_id is None:
        file_id = f'file_{upload_id}'
    conn.execute("INSERT INTO uploads (id) VALUES (?)", (upload_id,))
    conn.execute("INSERT INTO uploaded_files (id, upload_id) VALUES (?, ?)", (file_id, upload_id))
    return file_id


def insert_device_raw(conn, device_id, upload_id, file_id, origin, attrs):
    """Helper to insert a raw device."""
    conn.execute("""
        INSERT INTO devices_raw (id, upload_id, file_id, origin, attributes)
        VALUES (?, ?, ?, ?, ?)
    """, (device_id, upload_id, file_id, origin, json.dumps(attrs)))


def test_multi_upload_same_imei_merges(temp_db):
    """
    Test: Device with same IMEI across two uploads gets merged into one atomic.
    
    Upload 1: iPhone 7 with IMEI 123456
    Upload 2: iPhone 7 with IMEI 123456
    
    Expected: One atomic_device with two origins
    """
    # Setup: Insert first upload and device
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        insert_upload_and_file(conn, 'upload_1', 'file_1')
        insert_device_raw(conn, 'raw_1', 'upload_1', 'file_1', 'apple/web',
                         {'device_imei': '123456', 'device_model_name': 'iPhone 7'})
        conn.commit()
    
    # Process first upload
    group('upload_1', temp_db)
    
    # Setup: Insert second upload and device
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        insert_upload_and_file(conn, 'upload_2', 'file_2')
        insert_device_raw(conn, 'raw_2', 'upload_2', 'file_2', 'google/web',
                         {'device_imei': '123456', 'device_model_name': 'iPhone 7'})
        conn.commit()
    
    # Process second upload
    group('upload_2', temp_db)
    
    # Verify: Only one atomic (merged)
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        atomics = conn.execute('SELECT * FROM atomic_devices ORDER BY id').fetchall()
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
    # Upload 1
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        insert_upload_and_file(conn, 'upload_1', 'file_1')
        insert_device_raw(conn, 'raw_1', 'upload_1', 'file_1', 'apple/web',
                         {'device_imei': '123456', 'device_model_name': 'iPhone 7'})
        conn.commit()
    
    group('upload_1', temp_db)
    
    # Upload 2: Different device
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        insert_upload_and_file(conn, 'upload_2', 'file_2')
        insert_device_raw(conn, 'raw_2', 'upload_2', 'file_2', 'google/web',
                         {'device_imei': '789012', 'device_model_name': 'iPhone 13'})
        conn.commit()
    
    group('upload_2', temp_db)
    
    # Verify: Two atomics (no merge)
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
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
    # Upload 1: Two devices
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        insert_upload_and_file(conn, 'upload_1', 'file_1')
        insert_device_raw(conn, 'raw_1a', 'upload_1', 'file_1', 'apple/web',
                         {'device_imei': '111', 'device_model_name': 'iPhone 7'})
        insert_device_raw(conn, 'raw_1b', 'upload_1', 'file_1', 'apple/web',
                         {'device_imei': '222', 'device_model_name': 'iPhone 8'})
        conn.commit()
    
    group('upload_1', temp_db)
    
    # Upload 2: Device A (matches 111) + Device C (new)
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        insert_upload_and_file(conn, 'upload_2', 'file_2')
        insert_device_raw(conn, 'raw_2a', 'upload_2', 'file_2', 'google/web',
                         {'device_imei': '111', 'device_model_name': 'iPhone 7'})
        insert_device_raw(conn, 'raw_2c', 'upload_2', 'file_2', 'google/web',
                         {'device_imei': '333', 'device_model_name': 'Pixel 6'})
        conn.commit()
    
    group('upload_2', temp_db)
    
    # Verify: 3 atomics
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
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
    # Upload 1
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        insert_upload_and_file(conn, 'upload_1', 'file_1')
        insert_device_raw(conn, 'raw_1', 'upload_1', 'file_1', 'facebook/web',
                         {'device_imei': '555', 'device_model_name': 'Samsung S20'})
        conn.commit()
    
    group('upload_1', temp_db)
    
    # Upload 2: Same device
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        insert_upload_and_file(conn, 'upload_2', 'file_2')
        insert_device_raw(conn, 'raw_2', 'upload_2', 'file_2', 'twitter/api',
                         {'device_imei': '555', 'device_model_name': 'Samsung S20'})
        conn.commit()
    
    group('upload_2', temp_db)
    
    # Verify origin structure
    with DatabaseSession(temp_db, use_dict_factory=True) as conn:
        atomic = conn.execute('SELECT origins FROM atomic_devices').fetchone()
        origins = json.loads(atomic['origins'])
        
        for origin_obj in origins:
            assert 'origin' in origin_obj, "Origin object missing 'origin' field"
            assert 'upload_id' in origin_obj, "Origin object missing 'upload_id' field"
            assert origin_obj['upload_id'] in ['upload_1', 'upload_2']
