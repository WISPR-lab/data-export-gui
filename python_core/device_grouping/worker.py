from datetime import datetime, timezone
import json

from db_session import DatabaseSession
from device_grouping.hard_merge import hard_merge_single_upload, hard_merge_multi_upload, format_rows as format_hard_rows
from device_grouping.soft_merge import soft_merge_single_upload, soft_merge_multi_upload, format_rows as format_soft_rows
from device_grouping.computed_fields import compute_device_profile_fields
from device_grouping.event_assoc import associate_events_to_devices


def _get_config_value(name):
    import builtins
    if not hasattr(builtins, name):
        raise ValueError(f"Config value '{name}' not found in builtins.")
    return getattr(builtins, name)



def group(upload_id: str, db_path: str = None) -> None:
    db_path = db_path or _get_config_value('DB_PATH')

    with DatabaseSession(db_path, use_dict_factory=True, json_columns=['attributes', 'origins', 'upload_ids', 'file_ids', 'devices_raw_ids', 'atomic_devices_ids', 'tags', 'labels']) as conn:

        # ------------------------------------------------------------------ #
        # PASS 1: hard-merge devices_raw --> atomic_devices           #
        # ------------------------------------------------------------------ #
        devices_raw_rows = conn.execute(
            'SELECT * FROM devices_raw'
        ).fetchall()

        if not devices_raw_rows:
            print(f"[DeviceGrouping] No devices_raw rows in database")
            return



        uploads_count = conn.execute('SELECT COUNT(*) as count FROM uploads').fetchone()['count']
        print(f"[DeviceGrouping] Existing uploads: {uploads_count}") 

        if uploads_count > 1:  # if we've already uploaded stuff
            atomic_devices_rows = conn.execute(
                'SELECT * FROM atomic_devices'
            ).fetchall()
            
            rows = hard_merge_multi_upload(devices_raw_rows, atomic_devices_rows)
        else: # if this is the first upload
            rows = hard_merge_single_upload(devices_raw_rows)

        for row in format_hard_rows(rows):
            conn.execute(
                '''INSERT OR REPLACE INTO atomic_devices 
                   (id, attributes, origins, upload_ids, file_ids, devices_raw_ids, specificity)
                   VALUES (:id, :attributes, :origins, :upload_ids, :file_ids, :devices_raw_ids, :specificity)''',
                row
            )

        print(f"[DeviceGrouping] Pass 1: upserted {len(rows)} atomic_devices")


        # ------------------------------------------------------------------ #
        # PASS 2: soft-merge atomic_devices --> device_profiles                  #
        # ------------------------------------------------------------------ #

        atomic_devices_rows = conn.execute('SELECT * FROM atomic_devices').fetchall()
        
        if uploads_count > 1:
            new_atomic_device_rows = [r for r in atomic_devices_rows if upload_id in (r.get('upload_ids', []) or [])]
            existing_profile_rows = conn.execute('SELECT * FROM device_profiles').fetchall()
            rows = soft_merge_multi_upload(new_atomic_device_rows, existing_profile_rows, atomic_devices_rows)
        else: 
            rows = soft_merge_single_upload(atomic_devices_rows)

        device_group_rows = format_soft_rows(rows)
        ts = datetime.now(timezone.utc).timestamp()
        for row in device_group_rows:
            row['created_at'] = ts
            row['updated_at'] = ts
        
        conn.executemany(
            """INSERT OR REPLACE INTO device_profiles
               (id, atomic_devices_ids, attributes, specificity, model, manufacturer, origins, system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
               VALUES (:id, :atomic_devices_ids, :attributes, :specificity, :model, :manufacturer, :origins, :system_soft_merge, :is_generic, :user_label, :notes, :tags, :labels, :created_at, :updated_at)""",
            device_group_rows
        )
        print(f"[DeviceGrouping] Pass 2: upserted {len(device_group_rows)} device_profiles")


        # ------------------------------------------------------------------ #
        # PASS 3: associate events to atomic devices                         #
        # ------------------------------------------------------------------ #

        events_rows = conn.execute(
            'SELECT id, upload_id, attributes FROM events WHERE upload_id = ?',
            (upload_id,)
        ).fetchall()

        if events_rows and atomic_devices_rows:
            associations = associate_events_to_devices(events_rows, atomic_devices_rows)
            
            if associations:
                conn.executemany(
                    """INSERT OR REPLACE INTO events_assoc
                       (event_id, atomic_device_id, match_reason, event_specificity)
                       VALUES (:event_id, :atomic_device_id, :match_reason, :event_specificity)""",
                    associations
                )
                print(f"[DeviceGrouping] Pass 3: created {len(associations)} event associations")
            else:
                print(f"[DeviceGrouping] Pass 3: no events matched to devices")
        else:
            print(f"[DeviceGrouping] Pass 3: skipped (no events or no devices)")

        conn.commit()
        print(f"[DeviceGrouping] Done for upload_id={upload_id}")
