import json
from db_session import DatabaseSession
from field_normalization.user_agent import UserAgentParser
from field_normalization.device import normalize_device_fields
from field_normalization.geo import normalize_geo_fields
from field_normalization.origin import determine_origin
from field_normalization.auth_related_events import treat_event_as_auth_device
from python_core.utils.pyodide_utils import get_config_value


def _normalize(rows, platform, ua_parser, file_map, table=""):
    updates = []
    for row in rows:
        attrs = row["attributes"] or {}
        file_info = file_map.get(attrs.get("file_id"))
        if attrs.get("user_agent_original") or attrs.get("user_agent_os_full"):
            attrs.update(ua_parser.parse(attrs, file_info=file_info))
        origin = determine_origin(platform, attrs, file_info=file_info)
        attrs = normalize_geo_fields(attrs)
        attrs = normalize_device_fields(attrs)

        dct = {
            "id": row["id"],
            "attributes": json.dumps(attrs, sort_keys=True),
            "origin": origin,
        }
        if table == "events":
            dct["treat_as_auth_device"] = treat_event_as_auth_device(row)

        updates.append(dct)
    return updates


def normalize(upload_id: str, db_path: str = None) -> dict:
    db_path = db_path or get_config_value("DB_PATH")

    with DatabaseSession(
        db_path, use_dict_factory=True, json_columns=["attributes", "events_category"]
    ) as conn:
        print(
            f"[FieldNormalizeWorker] Starting normalization for upload_id={upload_id}"
        )

        # Get platform from uploads table
        upload = conn.execute(
            "SELECT platform FROM uploads WHERE id = ?", (upload_id,)
        ).fetchone()
        platform = upload["platform"] if upload else None

        uploaded_files = conn.execute(
            "SELECT id, manifest_file_id, manifest_filename FROM uploaded_files WHERE upload_id = ?",
            (upload_id,),
        ).fetchall()
        file_map = {uf["id"]: uf for uf in uploaded_files}

        ua_parser = UserAgentParser()

        # ----- devices raw normalization -------
        records_normalized = 0

        rows = conn.execute(
            """
            SELECT id, attributes
            FROM devices_raw
            WHERE upload_id = ?
            """,
            (upload_id,),
        ).fetchall()

        if rows:
            updates = _normalize(rows, platform, ua_parser, file_map, table="devices")
            conn.executemany(
                """
                UPDATE devices_raw
                SET attributes = :attributes, origin = :origin
                WHERE id = :id
                """,
                updates,
            )
            records_normalized += len(updates)
        else:
            print(
                f"[FieldNormalizeWorker] No devices_raw rows for upload_id={upload_id}"
            )

        # ----- events normalization -------

        print(f"[FieldNormalizeWorker] Normalizing events for upload_id={upload_id}")
        rows = conn.execute(
            """
            SELECT id, attributes, event_action as action, event_category as category
            FROM events
            WHERE upload_id = ?
            """,
            (upload_id,),
        ).fetchall()

        if rows:
            updates = _normalize(rows, platform, ua_parser, file_map, table="events")
            conn.executemany(
                """
                UPDATE events 
                SET attributes = :attributes, origin = :origin, treat_as_auth_device = :treat_as_auth_device
                WHERE id = :id
                """,
                updates,
            )
            records_normalized += len(updates)
        else:
            print(f"[FieldNormalizeWorker] No events rows for upload_id={upload_id}")

        conn.commit()

        print(f"[FieldNormalizeWorker] Normalization Complete")

        if records_normalized == 0:
            return {
                "status": "success",
                "message": "No records to normalize",
                "records_normalized": 0,
                "unique_uas_parsed": 0,
            }

        print(f"[normalize] Normalized {records_normalized} records")
        return {
            "status": "success",
            "message": f"Normalized {records_normalized} records",
            "records_normalized": records_normalized,
            "unique_uas_parsed": len(ua_parser._cache),
        }
