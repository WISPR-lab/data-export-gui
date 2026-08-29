import re
from collections import namedtuple
from utils.json_utils import get_value_at_path
from utils.filter_builder import make_filter
from semantic_map.time_utils import parse_date, unix_ms


def clean_target(v: str) -> str:
    if isinstance(v, list):
        return [clean_target(i) for i in v]
    if isinstance(v, str):
        return v.strip().replace("@", "").replace(".", "_").lower()
    print("[Views] Warning: Unhandled type in clean_target:", type(v))
    return ""


def is_trivial(x) -> bool:
    return (
        (x is None)
        or (isinstance(x, str) and x.strip() == "")
        or (x == [])
        or (isinstance(x, list) and all((e == "" or e is None or e == []) for e in x))
    )


def static_fields(view: dict):
    if not isinstance(view, dict) or "static" not in view:
        print(f"[Views] No static fields defined in view: {view}")
        return {}
    return {clean_target(k): v for k, v in view.get("static", {}).items()}


def dynamic_fields(record: dict, view: dict, default=""):
    if not isinstance(view, dict) or "fields" not in view:
        print(f"[Views] No dynamic fields defined in view: {view}")
        return {}
    if not isinstance(record, dict):
        print(f"[Views] Record is not a dict for dynamic field extraction: {record}")
        return {}

    fields = {}
    for f in view.get("fields", []):
        target, source, ftype = (
            f.get("target"),
            f.get("source"),
            f.get("type", "string"),
        )

        if isinstance(source, list):
            if f.get("transform", "").lower() == "coalesce":
                val = next(
                    (
                        get_value_at_path(record, s)
                        for s in source
                        if not is_trivial(get_value_at_path(record, s))
                    ),
                    default,
                )
            else:
                val = get_value_at_path(
                    record, source[0], default
                )  # default to first source if no transform specified
        else:
            val = get_value_at_path(record, source, default)

        # Apply regex extractor if configured
        if f.get("regex") and val:
            match = re.search(f.get("regex"), str(val))
            if match:
                val = match.group(1).strip()
            else:
                val = default

        if ftype in ["datetime", "timestamp", "date"]:
            val = unix_ms(parse_date(str(val)))

        key = clean_target(target)
        if not is_trivial(val) or key not in fields:
            fields[key] = val
    return fields


def fields(record: dict, view: dict, default="", static: dict = None):
    static = static_fields(view) if static is None else static
    dynamic = dynamic_fields(record, view, default)
    return {**static, **dynamic}


# One of these per view: the raw view dict plus its precompiled filter callable
# (None if the view has no `where` clause, i.e. always applies) and precomputed
# static-field dict. Bundled together — rather than parallel lists indexed by
# position — so filter/static can never end up misaligned with the view they
# belong to.
CompiledView = namedtuple("CompiledView", ["view", "filter", "static"])


def compile_views(views: list) -> list:
    """
    Precompute a CompiledView per view. `where`/`static` are invariant per view
    for the life of a Manifest, so callers processing many records against the
    same `views` list should build this once (see
    semantic_map.worker._generate_table_rows) instead of rebuilding a filter
    closure tree / static dict from the manifest config on every record.
    """
    compiled = []
    for view in views:
        where = view.get("file", {}).get("where", {}) if isinstance(view, dict) else {}
        filt = make_filter(where) if where else None
        compiled.append(CompiledView(view=view, filter=filt, static=static_fields(view)))
    return compiled


def view_indexes_to_apply(record: dict, views: list, compiled_views: list = None):
    indexes = []
    compiled = compiled_views if compiled_views is not None else compile_views(views)

    for i, cv in enumerate(compiled):
        if cv.filter is None or cv.filter(record):
            indexes.append(i)
    return indexes
