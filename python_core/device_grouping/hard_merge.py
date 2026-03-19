#  HARD MERGE
#  merge devices if they have the same deterministic, unique identifier
#  this is done by the system, user cannot unmerge

HARD_KEYS = {
    "device_id",
    "device_serial_number",
    "device_imei",
    "device_meid"
}

IS_HARD_KEY = lambda k: any(k == hk or k.startswith(hk) for hk in HARD_KEYS)


import uuid
import json
from utils.redaction_utils import compare_redacted_vals
from device_grouping.specificity import specificity
from device_grouping.shared_utils import union_find, merge_attrs, deduplicate_origins


def hard_match(attrs_a: dict, attrs_b: dict) -> bool:
    keys_a = {k for k in attrs_a if IS_HARD_KEY(k)}
    keys_b = {k for k in attrs_b if IS_HARD_KEY(k)}
    for k in keys_a & keys_b:
        if compare_redacted_vals(attrs_a[k], attrs_b[k]):
            return True
    return False



def hard_merge_one_upload(rows: list[dict]) -> list[dict]:
    def match(a: dict, b: dict) -> bool:
        return hard_match(a.get('attributes', {}), b.get('attributes', {}))
    
    children = union_find(rows, match)

    new_rows = []
    record_map = {r.get("id"): r for r in rows}
    for parent_id, child_id_list in children.items():
        id_list = sorted(list(set([parent_id] + child_id_list)))
        child_rows = [record_map[id] for id in set(id_list)]
        attrs = merge_attrs([r.get("attributes", {}) for r in child_rows], mode='hard')
        
        origins = [{
            "origin": r.get("origin"),
            "upload_id": r.get("upload_id")
        } for r in child_rows if r.get("origin")]
        origins = deduplicate_origins(origins)

        new_rows.append({
            'id': str(uuid.uuid4()),
            'attributes': attrs,
            'origins': origins,
            'upload_ids': sorted(list(set(r.get("upload_id") for r in child_rows))),
            'file_ids': sorted(list(set(r.get("file_id") for r in child_rows))),
            'devices_raw_ids': id_list,
        })

    return new_rows



def hard_merge_with_db(devices_raw_rows: list[dict], atomic_devices_rows: list[dict]) -> list[dict]:
    new_rows = hard_merge_one_upload(devices_raw_rows)
    
    for row in new_rows:
        attrs = row['attributes']
        matching_atomic = None
        for atomic in atomic_devices_rows:
            atomic_attrs = atomic.get('attributes', {})
            if hard_match(attrs, atomic_attrs):
                matching_atomic = atomic
                break
        
        if matching_atomic:
            row['id'] = matching_atomic['id'] or str(uuid.uuid4())
            row['attributes'] = merge_attrs([attrs, matching_atomic.get('attributes', {})], mode='hard')

            existing_origins = matching_atomic.get('origins', [])
            if isinstance(existing_origins, str):
                existing_origins = json.loads(existing_origins)
            row['origins']  = deduplicate_origins(existing_origins + row['origins'])

            existing_upload_ids = matching_atomic.get('upload_ids', [])
            if isinstance(existing_upload_ids, str):
                existing_upload_ids = json.loads(existing_upload_ids)
            row['upload_ids'] = list(set(existing_upload_ids + row['upload_ids']))

            existing_file_ids = matching_atomic.get('file_ids', [])
            if isinstance(existing_file_ids, str):
                existing_file_ids = json.loads(existing_file_ids)
            row['file_ids'] = list(set(existing_file_ids + row['file_ids']))

            existing_devices_raw_ids = matching_atomic.get('devices_raw_ids', [])
            if isinstance(existing_devices_raw_ids, str):
                existing_devices_raw_ids = json.loads(existing_devices_raw_ids)
            row['devices_raw_ids'] = list(set(existing_devices_raw_ids + row['devices_raw_ids']))
    
    return new_rows



def format_rows(rows: list[dict]) -> list[dict]:
    rows_for_db = []
    for row in rows:
        rows_for_db.append({
            'id': row['id'],
            'attributes': json.dumps(row['attributes']),
            'origins': json.dumps(row['origins']),
            'upload_ids': json.dumps(row['upload_ids']),
            'file_ids': json.dumps(row['file_ids']),
            'devices_raw_ids': json.dumps(row['devices_raw_ids']),
            'specificity': specificity(row['attributes']),
        })
    return rows_for_db