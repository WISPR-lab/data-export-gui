import os
import pytest
import json
import uuid
from db_session import DatabaseSession
from device_grouping2.worker import group

class TestDeviceGrouping2:
    """Test device_grouping2.worker.group() incremental edge insertion."""

    def test_group_edges_creation(self, test_db_path):
        upload_id = 'test-grouping2-' + str(uuid.uuid4())
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'schema.sql')
        
        with DatabaseSession(test_db_path, schema_path=schema_path) as conn:
            conn.execute(
                'INSERT INTO uploads (id, platform, given_name) VALUES (?, ?, ?)',
                (upload_id, 'test', 'test-group-2')
            )
            
            file_id = str(uuid.uuid4())
            conn.execute(
                'INSERT INTO uploaded_files (id, upload_id, opfs_filename) VALUES (?, ?, ?)',
                (file_id, upload_id, 'test_file.json')
            )
            
            # 1. Level 0: Add two identical events to trigger Deduplication
            attrs_dup = {
                'norm__manufacturer': 'Apple',
                'norm__model_name': 'iPhone 13',
                'norm__os_name': 'iOS',
                'norm__client_name': 'Safari',
                'norm__client_version': '16.0',
                'norm__os_version': '16.0',
                'device_serial_number': 'SN-DUP',
            }
            conn.execute(
                'INSERT INTO events (id, upload_id, file_ids, timestamp, attributes, treat_as_auth_device) VALUES (?, ?, ?, ?, ?, 1)',
                ('ev-dup-1', upload_id, json.dumps([file_id]), 1700000000.0, json.dumps(attrs_dup))
            )
            conn.execute(
                'INSERT INTO events (id, upload_id, file_ids, timestamp, attributes, treat_as_auth_device) VALUES (?, ?, ?, ?, ?, 1)',
                ('ev-dup-2', upload_id, json.dumps([file_id]), 1700000000.0, json.dumps(attrs_dup))
            )
            
            # 2. Level 1: Add two events sharing same hardware serial to trigger Hardware match
            attrs_hw = {
                'norm__manufacturer': 'Apple',
                'norm__model_name': 'iPhone 13',
                'norm__os_name': 'iOS',
                'norm__client_name': 'Safari',
                'norm__client_version': '16.0',
                'norm__os_version': '16.0',
                'device_serial_number': 'SN-HW',
            }
            conn.execute(
                'INSERT INTO events (id, upload_id, file_ids, timestamp, attributes, treat_as_auth_device) VALUES (?, ?, ?, ?, ?, 1)',
                ('ev-hw-1', upload_id, json.dumps([file_id]), 1700010000.0, json.dumps(attrs_hw))
            )
            conn.execute(
                'INSERT INTO events (id, upload_id, file_ids, timestamp, attributes, treat_as_auth_device) VALUES (?, ?, ?, ?, ?, 1)',
                ('ev-hw-2', upload_id, json.dumps([file_id]), 1700020000.0, json.dumps(attrs_hw))
            )

            # 3. Level 3: Add two events of same model but different hardware serials to trigger DeviceModel profile grouping
            attrs_prof1 = {
                'norm__manufacturer': 'Samsung',
                'norm__model_name': 'Galaxy S22',
                'norm__os_name': 'Android',
                'norm__client_name': 'Chrome',
                'norm__client_version': '100.0',
                'norm__os_version': '12.0',
                'device_serial_number': 'SN-PROF1',
            }
            attrs_prof2 = {
                'norm__manufacturer': 'Samsung',
                'norm__model_name': 'Galaxy S22',
                'norm__os_name': 'Android',
                'norm__client_name': 'Chrome',
                'norm__client_version': '100.0',
                'norm__os_version': '12.0',
                'device_serial_number': 'SN-PROF2',
            }
            conn.execute(
                'INSERT INTO events (id, upload_id, file_ids, timestamp, attributes, treat_as_auth_device) VALUES (?, ?, ?, ?, ?, 1)',
                ('ev-prof-1', upload_id, json.dumps([file_id]), 1700030000.0, json.dumps(attrs_prof1))
            )
            conn.execute(
                'INSERT INTO events (id, upload_id, file_ids, timestamp, attributes, treat_as_auth_device) VALUES (?, ?, ?, ?, ?, 1)',
                ('ev-prof-2', upload_id, json.dumps([file_id]), 1700040000.0, json.dumps(attrs_prof2))
            )

            conn.commit()

        # Run the new grouping worker
        group(upload_id, db_path=test_db_path)

        # Assert edges are populated correctly
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            edges = conn.execute('SELECT * FROM edges').fetchall()
            assert len(edges) >= 3, f"Should have created edges, got {edges}"
            
            types = {e['type'] for e in edges}
            assert 'Deduplication' in types, f"Expected Deduplication in types: {types}"
            assert 'Hardware' in types, f"Expected Hardware in types: {types}"
            assert 'DeviceModel' in types, f"Expected DeviceModel in types: {types}"
