from datetime import datetime, timezone
import json
import pandas as pd

from db_session import DatabaseSession
from . import deterministic_ids
from . import client_os_upgrades
from .instances import DeviceInstanceGraph
from .resolved_sessions_registrations import resolve
from . import profiles

from python_core.utils.pyodide_utils import get_config_value


def group(upload_id: str, db_path: str = None) -> None:
    db_path = db_path or get_config_value("DB_PATH")
    json_columns = [
        "attributes",
        "origins",
        "upload_ids",
        "file_ids",
        "devices_raw_ids",
        # "atomic_devices_ids",
        "tags",
        "labels",
    ]

    with DatabaseSession(
        db_path, use_dict_factory=True, json_columns=json_columns
    ) as conn:
        events_df, devices_df = _deduplicate_and_fetch_inputs(conn, upload_id)
        if events_df.empty and devices_df.empty:
            return

        # df = DeviceInstanceGraph.format_initial(events_df, devices_df)
        df = DeviceInstanceGraph.format_initial(events_df, devices_df.head(0)) # removing devices_raw for now

        identity_edges = deterministic_ids.get_edges(df)
        if not identity_edges.empty:
            identity_edges["upload_id"] = upload_id
            conn.executemany(
                "INSERT OR IGNORE INTO device_instance_edges (id_a, id_b, type, provenance, upload_id) VALUES (?, ?, ?, ?, ?)",
                identity_edges[
                    ["id_a", "id_b", "type", "provenance", "upload_id"]
                ].values.tolist(),
            )

        upgrade_edges = client_os_upgrades.get_edges(df[df["table"] == "events"])
        if not upgrade_edges.empty:
            upgrade_edges["upload_id"] = upload_id
            conn.executemany(
                "INSERT OR IGNORE INTO device_instance_edges (id_a, id_b, type, provenance, upload_id) VALUES (?, ?, ?, ?, ?)",
                upgrade_edges[
                    ["id_a", "id_b", "type", "provenance", "upload_id"]
                ].values.tolist(),
            )
        conn.commit()

        instances = _build_device_instances(conn, df)

        ts = datetime.now(timezone.utc).timestamp()
        _write_device_instances(conn, instances, ts)

        _write_device_profiles(conn, instances, ts)

        conn.execute("DELETE FROM resolved_sessions_registrations WHERE upload_id = ?", (upload_id,))
        raw_rows = conn.execute(
            "SELECT id, upload_id, entity_type, origin, attributes FROM devices_raw WHERE upload_id = ?",
            (upload_id,),
        ).fetchall()
        resolved_sessions_registration_rows = resolve(raw_rows)

        if not resolved_sessions_registration_rows:
            print(f"No resolved sessions or registrations found for upload_id: {upload_id}")
        else:
            conn.executemany(
                """
                INSERT INTO resolved_sessions_registrations (
                    id, upload_id, entity_type, origin, model_name, client_name, 
                    os_name, os_version, os_type, attributes, is_reduced_ua, 
                    has_trusted_cookie, trusted_cookie_id, has_passkey, registration_device
                ) VALUES (
                    :id, :upload_id, :entity_type, :origin, :model_name, :client_name, 
                    :os_name, :os_version, :os_type, :attributes, :is_reduced_ua, 
                    :has_trusted_cookie, :trusted_cookie_id, :has_passkey, :registration_device
                )
                """,
                resolved_sessions_registration_rows
            )

        conn.commit()


