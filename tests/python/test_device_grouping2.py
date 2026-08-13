import os
import json
import uuid
from db_session import DatabaseSession
from device_grouping2.worker import group


class TestDeviceGrouping2:
    """Test device_grouping2 pipeline and its DB outputs."""

    def test_group_pipeline_outputs(self, test_db_path):
        upload_id = "test-grouping2-" + uuid.uuid4().hex
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "..", "schema.sql"
        )

        with DatabaseSession(test_db_path, schema_path=schema_path) as conn:
            conn.execute(
                "INSERT INTO uploads (id, platform, given_name) VALUES (?, ?, ?)",
                (upload_id, "test", "test-group-2"),
            )

            file_id = uuid.uuid4().hex
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
            edges = conn.execute("SELECT * FROM device_group_edges").fetchall()
            assert len(edges) >= 2
            edge_types = {e["type"] for e in edges}
            assert "Deduplication" in edge_types
            assert "Hardware" in edge_types

            # Verify device_groups are created
            groups = conn.execute("SELECT * FROM device_groups").fetchall()
            assert len(groups) >= 2
            inst_ids = {i["id"] for i in groups}

            # Verify mapping tables are populated
            inst_events = conn.execute(
                "SELECT * FROM device_group_events"
            ).fetchall()
            assert (
                len(inst_events) >= 3
            )  # ev-dup-1 (representative), ev-hw-1 & ev-hw-2 (merged), ev-prof-1

    # test_multi_upload_order_independence was removed: it verified that
    # cross-upload device-profile merging was order-independent, but that
    # behavior no longer exists now that device profile computation
    # (device_profiles_v2 / device_profile_groups) was deprecated and
    # removed along with the underlying tables.
