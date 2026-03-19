from typing import Callable

def find(parent: dict, x: str) -> str:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

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
