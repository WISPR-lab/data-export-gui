import re
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from db_session import DatabaseSession
from utils.redaction_utils import compare_redacted_vals
from device_grouping.hard_merge import hard_merge
from device_grouping.soft_merge import soft_merge, merge_attrs


def _get_config_value(name):
    import builtins
    if not hasattr(builtins, name):
        raise ValueError(f"Config value '{name}' not found in builtins.")
    return getattr(builtins, name)



def group(upload_id: str, db_path: str = None) -> None:
    db_path = db_path or _get_config_value('DB_PATH')

    with DatabaseSession(db_path, use_dict_factory=True) as conn:

        # ------------------------------------------------------------------ #
        # PASS 1: hard-merge auth_devices_initial --> auth_devices           #
        # ------------------------------------------------------------------ #
        rows = conn.execute(
            """
            SELECT i.id, i.upload_id, i.file_id, i.attributes
            FROM auth_devices_initial i
            WHERE i.upload_id = ?
            """,
            (upload_id,)
        ).fetchall()

        if not rows:
            print(f"[DeviceGrouping] No auth_devices_initial rows for upload_id={upload_id}")
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
        
        auth_devices_rows = hard_merge(rows)   # lists already serialized

        conn.executemany(
            """
            INSERT INTO auth_devices (id, upload_ids, file_ids, auth_devices_initial_ids, attributes)
            VALUES (:id, :upload_ids, :file_ids, :auth_devices_initial_ids, :attributes)
            """,
            auth_devices_rows
        )
        print(f"[DeviceGrouping] Pass 1: inserted {len(auth_devices_rows)} auth_devices")


        # ------------------------------------------------------------------ #
        # PASS 2: soft-merge auth_devices --> device_groups                  #
        # ------------------------------------------------------------------ #

        auth_devices_rows2 = []
        ts = datetime.now(timezone.utc).timestamp()
        for r in auth_devices_rows:
            try:
                attrs = json.loads(r.get('attributes', '{}'))
            except json.JSONDecodeError:
                attrs = {}
            auth_devices_rows2.append({'id': r['id'], 'attributes': attrs})
        
        device_group_rows = []
        for r in soft_merge(auth_devices_rows2):
            device_group_rows.append({
                'id': r['id'],
                'auth_devices_ids': r['auth_devices_ids'],  # already stringified
                'initial_soft_merge': r['initial_soft_merge'],
                'soft_merge_flag_status': 'na',
                'tags': '[]',
                'labels': '[]',
                'created_at': ts,
                'updated_at': ts,
            })

        conn.executemany(
            """
            INSERT INTO device_groups
                (id, auth_devices_ids, initial_soft_merge, soft_merge_flag_status,
                 tags, labels, created_at, updated_at)
            VALUES
                (:id, :auth_devices_ids, :initial_soft_merge, :soft_merge_flag_status,
                 :tags, :labels, :created_at, :updated_at)
            """,
            device_group_rows
        )
        print(f"[DeviceGrouping] Pass 2: inserted {len(device_group_rows)} device_groups")

        conn.commit()
        print(f"[DeviceGrouping] Done for upload_id={upload_id}")
