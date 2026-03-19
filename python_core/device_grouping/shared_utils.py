from typing import Callable
from utils.redaction_utils import get_unredacted_val


def find(parent: dict, x: str) -> str:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


HARD_KEYS = {
    "device_id",
    "device_serial_number",
    "device_imei",
    "device_meid"
}


def union_find(records: list[dict], match_fn: Callable[[dict, dict], bool]) -> dict[str, list[str]]:
    parent = {r.get("id"): r.get("id") for r in records}
    
    for i, dct_a in enumerate(records):
        for dct_b in records[i + 1:]:
            if match_fn(dct_a, dct_b):
                parent[find(parent, dct_a.get('id'))] = find(parent, dct_b.get('id'))
    
    children: dict[str, list[str]] = {}
    for r in records:
        root = find(parent, r.get("id"))
        if root not in children:
            children[root] = []
        children[root].append(r.get("id"))
    
    return children


def merge_attrs(attrs_list: list[dict], mode: str = 'soft') -> dict:
    if not attrs_list:
        return {}
    
    attrs_new = attrs_list[0].copy()
    for attrs in attrs_list[1:]:
        for k in set(attrs_new) | set(attrs):
            v_a, v_b = attrs_new.get(k), attrs.get(k)
            
            if mode == 'hard' and k in HARD_KEYS:
                attrs_new[k] = get_unredacted_val(v_a, v_b)[0] or v_a or v_b
            else:
                attrs_new[k] = v_a if (v_a and v_a != '') else v_b
    
    return attrs_new


def deduplicate_origins(origins_list: list[dict]) -> list[dict]:
    return [dict(t) for t in set(tuple(sorted(d.items())) for d in origins_list)]
