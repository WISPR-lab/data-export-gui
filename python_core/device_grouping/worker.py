import re
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from db_session import DatabaseSession
from utils.redaction_utils import compare_redacted_vals
from device_grouping.hard_merge import hard_merge
from device_grouping.soft_merge import soft_merge, merge_attrs
from python_core.device_grouping.specificity import specificity


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
        
        for row in atomic_devices_rows:
            attrs = json.loads(row.get('attributes', '{}'))
            row['specificity'] = specificity(attrs)

        conn.executemany(
            """
            INSERT INTO atomic_devices (id, upload_ids, file_ids, devices_raw_ids, attributes, origins, specificity)
            VALUES (:id, :upload_ids, :file_ids, :devices_raw_ids, :attributes, :origins, :specificity)
            """,
            atomic_devices_rows
        )
        print(f"[DeviceGrouping] Pass 1: inserted {len(atomic_devices_rows)} atomic_devices")


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
