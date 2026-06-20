def clean_target(v: str) -> str:
    if isinstance(v, list):
        return [clean_target(i) for i in v]
    if isinstance(v, str):
        return v.strip().replace("@", "").replace(".", "_").lower()
    print("[Utils] Warning: Unhandled type in clean_target:", type(v))
    return ""


def is_trivial(x) -> bool:
    return (
        (x is None)
        or (isinstance(x, str) and x.strip() == "")
        or (x == [])
        or (isinstance(x, list) and all((e == "" or e is None or e == []) for e in x))
    )
