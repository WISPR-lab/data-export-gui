import json
import uuid
from datetime import datetime, timezone

from db_session import DatabaseSession
from device_grouping.hard_merge import hard_merge_one_upload, hard_merge_with_db, format_rows
from device_grouping.soft_merge import soft_merge
from device_grouping.specificity import specificity


def _get_config_value(name):
    import builtins
    if not hasattr(builtins, name):
        raise ValueError(f"Config value '{name}' not found in builtins.")
    return getattr(builtins, name)



def group(upload_id: str, db_path: str = None) -> None:
    db_path = db_path or _get_config_value('DB_PATH')

    with DatabaseSession(db_path, use_dict_factory=True) as conn:

        # ------------------------------------------------------------------ #
        # PASS 1: hard-merge devices_raw --> atomic_devices           #
        # ------------------------------------------------------------------ #
        devices_raw_rows = conn.execute(
            'SELECT * FROM devices_raw'
        ).fetchall()

        if not devices_raw_rows:
            print(f"[DeviceGrouping] No devices_raw rows in database")
            return

        for r in devices_raw_rows:
            if not r['attributes']:
                r['attributes'] = '{}'
            if isinstance(r['attributes'], str):
                try:
                    r['attributes'] = json.loads(r['attributes'])
                except json.JSONDecodeError:
                    print(f"[DeviceGrouping] Warning: invalid JSON in attributes for id={r['id']}")
                    r['attributes'] = {}



        uploads_count = conn.execute('SELECT COUNT(*) as count FROM uploads').fetchone()['count']
        print(f"[DeviceGrouping] Existing uploads: {uploads_count}") 

        if uploads_count > 1:  # if we've already uploaded stuff
            atomic_devices_rows = conn.execute(
                'SELECT * FROM atomic_devices'
            ).fetchall()
            for a in atomic_devices_rows:
                if isinstance(a['attributes'], str):
                    a['attributes'] = json.loads(a['attributes'])
            
            rows = hard_merge_with_db(devices_raw_rows, atomic_devices_rows)
        else: # if this is the first upload
            rows = hard_merge_one_upload(devices_raw_rows)

        for row in format_rows(rows):
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

        atomic_devices_rows = conn.execute(
            'SELECT * FROM atomic_devices'
        ).fetchall()

        atomic_devices_input = []
        for r in atomic_devices_rows:
            attrs = r.get('attributes', {})
            if isinstance(attrs, str):
                try:
                    attrs = json.loads(attrs)
                except json.JSONDecodeError:
                    attrs = {}
            atomic_devices_input.append({
                'id': r['id'],
                'attributes': attrs,
                'specificity': r.get('specificity', 1)
            })

        ts = datetime.now(timezone.utc).timestamp()
        device_group_rows = []
        for r in soft_merge(atomic_devices_input):
            device_group_rows.append({
                'id': r['id'],
                'atomic_devices_ids': r['atomic_devices_ids'],
                'initial_soft_merge': r['initial_soft_merge'],
                'soft_merge_flag_status': 'na',
                'user_label': None,
                'notes': None,
                'tags': '[]',
                'labels': '[]',
                'created_at': ts,
                'updated_at': ts,
            })

        conn.executemany(
            """
            INSERT INTO device_profiles
                (id, atomic_devices_ids, initial_soft_merge, soft_merge_flag_status,
                 user_label, notes,
                 tags, labels, created_at, updated_at)
            VALUES
                (:id, :atomic_devices_ids, :initial_soft_merge, :soft_merge_flag_status,
                 :user_label, :notes,
                 :tags, :labels, :created_at, :updated_at)
            """,
            device_group_rows
        )
        print(f"[DeviceGrouping] Pass 2: inserted {len(device_group_rows)} device_profiles")

        conn.commit()
        print(f"[DeviceGrouping] Done for upload_id={upload_id}")
