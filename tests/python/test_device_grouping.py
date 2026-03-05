import pytest
import json
import uuid
from datetime import datetime, timezone

from db_session import DatabaseSession

# Mock the _get_config_value function used in worker.py
import builtins
builtins.DB_PATH = ":memory:" # Use in-memory database for testing


# Import the worker functions
from device_grouping.worker import group, _os_guard, _hard_match, _is_specific_model, _soft_match
from utils.redaction_utils import values_match


@pytest.fixture
def db_session():
    with DatabaseSession(":memory:") as conn:
        conn.execute("""
            CREATE TABLE uploads (
                id TEXT PRIMARY KEY, 
                given_name TEXT,         
                platform TEXT,           
                upload_timestamp REAL,
                updated_at REAL,
                color TEXT
            );
        """)
        conn.execute("""
            CREATE TABLE uploaded_files (
                id TEXT PRIMARY KEY, 
                manifest_file_id TEXT,
                upload_id TEXT, 
                opfs_filename TEXT,                
                manifest_filename TEXT,        
                file_hash TEXT,               
                upload_timestamp REAL,        
                file_size_bytes INTEGER,
                parse_status TEXT,
                FOREIGN KEY(upload_id) REFERENCES uploads(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE raw_data (
                id TEXT PRIMARY KEY,
                upload_id TEXT,
                file_id TEXT,             
                data JSONTEXT,
                FOREIGN KEY(upload_id) REFERENCES uploads(id) ON DELETE CASCADE,
                FOREIGN KEY(file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE auth_devices_initial (
                id TEXT PRIMARY KEY,
                upload_id TEXT,
                file_id TEXT,
                raw_data_id TEXT,
                entity_type TEXT,
                event_kind TEXT,
                event_category JSONTEXT DEFAULT '[]',
                attributes JSONTEXT,     
                FOREIGN KEY(upload_id) REFERENCES uploads(id) ON DELETE CASCADE,
                FOREIGN KEY(file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE,
                FOREIGN KEY(raw_data_id) REFERENCES raw_data(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE auth_devices (
                id TEXT PRIMARY KEY,
                upload_ids JSONTEXT NOT NULL,
                file_ids JSONTEXT NOT NULL,    
                auth_devices_initial_ids JSONTEXT NOT NULL,
                attributes JSONTEXT    
            );
        """)
        conn.execute("""
            CREATE TABLE device_groups (
                id TEXT PRIMARY KEY,
                auth_devices_ids JSONTEXT NOT NULL,  
                initial_soft_merge BOOLEAN DEFAULT 0,
                soft_merge_flag_status TEXT DEFAULT "na",
                created_at REAL,
                updated_at REAL,
                tags JSONTEXT DEFAULT "[]",
                labels JSONTEXT DEFAULT "[]"
            );
        """)
        conn.commit()
        yield conn

@pytest.fixture
def upload_id():
    return str(uuid.uuid4())

@pytest.fixture
def file_id():
    return str(uuid.uuid4())

@pytest.fixture
def raw_data_id():
    return str(uuid.uuid4())

