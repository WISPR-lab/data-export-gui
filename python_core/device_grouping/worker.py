from datetime import datetime, timezone
import json

from db_session import DatabaseSession
from device_grouping.hard_merge import hard_merge_single_upload, hard_merge_multi_upload, format_rows as format_hard_rows
from device_grouping.soft_merge import soft_merge_single_upload, soft_merge_multi_upload_increment, format_rows as format_soft_rows


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
            # Multi-upload: incremental soft merge
            # New atomics are those from this upload
            new_atomics = [r for r in atomic_devices_rows if upload_id in (r.get('upload_ids', []) or [])]
            
            # Get existing profiles and build atomic lookup
            existing_profiles = conn.execute('SELECT * FROM device_profiles').fetchall()
            all_atomics = {r['id']: r for r in atomic_devices_rows}
            
            # Run incremental soft merge
            result = soft_merge_multi_upload_increment(new_atomics, existing_profiles, all_atomics)
            
            # Update existing profiles with new atomics
            profiles_to_update = result['profiles_to_update']
            for profile_id, new_atomic_ids_to_add in profiles_to_update.items():
                existing_profile = next((p for p in existing_profiles if p['id'] == profile_id), None)
                if existing_profile:
                    current_ids = existing_profile.get('atomic_devices_ids', [])
                    merged_ids = sorted(list(set(current_ids + new_atomic_ids_to_add)))
                    conn.execute(
                        '''UPDATE device_profiles SET atomic_devices_ids = :atomic_devices_ids, updated_at = :updated_at 
                           WHERE id = :id''',
                        {'id': profile_id, 'atomic_devices_ids': json.dumps(merged_ids), 'updated_at': datetime.now(timezone.utc).timestamp()}
                    )
            
            # Insert new profiles
            new_profiles = result['new_profiles']
            device_group_rows = format_soft_rows(new_profiles)
            ts = datetime.now(timezone.utc).timestamp()
            for row in device_group_rows:
                row['created_at'] = ts
                row['updated_at'] = ts
            
            if device_group_rows:
                conn.executemany(
                    """INSERT INTO device_profiles
                       (id, atomic_devices_ids, system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
                       VALUES (:id, :atomic_devices_ids, :system_soft_merge, :is_generic, :user_label, :notes, :tags, :labels, :created_at, :updated_at)""",
                    device_group_rows
                )
                print(f"[DeviceGrouping] Pass 2: inserted {len(device_group_rows)} new profiles, updated {len(profiles_to_update)} existing profiles")
            else:
                print(f"[DeviceGrouping] Pass 2: updated {len(profiles_to_update)} existing profiles, no new profiles")
        else: 
            # Single upload: standard soft merge
            profiles = soft_merge_single_upload(atomic_devices_rows)
            device_group_rows = format_soft_rows(profiles)
            ts = datetime.now(timezone.utc).timestamp()
            for row in device_group_rows:
                row['created_at'] = ts
                row['updated_at'] = ts
            
            conn.executemany(
                """INSERT INTO device_profiles
                   (id, atomic_devices_ids, system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
                   VALUES (:id, :atomic_devices_ids, :system_soft_merge, :is_generic, :user_label, :notes, :tags, :labels, :created_at, :updated_at)""",
                device_group_rows
            )
            print(f"[DeviceGrouping] Pass 2: inserted {len(device_group_rows)} device_profiles")

        conn.commit()
        print(f"[DeviceGrouping] Done for upload_id={upload_id}")
