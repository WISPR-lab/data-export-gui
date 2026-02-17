import os
import cfg
import sys
import json
from itertools import groupby
import uuid


from manifest import Manifest
from database.db_session import DatabaseSession
import semantic_map.map_utils as map_utils
import semantic_map.action_message_builder as amb
from semantic_map.deduplicate_events import deduplicate_events





def _generate_table_rows(cursor_rows: list, manifest: Manifest, upload_id):
    # rows to add to tables
    event_rows = []
    auth_device_rows = []
    # add more as we create more tables?

    for manifest_file_id, group in groupby(cursor_rows, key=lambda x: x[3]):
        views = manifest.views(manifest_file_id)
        if not views:
            print(f"[SemanticMapWorker] No views for manifest_file_id: {manifest_file_id}")
            continue

        for (raw_data_id, file_id, raw_data) in group:
            try:
                record = json.loads(raw_data)
            except Exception as e:
                print(f"[SemanticMapWorker] JSON parse error for raw_data_id {raw_data_id}: {e}")
                continue
            
            for vindex in map_utils.view_indexes_to_apply(record, views):
                fields = map_utils.fields(record, views[vindex])
                event_kind = fields.pop("event_kind", None)
                
                shared = {
                    "id": str(uuid.uuid4()), 
                    "upload_id": upload_id, 
                    "file_ids": [file_id], 
                    "raw_data_ids": [raw_data_id]
                }

                # EVENTS
                if event_kind == "event":
                    event_action = fields.pop('event_action', None)
                    event_rows.append(shared | {
                        "timestamp": fields.pop('timestamp', None),
                        "event_action": event_action,
                        "event_kind": event_kind,
                        "message": amb.message(event_action, **fields),
                        "attributes": fields,
                        "deduplicated": False,  # taken care of in deduplication step
                        "extra_timestamps": []  # ^^
                    })
                
                # AUTH/DEVICE ENTITIES
                elif event_kind == "asset" or event_kind == "entity":
                    entity_type = fields.pop('entity_type', None)
                    if entity_type == "authenticated_device":
                        auth_device_rows.append(shared | {
                            "entity_type": entity_type,
                            "event_kind": event_kind,
                            "attributes": fields
                        })
                else: 
                    print(f"[SemanticMapWorker] Unhandled event_kind '{event_kind}' for raw_data_id {raw_data_id}") 
                    continue
    
    return event_rows, auth_device_rows  # add more as we create more tables


def _stringify(rows: list[dict]) -> list[dict]:
    keys = ["raw_data_ids", "file_ids", "extra_timestamps", "attributes"] # add more as needed
    for r in rows:
        for k in keys:
            if k in r and isinstance(r[k], (list, dict)):
                r[k] = json.dumps(r[k])
            elif k in r and r[k] is None:
                r[k] = json.dumps([]) if k != "attributes" else json.dumps({})
    return rows


def map(platform, 
        upload_id, 
        db_path=cfg.DB_PATH, 
        manifest_dir=cfg.MANIFESTS_DIR):

    print(f"[SemanticMapWorker] Starting mapping for upload_id: {upload_id}")

    try:
        manifest = Manifest(platform=platform, manifest_dir=manifest_dir)
        schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
        
        with DatabaseSession(db_path, schema_path) as conn:
            
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
                ORDER BY r.id ASC
                """,
                (upload_id,)
            )
            rows = cursor.fetchall()
            if not rows:
                print(f"[SemanticMapWorker] No raw_data found for upload_id: {upload_id}")
                return
            
            event_rows, auth_device_rows = _generate_table_rows(rows, manifest, upload_id)
            event_rows = deduplicate_events(event_rows)
            event_rows = _stringify(event_rows)
            auth_device_rows = _stringify(auth_device_rows)
            

            # Insert into events table
            conn.executemany(
                """
                INSERT INTO events (id, upload_id, file_ids, raw_data_ids, timestamp, event_action, event_kind, message, attributes, deduplicated, extra_timestamps)
                VALUES (:id, :upload_id, :file_ids, :raw_data_ids, :timestamp, :event_action, :event_kind, :message, :attributes, :deduplicated, :extra_timestamps)
                """,
                event_rows
            )

            # Insert into auth_device table
            conn.executemany(
                """
                INSERT INTO auth_device (id, upload_id, file_ids, raw_data_ids, entity_type, event_kind, attributes)
                VALUES (:id, :upload_id, :file_ids, :raw_data_ids, :entity_type, :event_kind, :attributes)
                """,
                auth_device_rows
            )

            conn.commit()
            print(f"[SemanticMapWorker] Mapping completed for upload_id: {upload_id}. Inserted {len(event_rows)} events and {len(auth_device_rows)} auth/device entities.")


                    
    except Exception as e:
        print(f"[SemanticMapWorker] Fatal Database Error: {e}") # TODO better error handling
        return