def insert_auth_device_initial(conn, upload_id, file_id, raw_data_id, attributes):
    device_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO auth_devices_initial (id, upload_id, file_id, raw_data_id, attributes)
        VALUES (?, ?, ?, ?, ?)
    """, (device_id, upload_id, file_id, raw_data_id, json.dumps(attributes)))
    conn.commit()
    return device_id

def get_auth_devices(conn):
    return conn.execute("SELECT id, upload_ids, file_ids, auth_devices_initial_ids, attributes FROM auth_devices").fetchall()

def get_device_groups(conn):
    return conn.execute("SELECT id, auth_devices_ids, initial_soft_merge, soft_merge_flag_status, tags, labels FROM device_groups").fetchall()


# Test cases for _is_specific_model
@pytest.mark.parametrize("model_name,expected", [
    ("iPhone 12 Pro Max", True),
    ("Samsung Galaxy S21 Ultra", True),
    ("iPad Air 4", True),
    ("Pixel 6a", True),
    ("iPhone", False),
    ("Samsung Galaxy", False),
    ("Other Device", False),
    ("unknown", False),
    ("phone", False),
    ("", False),
])
def test_is_specific_model(model_name, expected):
    assert _is_specific_model(model_name) == expected


# Test cases for _os_guard
@pytest.mark.parametrize("attrs_a,attrs_b,expected", [
    ({"user_agent.os.type": "ios"}, {"user_agent.os.type": "ios"}, True),
    ({"user_agent.os.type": "android"}, {"user_agent.os.type": "android"}, True),
    ({"user_agent.os.type": "ios"}, {"user_agent.os.type": "android"}, False),
    ({"user_agent.os.type": "ios"}, {}, True),
    ({}, {"user_agent.os.type": "android"}, True),
    ({}, {}, True),
    ({"user_agent.os.type": "iOS"}, {"user_agent.os.type": "ios"}, True), # Case insensitive
])
def test_os_guard(attrs_a, attrs_b, expected):
    assert _os_guard(attrs_a, attrs_b) == expected


# Test cases for _hard_match
@pytest.mark.parametrize("attrs_a,attrs_b,expected", [
    ({"device.id.some_id": "123"}, {"device.id.some_id": "123"}, True),
    ({"device.serial_number": "SN123"}, {"device.serial_number": "SN123"}, True),
    ({"device.imei": "****1234"}, {"device.imei": "****1234"}, True),
    ({"device.id.some_id": "123"}, {"device.id.some_id": "456"}, False),
    ({"device.id.some_id": "123"}, {"device.serial_number": "SN123"}, False),
    ({"device.imei": "****1234"}, {"device.imei": "***5678"}, False),
    ({"device.imei": "1234"}, {"device.imei": "****1234"}, True), # values_match test
    ({"device.imei": "1234"}, {"device.imei": "1234"}, True),
    ({"device.imei": "1234"}, {"device.imei": "4321"}, False),
    ({"device.imei": "XXXX1234"}, {"device.imei": "YYYY1234"}, True), # values_match test
    ({"device.imei": "XXXX1234"}, {"device.imei": "YYYY5678"}, False),
])
def test_hard_match(attrs_a, attrs_b, expected):
    assert _hard_match(attrs_a, attrs_b) == expected


# Test cases for _soft_match
@pytest.mark.parametrize("attrs_a,attrs_b,expected", [
    ({"device.manufacturer": "Apple", "device.model.name": "iPhone 12 Pro"}, {"device.manufacturer": "Apple", "device.model.name": "iPhone 12 Pro"}, True),
    ({"device.manufacturer": "Samsung", "device.model.name": "Galaxy S21 Ultra"}, {"device.manufacturer": "Samsung", "device.model.name": "Galaxy S21 Ultra"}, True),
    ({"device.manufacturer": "Apple", "device.model.name": "iPhone"}, {"device.manufacturer": "Apple", "device.model.name": "iPhone"}, False), # Not specific
    ({"device.manufacturer": "Apple", "device.model.name": "iPhone 12 Pro"}, {"device.manufacturer": "Samsung", "device.model.name": "iPhone 12 Pro"}, False),
    ({"device.manufacturer": "Apple", "device.model.name": "iPhone 12 Pro"}, {"device.manufacturer": "Apple", "device.model.name": "iPhone 13 Pro"}, False),
    ({"device.manufacturer": "Apple"}, {"device.manufacturer": "Apple", "device.model.name": "iPhone 12 Pro"}, False), # Missing model.name
    ({}, {}, False),
])
def test_soft_match(attrs_a, attrs_b, expected):
    assert _soft_match(attrs_a, attrs_b) == expected


# End-to-end tests for the group function
def test_group_hard_match(db_session, upload_id, file_id, raw_data_id):
    # Two devices with same serial number, same OS
    id1 = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.serial_number": "SN123", "user_agent.os.type": "ios"})
    id2 = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.serial_number": "SN123", "user_agent.os.type": "ios"})

    group(upload_id)

    auth_devices = get_auth_devices(db_session)
    device_groups = get_device_groups(db_session)

    assert len(auth_devices) == 1
    assert json.loads(auth_devices[0]["auth_devices_initial_ids"]) == [id1, id2]
    assert len(device_groups) == 1
    assert json.loads(device_groups[0]["auth_devices_ids"]) == [auth_devices[0]["id"]]
    assert device_groups[0]["initial_soft_merge"] == 0 # No soft merge at this point

def test_group_os_guard_hard_match(db_session, upload_id, file_id, raw_data_id):
    # Two devices with same serial number, different OS
    id1 = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.serial_number": "SN123", "user_agent.os.type": "ios"})
    id2 = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.serial_number": "SN123", "user_agent.os.type": "android"})

    group(upload_id)

    auth_devices = get_auth_devices(db_session)
    device_groups = get_device_groups(db_session)

    assert len(auth_devices) == 2 # Should not hard merge due to OS guard
    assert len(device_groups) == 2 # Should not soft merge either

def test_group_soft_match(db_session, upload_id, file_id, raw_data_id):
    # Two auth_devices with same manufacturer and specific model, same OS
    # First, create auth_devices from auth_devices_initial
    id1_initial = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.manufacturer": "Apple", "device.model.name": "iPhone 13", "user_agent.os.type": "ios"})
    id2_initial = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.manufacturer": "Apple", "device.model.name": "iPhone 13", "user_agent.os.type": "ios"})

    group(upload_id) # This runs pass 1 (hard merge) and pass 2 (soft merge)

    auth_devices = get_auth_devices(db_session)
    device_groups = get_device_groups(db_session)

    assert len(auth_devices) == 2 # No hard match, so two auth_devices
    assert len(device_groups) == 1 # Should soft merge into one device_group
    assert device_groups[0]["initial_soft_merge"] == 1
    assert json.loads(device_groups[0]["auth_devices_ids"]) == [auth_devices[0]["id"], auth_devices[1]["id"]]


def test_group_os_guard_soft_match(db_session, upload_id, file_id, raw_data_id):
    # Two auth_devices with same manufacturer and specific model, different OS
    id1_initial = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.manufacturer": "Apple", "device.model.name": "iPhone 13", "user_agent.os.type": "ios"})
    id2_initial = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.manufacturer": "Apple", "device.model.name": "iPhone 13", "user_agent.os.type": "android"})

    group(upload_id)

    auth_devices = get_auth_devices(db_session)
    device_groups = get_device_groups(db_session)

    assert len(auth_devices) == 2
    assert len(device_groups) == 2 # Should not soft merge due to OS guard

def test_group_singleton_output(db_session, upload_id, file_id, raw_data_id):
    # One device that doesn't match anything
    id1_initial = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.manufacturer": "Generic", "device.model.name": "Tablet", "user_agent.os.type": "android"})

    group(upload_id)

    auth_devices = get_auth_devices(db_session)
    device_groups = get_device_groups(db_session)

    assert len(auth_devices) == 1
    assert len(device_groups) == 1
    assert json.loads(device_groups[0]["auth_devices_ids"]) == [auth_devices[0]["id"]]
    assert device_groups[0]["initial_soft_merge"] == 0 # Not a soft merge

def test_group_redaction_suffix_comparison(db_session, upload_id, file_id, raw_data_id):
    # Two devices hard-matching via redacted IMEI
    id1 = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.imei": "XXXX1234", "user_agent.os.type": "ios"})
    id2 = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.imei": "YYYY1234", "user_agent.os.type": "ios"})

    group(upload_id)

    auth_devices = get_auth_devices(db_session)
    device_groups = get_device_groups(db_session)

    assert len(auth_devices) == 1
    assert json.loads(auth_devices[0]["auth_devices_initial_ids"]) == [id1, id2]
    assert len(device_groups) == 1
    assert json.loads(device_groups[0]["auth_devices_ids"]) == [auth_devices[0]["id"]]
    assert device_groups[0]["initial_soft_merge"] == 0

def test_group_multiple_hard_and_soft_matches(db_session, upload_id, file_id, raw_data_id):
    # Scenario:
    # A & B hard-match (same SN) -> AD1
    # C & D hard-match (same IMEI) -> AD2
    # E is singleton -> AD3
    # AD1 & AD2 soft-match (same Mfr, specific Model, same OS) -> DG1
    # AD3 is singleton -> DG2

    # Initial devices
    # Group 1: Hard match (SN123, iOS)
    id_a = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.serial_number": "SN123", "user_agent.os.type": "ios", "device.manufacturer": "Apple", "device.model.name": "iPhone 14"})
    id_b = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.serial_number": "SN123", "user_agent.os.type": "ios", "device.manufacturer": "Apple", "device.model.name": "iPhone 14"})
    # Group 2: Hard match (IMEI456, iOS)
    id_c = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.imei": "XXXX4567", "user_agent.os.type": "ios", "device.manufacturer": "Apple", "device.model.name": "iPhone 14"})
    id_d = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.imei": "YYYY4567", "user_agent.os.type": "ios", "device.manufacturer": "Apple", "device.model.name": "iPhone 14"})
    # Group 3: Singleton (Android)
    id_e = insert_auth_device_initial(db_session, upload_id, file_id, raw_data_id, {"device.manufacturer": "Samsung", "device.model.name": "Galaxy Tab S8", "user_agent.os.type": "android"})

    group(upload_id)

    auth_devices = get_auth_devices(db_session)
    device_groups = get_device_groups(db_session)

    assert len(auth_devices) == 3 # AD1 (A,B), AD2 (C,D), AD3 (E)
    assert len(device_groups) == 2 # DG1 (AD1, AD2), DG2 (AD3)

    # Verify hard merges
    ad_initial_ids_list = [json.loads(ad["auth_devices_initial_ids"]) for ad in auth_devices]
    assert [id_a, id_b] in ad_initial_ids_list
    assert [id_c, id_d] in ad_initial_ids_list
    assert [id_e] in ad_initial_ids_list

    # Verify soft merges
    dg_auth_device_ids_list = [json.loads(dg["auth_devices_ids"]) for dg in device_groups]
    
    # Find the auth_device IDs for AD1, AD2, AD3
    ad1_id = next(ad["id"] for ad in auth_devices if id_a in json.loads(ad["auth_devices_initial_ids"]))
    ad2_id = next(ad["id"] for ad in auth_devices if id_c in json.loads(ad["auth_devices_initial_ids"]))
    ad3_id = next(ad["id"] for ad in auth_devices if id_e in json.loads(ad["auth_devices_initial_ids"]))

    # Check that AD1 and AD2 are grouped together
    assert sorted([ad1_id, ad2_id]) in [sorted(ids) for ids in dg_auth_device_ids_list]
    # Check that AD3 is a singleton group
    assert [ad3_id] in dg_auth_device_ids_list

    # Check initial_soft_merge flag
    for dg in device_groups:
        if sorted(json.loads(dg["auth_devices_ids"])) == sorted([ad1_id, ad2_id]):
            assert dg["initial_soft_merge"] == 1
        elif json.loads(dg["auth_devices_ids"]) == [ad3_id]:
            assert dg["initial_soft_merge"] == 0
