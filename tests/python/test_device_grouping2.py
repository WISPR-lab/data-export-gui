import os
import json
import uuid
import pandas as pd
from db_session import DatabaseSession
from device_grouping2.worker import group
from device_grouping2 import client_os_upgrades
from device_grouping2.graph import DeviceGroupGraph


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


class TestDeviceGroupGraphUnionFind:
    """Unit tests for DeviceGroupGraph's union-find (graph.py)."""

    def _vertices(self, ids):
        n = len(ids)
        return pd.DataFrame({
            "id": ids,
            "timestamp": range(n),
            "table": ["events"] * n,
            "upload_id": ["u"] * n,
            "platform": ["facebook"] * n,
        })

    def test_star_topology_does_not_crash(self):
        # One anchor edged to thousands of others in sequence used to build an O(n)-deep parent
        # chain and blow Python's recursion limit in a recursive, rank-less _find/_union.
        n = 5000
        ids = [f"r{i}" for i in range(n)]
        edges = pd.DataFrame({
            "id_a": ["r0"] * (n - 1),
            "id_b": ids[1:],
            "type": ["Session"] * (n - 1),
        })
        groups = DeviceGroupGraph(self._vertices(ids), edges).get_groups()
        assert len(groups) == 1
        assert len(groups[0].df) == n

    def test_disjoint_groups_stay_separate(self):
        ids = [f"r{i}" for i in range(6)]
        edges = pd.DataFrame({
            "id_a": ["r0", "r1", "r3"],
            "id_b": ["r1", "r2", "r4"],
            "type": ["Session"] * 3,
        })
        groups = DeviceGroupGraph(self._vertices(ids), edges).get_groups()
        sizes = sorted(len(g.df) for g in groups)
        assert sizes == [1, 2, 3]  # {r0,r1,r2}, {r3,r4}, {r5}


class TestClientOsUpgrades:
    """Unit tests for the ClientUpgrade pass-1 edge logic in client_os_upgrades.py."""

    BASE_ATTRS = {
        "attr__norm__manufacturer": "Apple",
        "attr__norm__model_name": "iPhone 13",
        "attr__norm__os_name": "iOS",
        "attr__norm__os_version": "16.0",
        "attr__norm__client_name": "Safari",
    }

    def _row(self, id_, ts, client_version):
        return {
            "id": id_,
            "timestamp": pd.Timestamp(ts, unit="s", tz="UTC"),
            "attr__norm__client_version": client_version,
            **self.BASE_ATTRS,
        }

    def test_null_client_version_does_not_form_edge(self):
        """Two records with identical hardware/OS specs but no client_version on
        either side must NOT be linked -- there's no version evidence to verify
        an upgrade against, so this should be treated like any other missing
        required field rather than silently passing through."""
        df = pd.DataFrame(
            [
                self._row("a", 1_700_000_000, None),
                self._row("b", 1_700_010_000, None),
            ]
        )
        edges, _ = client_os_upgrades._valid_client_upgrade(df)
        assert edges.empty

    def test_one_sided_null_client_version_does_not_form_edge(self):
        df = pd.DataFrame(
            [
                self._row("a", 1_700_000_000, "16.0"),
                self._row("b", 1_700_010_000, None),
            ]
        )
        edges, _ = client_os_upgrades._valid_client_upgrade(df)
        assert edges.empty

    def test_valid_client_version_upgrade_still_forms_edge(self):
        """Sanity check the fix doesn't regress the normal upgrade case."""
        df = pd.DataFrame(
            [
                self._row("a", 1_700_000_000, "16.0"),
                self._row("b", 1_700_010_000, "16.1"),
            ]
        )
        edges, _ = client_os_upgrades._valid_client_upgrade(df)
        assert len(edges) == 1
        assert set(edges.iloc[0][["id_a", "id_b"]]) == {"a", "b"}