def _deduplicate_and_fetch_inputs(
    conn, upload_id: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    conn.execute(
        """INSERT OR IGNORE INTO device_instance_edges (id_a, id_b, type, provenance, upload_id)
           WITH Ranked AS (
               SELECT id, MIN(id) OVER(PARTITION BY attributes, timestamp) as id_a
               FROM events WHERE upload_id = ? AND treat_as_auth_device = 1
           )
           SELECT id_a, id, 'Deduplication', '{"reason": "identical event metadata"}', ?
           FROM Ranked WHERE id != id_a;""",
        (upload_id, upload_id),
    )
    conn.commit()

    events_rows = conn.execute(
        """SELECT e.id, e.upload_id, e.attributes, e.origin, e.timestamp, e.treat_as_auth_device, u.platform
           FROM events e
           JOIN uploads u ON e.upload_id = u.id
           WHERE e.upload_id = ?
           AND e.treat_as_auth_device = 1
           AND e.id IN (
               SELECT MIN(id)
               FROM events
               WHERE upload_id = ?
               AND treat_as_auth_device = 1
               GROUP BY attributes, timestamp
           )""",
        (upload_id, upload_id),
    ).fetchall()

    devices_rows = conn.execute(
        """SELECT d.id, d.upload_id, d.attributes, d.origin, u.platform
           FROM devices_raw d
           JOIN uploads u ON d.upload_id = u.id
           WHERE d.upload_id = ?""",
        (upload_id,),
    ).fetchall()

    return pd.DataFrame(events_rows), pd.DataFrame(devices_rows)


def _build_device_instances(conn, df: pd.DataFrame) -> list:
    vertex_ids = df["id"].tolist()
    placeholders = ",".join("?" for _ in vertex_ids)

    edges_rows = conn.execute(
        f"""SELECT id_a, id_b, type FROM device_instance_edges 
            WHERE id_a IN ({placeholders}) OR id_b IN ({placeholders})""",
        vertex_ids + vertex_ids,
    ).fetchall()

    graph = DeviceInstanceGraph(df, pd.DataFrame(edges_rows))
    return graph.get_instances()


def _write_device_instances(conn, instances: list, ts: float) -> None:
    instance_ids = [inst.root_id for inst in instances]
    if not instance_ids:
        return

    inst_placeholders = ",".join("?" for _ in instance_ids)
    conn.execute(
        f"DELETE FROM device_instances WHERE id IN ({inst_placeholders})", instance_ids
    )

    for inst in instances:
        export_data = inst.export_as_dict()
        export_data["created_at"] = ts
        for list_col in ["os_versions", "client_versions", "client_ips", "locations"]:
            export_data[list_col] = json.dumps(export_data[list_col])

        conn.execute(
            """INSERT INTO device_instances 
               (id, upload_id, platform, manufacturer, model, client_name, os_name, os_type, apple_masking, 
                first_seen, last_seen, last_seen_dt, event_count, latest_os_version, latest_client_version, 
                latest_client_ip, os_versions, client_versions, client_ips, locations, created_at)
               VALUES (:id, :upload_id, :platform, :manufacturer, :model, :client_name, :os_name, :os_type, :apple_masking, 
                       :first_seen, :last_seen, :last_seen_dt, :event_count, :latest_os_version, :latest_client_version, 
                       :latest_client_ip, :os_versions, :client_versions, :client_ips, :locations, :created_at)""",
            export_data,
        )

        events_mapping = [
            (inst.root_id, vid) for vid in inst.df[inst.df["table"] == "events"]["id"]
        ]
        if events_mapping:
            conn.executemany(
                "INSERT OR IGNORE INTO device_instance_events (device_instance_id, event_id) VALUES (?, ?)",
                events_mapping,
            )

        devices_mapping = [
            (inst.root_id, vid)
            for vid in inst.df[inst.df["table"] == "devices_raw"]["id"]
        ]
        if devices_mapping:
            conn.executemany(
                "INSERT OR IGNORE INTO device_instance_raw_devices (device_instance_id, devices_raw_id) VALUES (?, ?)",
                devices_mapping,
            )


def _write_device_profiles(conn, instances: list, ts: float) -> None:
    existing_instances = conn.execute(
        "SELECT id, manufacturer, model, os_type FROM device_instances"
    ).fetchall()
    existing_mappings = conn.execute(
        "SELECT device_profile_id, device_instance_id FROM device_profile_instances"
    ).fetchall()

    device_profiles_v2_rows, device_profile_instances_rows = (
        profiles.calculate_profile_updates(
            instances, existing_instances, existing_mappings, ts
        )
    )

    if device_profiles_v2_rows:
        conn.executemany(
            """INSERT INTO device_profiles_v2 (id, manufacturer, model, os_type, created_at, updated_at) 
               VALUES (:id, :manufacturer, :model, :os_type, :created_at, :updated_at)""",
            device_profiles_v2_rows,
        )
    if device_profile_instances_rows:
        conn.executemany(
            """INSERT OR IGNORE INTO device_profile_instances (device_profile_id, device_instance_id) 
               VALUES (:device_profile_id, :device_instance_id)""",
            device_profile_instances_rows,
        )
