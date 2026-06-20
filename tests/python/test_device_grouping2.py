import os
import pytest
import json
import uuid
from db_session import DatabaseSession
from device_grouping2.worker import group


class TestDeviceGrouping2:
    """Test device_grouping2 pipeline and its DB outputs."""

    def test_group_pipeline_outputs(self, test_db_path):
        upload_id = "test-grouping2-" + str(uuid.uuid4())
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "..", "schema.sql"
        )

        with DatabaseSession(test_db_path, schema_path=schema_path) as conn:
            conn.execute(
                "INSERT INTO uploads (id, platform, given_name) VALUES (?, ?, ?)",
                (upload_id, "test", "test-group-2"),
            )

            file_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO uploaded_files (id, upload_id, opfs_filename) VALUES (?, ?, ?)",
                (file_id, upload_id, "test_file.json"),
            )

            # 1. Level 0: Deduplication events
            attrs_dup = {
                "norm__manufacturer": "Apple",
                "norm__model_name": "iPhone 13",
                "norm__os_name": "iOS",
                "norm__client_name": "Safari",
                "norm__client_version": "16.0",
                "norm__os_version": "16.0",
                "device_serial_number": "SN-DUP",
            }
            conn.execute(
                "INSERT INTO events (id, upload_id, file_ids, timestamp, attributes, treat_as_auth_device) VALUES (?, ?, ?, ?, ?, 1)",
                (
                    "ev-dup-1",
                    upload_id,
                    json.dumps([file_id]),
                    1700000000.0,
                    json.dumps(attrs_dup),
                ),
            )
            conn.execute(
                "INSERT INTO events (id, upload_id, file_ids, timestamp, attributes, treat_as_auth_device) VALUES (?, ?, ?, ?, ?, 1)",
                (
                    "ev-dup-2",
                    upload_id,
                    json.dumps([file_id]),
                    1700000000.0,
                    json.dumps(attrs_dup),
                ),
            )

            # 2. Level 1: Hardware serial match events (same serial)
            attrs_hw = {
                "norm__manufacturer": "Apple",
                "norm__model_name": "iPhone 13",
                "norm__os_name": "iOS",
                "norm__client_name": "Safari",
                "norm__client_version": "16.0",
                "norm__os_version": "16.0",
                "device_serial_number": "SN-HW",
            }
            conn.execute(
                "INSERT INTO events (id, upload_id, file_ids, timestamp, attributes, treat_as_auth_device) VALUES (?, ?, ?, ?, ?, 1)",
                (
                    "ev-hw-1",
                    upload_id,
                    json.dumps([file_id]),
                    1700010000.0,
                    json.dumps(attrs_hw),
                ),
            )
            conn.execute(
                "INSERT INTO events (id, upload_id, file_ids, timestamp, attributes, treat_as_auth_device) VALUES (?, ?, ?, ?, ?, 1)",
                (
                    "ev-hw-2",
                    upload_id,
                    json.dumps([file_id]),
                    1700020000.0,
                    json.dumps(attrs_hw),
                ),
            )

            # 3. Different model events to create a second profile
            attrs_prof = {
                "norm__manufacturer": "Samsung",
                "norm__model_name": "Galaxy S22",
                "norm__os_name": "Android",
                "norm__client_name": "Chrome",
                "norm__client_version": "100.0",
                "norm__os_version": "12.0",
                "device_serial_number": "SN-PROF1",
            }
            conn.execute(
                "INSERT INTO events (id, upload_id, file_ids, timestamp, attributes, treat_as_auth_device) VALUES (?, ?, ?, ?, ?, 1)",
                (
                    "ev-prof-1",
                    upload_id,
                    json.dumps([file_id]),
                    1700030000.0,
                    json.dumps(attrs_prof),
                ),
            )

            conn.commit()

        # Run the grouping pipeline
        group(upload_id, db_path=test_db_path)

        # Validate outputs in SQLite
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            # Check edge tables (Deduplication and Hardware matching)
            edges = conn.execute("SELECT * FROM device_instance_edges").fetchall()
            assert len(edges) >= 2
            edge_types = {e["type"] for e in edges}
            assert "Deduplication" in edge_types
            assert "Hardware" in edge_types

            # Verify device_instances are created
            instances = conn.execute("SELECT * FROM device_instances").fetchall()
            assert len(instances) >= 2
            inst_ids = {i["id"] for i in instances}

            # Verify mapping tables are populated
            inst_events = conn.execute(
                "SELECT * FROM device_instance_events"
            ).fetchall()
            assert (
                len(inst_events) >= 3
            )  # ev-dup-1 (representative), ev-hw-1 & ev-hw-2 (merged), ev-prof-1

            # Verify profiles are populated
            profiles = conn.execute("SELECT * FROM device_profiles_v2").fetchall()
            assert len(profiles) >= 2  # Apple iPhone 13, and Samsung Galaxy S22

            # Check profile instances links
            prof_insts = conn.execute(
                "SELECT * FROM device_profile_instances"
            ).fetchall()
            assert len(prof_insts) >= 2

    @pytest.mark.parametrize("order", [("A", "B"), ("B", "A")])
    def test_multi_upload_order_independence(self, test_db_path, order):
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "..", "schema.sql"
        )
        if os.path.exists(test_db_path):
            os.remove(test_db_path)

        uploads_data = {
            "A": {
                "id": "upload-A",
                "event_id": "ev-A",
                "attrs": {
                    "norm__manufacturer": "Google",
                    "norm__model_name": "Pixel 6",
                    "norm__os_name": "Android",
                    "norm__client_name": "Google App",
                },
            },
            "B": {
                "id": "upload-B",
                "event_id": "ev-B",
                "attrs": {
                    "norm__manufacturer": "Google",
                    "norm__model_name": "Pixel 6",
                    "norm__os_name": "Android",
                    "norm__client_name": "Facebook App",
                },
            },
        }

        for upload_name in order:
            data = uploads_data[upload_name]
            with DatabaseSession(test_db_path, schema_path=schema_path) as conn:
                conn.execute(
                    "INSERT INTO uploads (id, platform, given_name) VALUES (?, ?, ?)",
                    (data["id"], "test", "given-" + data["id"]),
                )
                file_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO uploaded_files (id, upload_id, opfs_filename) VALUES (?, ?, ?)",
                    (file_id, data["id"], "file_" + data["id"] + ".json"),
                )
                conn.execute(
                    "INSERT INTO events (id, upload_id, file_ids, timestamp, attributes, treat_as_auth_device) VALUES (?, ?, ?, ?, ?, 1)",
                    (
                        data["event_id"],
                        data["id"],
                        json.dumps([file_id]),
                        1700000000.0,
                        json.dumps(data["attrs"]),
                    ),
                )
                conn.commit()

            group(data["id"], db_path=test_db_path)

        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            profiles = conn.execute("SELECT * FROM device_profiles_v2").fetchall()
            assert len(profiles) == 1
            assert profiles[0]["manufacturer"] == "Google"
            assert profiles[0]["model"] == "Pixel 6"

            mappings = conn.execute("SELECT * FROM device_profile_instances").fetchall()
            assert len(mappings) == 2
            profile_id = profiles[0]["id"]
            assert mappings[0]["device_profile_id"] == profile_id
            assert mappings[1]["device_profile_id"] == profile_id
