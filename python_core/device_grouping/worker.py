import re
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from db_session import DatabaseSession
from utils.redaction_utils import values_match


_HARD_KEY_RE = re.compile(r'^device\.id\..+')
_HARD_KEY_FIXED = {'device.serial_number', 'device.imei', 'device.meid'}

_VARIANT_SUFFIXES = {
    'xr', 'xs', 'se', 'max', 'plus', 'pro', 'ultra', 'mini',
    'air', 'lite', 'edge', 'note', 'fold', 'flip'
}

_GENERIC = {'other', 'unknown', 'phone', 'smartphone', 'tablet', 'android', 'iphone', 'ipad', ''}


def _get_config_value(name):
    import builtins
    if not hasattr(builtins, name):
        raise ValueError(f"Config value '{name}' not found in builtins.")
    return getattr(builtins, name)


def _is_hard_key(k: str) -> bool:
    return bool(_HARD_KEY_RE.match(k)) or k in _HARD_KEY_FIXED


def _os_type(attrs: dict) -> str:
    return (attrs.get('user_agent.os.type') or '').strip().lower()


def _os_guard(attrs_a: dict, attrs_b: dict) -> bool:
    """Returns True if the records are compatible (could be same device)."""
    os_a, os_b = _os_type(attrs_a), _os_type(attrs_b)
    if os_a and os_b and os_a != os_b:
        return False
    return True


def _hard_match(attrs_a: dict, attrs_b: dict) -> bool:
    keys_a = {k for k in attrs_a if _is_hard_key(k)}
    keys_b = {k for k in attrs_b if _is_hard_key(k)}
    for k in keys_a & keys_b:
        if values_match(attrs_a[k], attrs_b[k]):
            return True
    return False


def _is_specific_model(name: str) -> bool:
    if not name or name.lower() in _GENERIC:
        return False
    if any(c.isdigit() for c in name):
        return True
    words = {w.lower().rstrip('.,') for w in name.split()}
    return bool(words & _VARIANT_SUFFIXES)


def _soft_match(attrs_a: dict, attrs_b: dict) -> bool:
    mfr_a = (attrs_a.get('device.manufacturer') or '').strip().lower()
    mfr_b = (attrs_b.get('device.manufacturer') or '').strip().lower()
    model_a = (attrs_a.get('device.model.name') or '').strip()
    model_b = (attrs_b.get('device.model.name') or '').strip()
    if not mfr_a or not mfr_b or not model_a or not model_b:
        return False
    return (
        mfr_a == mfr_b
        and model_a.lower() == model_b.lower()
        and _is_specific_model(model_a)
    )


def _merge_attrs(attrs_list: list[dict]) -> dict:
    merged = {}
    for attrs in attrs_list:
        for k, v in attrs.items():
            if v and not merged.get(k):
                merged[k] = v
    return merged


def _find(parent: dict, x: str) -> str:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _union(parent: dict, x: str, y: str) -> None:
    parent[_find(parent, x)] = _find(parent, y)


def _build_components(ids: list, parent: dict) -> dict:
    components = defaultdict(list)
    for i in ids:
        components[_find(parent, i)].append(i)
    return components


def group(upload_id: str, db_path: str = None) -> None:
    db_path = db_path or _get_config_value('DB_PATH')
    ts = datetime.now(timezone.utc).timestamp()

    with DatabaseSession(db_path, use_dict_factory=True) as conn:

        # ------------------------------------------------------------------ #
        # PASS 1: hard-merge auth_devices_initial → auth_devices              #
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

        records = [
            (r['id'], r['upload_id'], r['file_id'], json.loads(r['attributes'] or '{}'))
            for r in rows
        ]

        parent = {r[0]: r[0] for r in records}

        for i, (id_a, _, _, attrs_a) in enumerate(records):
            for id_b, _, _, attrs_b in records[i + 1:]:
                if not _os_guard(attrs_a, attrs_b):
                    continue
                if _hard_match(attrs_a, attrs_b):
                    _union(parent, id_a, id_b)

        hard_components = _build_components([r[0] for r in records], parent)

        record_map = {r[0]: r for r in records}
        auth_device_rows = []
        for members in hard_components.values():
            merged_attrs = _merge_attrs([record_map[m][3] for m in members])
            auth_device_rows.append({
                'id': str(uuid.uuid4()),
                'upload_ids': json.dumps([upload_id]),
                'file_ids': json.dumps(list({record_map[m][2] for m in members})),
                'auth_devices_initial_ids': json.dumps(members),
                'attributes': json.dumps(merged_attrs),
                'created_at': ts,
            })

        conn.executemany(
            """
            INSERT INTO auth_devices (id, upload_ids, file_ids, auth_devices_initial_ids, attributes, created_at)
            VALUES (:id, :upload_ids, :file_ids, :auth_devices_initial_ids, :attributes, :created_at)
            """,
            auth_device_rows
        )
        print(f"[DeviceGrouping] Pass 1: inserted {len(auth_device_rows)} auth_devices")

        # ------------------------------------------------------------------ #
        # PASS 2: soft-merge auth_devices → device_groups                     #
        # ------------------------------------------------------------------ #
        ad_rows = conn.execute(
            """
            SELECT id, attributes FROM auth_devices
            WHERE json_extract(upload_ids, '$[0]') = ?
            """,
            (upload_id,)
        ).fetchall()

        ad_records = [
            (r['id'], json.loads(r['attributes'] or '{}'))
            for r in ad_rows
        ]

        parent2 = {r[0]: r[0] for r in ad_records}

        for i, (id_a, attrs_a) in enumerate(ad_records):
            for id_b, attrs_b in ad_records[i + 1:]:
                if not _os_guard(attrs_a, attrs_b):
                    continue
                if _soft_match(attrs_a, attrs_b):
                    _union(parent2, id_a, id_b)

        soft_components = _build_components([r[0] for r in ad_records], parent2)
        ad_map = {r[0]: r[1] for r in ad_records}

        device_group_rows = []
        for members in soft_components.values():
            is_soft = len(members) > 1
            merged_attrs = _merge_attrs([ad_map[m] for m in members])
            device_group_rows.append({
                'id': str(uuid.uuid4()),
                'auth_devices_ids': json.dumps(members),
                'initial_soft_merge': 1 if is_soft else 0,
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
