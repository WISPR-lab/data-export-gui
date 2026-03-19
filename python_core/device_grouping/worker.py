import json
import uuid
from datetime import datetime, timezone

from db_session import DatabaseSession
from device_grouping.hard_merge import hard_merge, split
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
        rows = conn.execute(
            """
            SELECT i.id, i.upload_id, i.file_id, i.attributes, i.origin
            FROM devices_raw i
            WHERE i.upload_id = ?
            """,
            (upload_id,)
        ).fetchall()

        if not rows:
            print(f"[DeviceGrouping] No devices_raw rows for upload_id={upload_id}")
            return
        
        for r in rows:
            if not r['attributes']:
                r['attributes'] = '{}'
            if isinstance(r['attributes'], str):
                try:
                    r['attributes'] = json.loads(r['attributes'])
                except json.JSONDecodeError:
                    print(f"[DeviceGrouping] Warning: invalid JSON in attributes for id={r['id']}")
                    r['attributes'] = {}
        # rows = [{"id": 123, "upload_id": 456, "file_id": 789, "attributes": {}}, ...]
        
        atomic_devices_rows = hard_merge(rows)   # lists already serialized
        
        existing_atomics = conn.execute(
            'SELECT id, attributes FROM atomic_devices'
        ).fetchall()
        
        to_insert, to_update = split(atomic_devices_rows, existing_atomics)
        
        for new in to_insert + [u['new'] for u in to_update]:
            attrs = json.loads(new.get('attributes', '{}'))
            new['specificity'] = specificity(attrs)

        conn.executemany(
            """
            INSERT INTO atomic_devices (id, upload_ids, file_ids, devices_raw_ids, attributes, origins, specificity)
            VALUES (:id, :upload_ids, :file_ids, :devices_raw_ids, :attributes, :origins, :specificity)
            """,
            to_insert
        )
        print(f"[DeviceGrouping] Pass 1: inserted {len(to_insert)} new atomic_devices")
        
        for update_info in to_update:
            new = update_info['new']
            existing = update_info['existing']
            atomic_id = existing['id']
            
            new_attrs = json.loads(new.get('attributes', '{}'))
            new_specificity = specificity(new_attrs)
            
            existing_atomic = conn.execute(
                'SELECT attributes, origins, specificity, upload_ids, file_ids, devices_raw_ids FROM atomic_devices WHERE id = ?',
                (atomic_id,)
            ).fetchone()
            
            existing_attrs = json.loads(existing_atomic['attributes'])
            existing_origins = json.loads(existing_atomic['origins'])
            
            merged_attrs = _merge_attrs_pairwise(existing_attrs, new_attrs)
            merged_origins = existing_origins + json.loads(new.get('origins', '[]'))
            merged_origins = [dict(t) for t in set(tuple(sorted(d.items())) for d in merged_origins)]
            merged_origins = sorted(merged_origins, key=lambda x: (x['origin'], x['upload_id']))
            
            merged_upload_ids = sorted(list(set(
                json.loads(existing_atomic['upload_ids']) + 
                json.loads(new.get('upload_ids', '[]'))
            )))
            merged_file_ids = sorted(list(set(
                json.loads(existing_atomic['file_ids']) +
                json.loads(new.get('file_ids', '[]'))
            )))
            merged_devices_raw_ids = sorted(list(set(
                json.loads(existing_atomic['devices_raw_ids']) +
                json.loads(new.get('devices_raw_ids', '[]'))
            )))
            
            conn.execute(
                """
                UPDATE atomic_devices SET
                  attributes = ?,
                  origins = ?,
                  upload_ids = ?,
                  file_ids = ?,
                  devices_raw_ids = ?,
                  specificity = ?
                WHERE id = ?
                """,
                (
                    json.dumps(merged_attrs),
                    json.dumps(merged_origins),
                    json.dumps(merged_upload_ids),
                    json.dumps(merged_file_ids),
                    json.dumps(merged_devices_raw_ids),
                    max(existing_atomic['specificity'], new_specificity),
                    atomic_id
                )
            )
        if to_update:
            print(f"[DeviceGrouping] Pass 1: updated {len(to_update)} existing atomic_devices with cross-upload matches")


        # ------------------------------------------------------------------ #
        # PASS 2: soft-merge atomic_devices --> device_profiles                  #
        # ------------------------------------------------------------------ #

        atomic_devices_rows2 = []
        ts = datetime.now(timezone.utc).timestamp()
        for r in atomic_devices_rows:
            try:
                attrs = json.loads(r.get('attributes', '{}'))
            except json.JSONDecodeError:
                attrs = {}
            atomic_devices_rows2.append({
                'id': r['id'],
                'attributes': attrs,
                'specificity': r.get('specificity', 1)
            })
        
        device_group_rows = []
        for r in soft_merge(atomic_devices_rows2):
            device_group_rows.append({
                'id': r['id'],
                'atomic_devices_ids': r['atomic_devices_ids'],  # already stringified
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
