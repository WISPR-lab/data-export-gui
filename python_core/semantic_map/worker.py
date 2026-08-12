import json
from itertools import groupby
import uuid
import traceback
from manifest import Manifest
from db_session import DatabaseSession
import semantic_map.views as sm_views
import semantic_map.action_message_builder as sm_amb
from semantic_map.deduplicate_events import deduplicate_events
from python_core.logger import get_logger

logger = get_logger("semantic_map")


def _generate_table_rows(cursor_rows: list, manifest: Manifest, upload_id):
    event_rows = []
    auth_device_rows = []

    for manifest_file_id, group in groupby(cursor_rows, key=lambda x: x[3]):
        group_list = list(group)
        views = manifest.views(manifest_file_id)
        if not views:
            logger.warning("No manifest views found for file ID '%s'", manifest_file_id)
            continue

        # `where` filters and `static` fields are invariant per view — compile them
        # once per file group instead of rebuilding on every record below.
        compiled_views = sm_views.compile_views(views)

        for raw_data_id, file_id, raw_data, _manifest_file_id in group_list:
            try:
                record = json.loads(raw_data)
            except Exception as e:
                logger.warning("JSON parse error for raw_data_id %s: %s", raw_data_id, e)
                continue

            if not isinstance(record, dict):
                logger.warning("Expected dict after JSON parse for raw_data_id %s in %s (got %s). Skipping.", raw_data_id, file_id, type(record).__name__)
                continue

            view_indices = list(
                sm_views.view_indexes_to_apply(record, views, compiled_views)
            )

            for vindex in view_indices:
                cv = compiled_views[vindex]
                fields = sm_views.fields(record, cv.view, static=cv.static)
                event_kind = fields.pop("event_kind", None)

                shared = {
                    "id": uuid.uuid4().hex,
                    "upload_id": upload_id,
                    "file_ids": [file_id],
                    "raw_data_ids": [raw_data_id],
                }

                # EVENTS
                if event_kind == "event":
                    event_action = fields.pop("event_action", None)
                    event_category = fields.pop("event_category", [])
                    event_type = fields.pop("event_type", [])

                    event_rows.append(
                        shared
                        | {
                            "timestamp": fields.pop("timestamp", None),
                            "event_action": event_action,
                            "event_kind": event_kind,
                            "event_category": event_category,
                            "event_type": event_type,
                            "event_type_msg": sm_amb.message(event_action, **fields),
                            "attributes": fields,
                            "deduplicated": False,  # taken care of in deduplication step
                            "extra_timestamps": [],  # ^^
                        }
                    )

                # AUTH/DEVICE ENTITIES
                elif event_kind == "asset" or event_kind == "entity":
                    entity_type = fields.pop("entity_type", None)
                    # Pop event_category and event_type from fields before storing as attributes
                    fields.pop("event_category", [])
                    fields.pop("event_type", [])
                    if entity_type in (
                        "authenticated_device",
                        "trusted_cookie",
                        "session",
                        "app_registration",
                        "hardware_registration",
                        "passkey_registration",
                        "platform_inferred_device",
                    ):
                        auth_device_rows.append(
                            {
                                "id": uuid.uuid4().hex,
                                "upload_id": upload_id,
                                "file_id": file_id,
                                "raw_data_id": raw_data_id,
                                "entity_type": entity_type,
                                "event_kind": event_kind,
                                "attributes": fields,
                            }
                        )
                else:
                    logger.warning("Unhandled event_kind '%s' for raw_data_id %s", event_kind, raw_data_id)
                    continue

    return event_rows, auth_device_rows  # add more as we create more tables


def _stringify(rows: list[dict]) -> list[dict]:
    list_keys = [
        "raw_data_ids",
        "file_ids",
        "extra_timestamps",
        "event_category",
        "event_type",
    ]
    dict_keys = ["attributes"]
    for r in rows:
        for k in list_keys:
            if k in r:
                r[k] = (
                    json.dumps(r[k])
                    if isinstance(r[k], (list, dict))
                    else json.dumps([])
                )
        for k in dict_keys:
            if k in r:
                r[k] = (
                    json.dumps(r[k])
                    if isinstance(r[k], (list, dict))
                    else json.dumps({})
                )
    return rows


def map(platform: str, upload_id: str, db_path: str = None, manifest: Manifest = None):

    try:
        manifest = manifest or Manifest(platform=platform)

        with DatabaseSession(db_path) as conn:
            cursor = conn.execute(
                """
                SELECT 
                    r.id, 
                    r.file_id, 
                    r.data, 
                    f.manifest_file_id
                FROM raw_data r
                JOIN uploaded_files f ON r.file_id = f.id
                WHERE r.upload_id = ?
                ORDER BY f.manifest_file_id ASC, r.id ASC
                """,
                (upload_id,),
            )

            if cursor is None:
                raise RuntimeError("Database cursor is None after execute()")

            rows = cursor.fetchall()
            if not rows:
                logger.warning("No raw_data found for upload_id: %s", upload_id)
                return

            event_rows, auth_device_rows = _generate_table_rows(
                rows, manifest, upload_id
            )

            event_rows = deduplicate_events(event_rows)
            event_rows = _stringify(event_rows)
            auth_device_rows = _stringify(auth_device_rows)

            if event_rows:
                conn.executemany(
                    """
                    INSERT INTO events (id, upload_id, file_ids, raw_data_ids, timestamp, event_action, event_kind, event_category, event_type, event_type_msg, attributes, deduplicated, extra_timestamps)
                    VALUES (:id, :upload_id, :file_ids, :raw_data_ids, :timestamp, :event_action, :event_kind, :event_category, :event_type, :event_type_msg, :attributes, :deduplicated, :extra_timestamps)
                    """,
                    event_rows,
                )

            if auth_device_rows:
                conn.executemany(
                    """
                    INSERT INTO devices_raw (id, upload_id, file_id, raw_data_id, entity_type, event_kind, attributes)
                    VALUES (:id, :upload_id, :file_id, :raw_data_id, :entity_type, :event_kind, :attributes)
                    """,
                    auth_device_rows,
                )

            conn.commit()
            logger.info("Mapped %d events and %d auth devices", len(event_rows), len(auth_device_rows))

    except Exception as e:
        logger.error("Fatal Database Error: %s: %s", type(e).__name__, e)
        traceback.print_exc()
        return


def get_counts(upload_id):
    import builtins

    with DatabaseSession(builtins.DB_PATH, use_dict_factory=True) as conn:
        events_count = conn.execute(
            "SELECT COUNT(*) as count FROM events WHERE upload_id = ?", (upload_id,)
        ).fetchone()["count"]

        devices_count = conn.execute(
            "SELECT COUNT(*) as count FROM devices_raw WHERE upload_id = ?",
            (upload_id,),
        ).fetchone()["count"]

        return {
            "status": "success",
            "events_count": events_count,
            "devices_count": devices_count,
        }
