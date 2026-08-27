#!/usr/bin/env python3
"""
scripts/validate_manifests.py

checks manifests/*.yaml against manifests/__taxonomy.yaml: structure, field
vocab, and event.action/entity.type relationship shape. read-only — reports
gaps and mismatches, never writes. manifests/__taxonomy.yaml is edited by hand
(a person or an AI session), not by this script.

    python scripts/validate_manifests.py
"""

import argparse
import glob
import os
import re
import sys
from collections import namedtuple

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MANIFESTS_DIR = os.path.join(REPO_ROOT, "manifests")
DEFAULT_TAXONOMY_PATH = os.path.join(DEFAULT_MANIFESTS_DIR, "__taxonomy.yaml")

KNOWN_PARSER_FORMATS = {  # python_core/semantic_map/views.py REGISTRY
    "json", "jsonl", "csv", "csv_multi", "json_label_values",
    "html", "html_table", "html_ggl_myactivity", "html_ggl_subscriber_info",
    "html_key_val",
}

KNOWN_WHERE_OPS = {  # python_core/utils/filter_builder.py OP_MAPPING
    "==", "===", "=", "eq",
    "!=", "!==", "ne", "neq",
    "contains", "includes",
    "startswith", "starts_with",
    "endswith", "ends_with",
}

KNOWN_FIELD_TYPES = {"string", "datetime", "date", "timestamp"}  # anything else passes through untouched at runtime
KNOWN_DEDUPE_KEEP = {"first", "last", "row_completeness"}  # python_core/extractors/csv_.py drop_duplicates()

RELATIONSHIP_KEYS = ("event.action", "entity.type", "entity.sub_type")

Issue = namedtuple("Issue", ["severity", "message"])


def discover_and_load(manifests_dir):
    loaded = []
    for path in sorted(glob.glob(os.path.join(manifests_dir, "*.yaml"))):
        if os.path.basename(path) == os.path.basename(DEFAULT_TAXONOMY_PATH):
            continue
        platform = os.path.splitext(os.path.basename(path))[0]
        try:
            cfg = yaml.safe_load(open(path, "r", encoding="utf-8"))
        except yaml.YAMLError as e:
            loaded.append((platform, path, None, str(e)))
            continue
        if not isinstance(cfg, dict):
            loaded.append((platform, path, None, "top-level YAML is not a mapping"))
            continue
        loaded.append((platform, path, cfg, None))
    return loaded


def iter_view_fields(view):
    static = view.get("static")
    if isinstance(static, dict):
        for k, v in static.items():
            if isinstance(k, str) and k.strip():
                yield k, "static", v
    for f in view.get("fields") or []:
        if isinstance(f, dict) and isinstance(f.get("target"), str) and f["target"].strip():
            yield f["target"], "dynamic", None


def load_taxonomy(path):
    data = yaml.safe_load(open(path, "r", encoding="utf-8")) or {}
    if not isinstance(data.get("fields"), dict):
        data["fields"] = {}
    if not isinstance(data.get("relationships"), dict):
        data["relationships"] = {}
    for key in RELATIONSHIP_KEYS:
        if not isinstance(data["relationships"].get(key), dict):
            data["relationships"][key] = {}
    return data


def collect_used_fields(manifests):
    used_field_to_platforms = {}
    for platform, _path, cfg, err in manifests:
        if err is not None or not cfg:
            continue
        for view in cfg.get("views") or []:
            if not isinstance(view, dict):
                continue
            for name, _kind, _value in iter_view_fields(view):
                used_field_to_platforms.setdefault(name, set()).add(platform)
    return used_field_to_platforms


def collect_used_static_values(manifests):
    """field_name -> set of literal values its static: entries hold across all
    manifests (list-valued fields like event.category get flattened)."""
    used_field_to_values = {}
    for platform, _path, cfg, err in manifests:
        if err is not None or not cfg:
            continue
        for view in cfg.get("views") or []:
            if not isinstance(view, dict):
                continue
            for name, kind, value in iter_view_fields(view):
                if kind != "static":
                    continue
                bucket = used_field_to_values.setdefault(name, set())
                bucket.update(value) if isinstance(value, list) else bucket.add(value)
    return used_field_to_values


def validate_where(where, loc):
    if not isinstance(where, dict):
        return [Issue("error", f"{loc}: must be a mapping")]
    if all(k in where for k in ("source", "op", "value")):
        if where["op"] not in KNOWN_WHERE_OPS:
            return [Issue("error", f"{loc}: unknown op '{where['op']}'")]
        return []
    if "logic" in where and "conditions" in where:
        issues = []
        if str(where.get("logic")).lower() not in ("all", "any"):
            issues.append(Issue("error", f"{loc}.logic: must be 'all' or 'any'"))
        for i, cond in enumerate(where.get("conditions") or []):
            cloc = f"{loc}.conditions[{i}]"
            if not isinstance(cond, dict) or not all(k in cond for k in ("source", "op", "value")):
                issues.append(Issue("error", f"{cloc}: must have source/op/value"))
            elif cond["op"] not in KNOWN_WHERE_OPS:
                issues.append(Issue("error", f"{cloc}: unknown op '{cond['op']}'"))
        return issues
    return [Issue("error", f"{loc}: must be {{source, op, value}} or {{logic, conditions}}")]


def check_static_value(name, value, taxonomy_fields, loc):
    allowed_values = (taxonomy_fields.get(name) or {}).get("allowed_values")
    if allowed_values is None:
        return []
    bad_values = [v for v in (value if isinstance(value, list) else [value]) if v not in allowed_values]
    return [Issue("error", f"{loc}: value '{v}' for '{name}' not in allowed_values ({', '.join(map(str, allowed_values))}) "
                            "— add it if legitimate, or fix the manifest")
            for v in bad_values]


def check_relationship_shape(rel_entry, static, loc, check_type):
    issues = []
    want_kind = rel_entry.get("kind")
    if want_kind is not None and static.get("event.kind") != want_kind:
        issues.append(Issue("error", f"{loc}: event.kind '{static.get('event.kind')}' expected '{want_kind}'"))
    want_category = rel_entry.get("category")
    if want_category is not None:
        got_category = static.get("event.category")
        if set(got_category or []) != set(want_category):
            issues.append(Issue("error", f"{loc}: event.category {got_category} expected {want_category}"))
    if not check_type:
        return issues
    want_type = rel_entry.get("type")
    if want_type is not None:
        got_type = static.get("event.type")
        if set(got_type or []) != set(want_type):
            issues.append(Issue("error", f"{loc}: event.type {got_type} expected {want_type}"))
    want_outcomes = rel_entry.get("outcomes")
    got_outcome = static.get("event.outcome")
    if want_outcomes is not None and got_outcome is not None and got_outcome not in want_outcomes:
        issues.append(Issue("error", f"{loc}: event.outcome '{got_outcome}' not in {want_outcomes} for this action"))
    return issues


def check_relationship_key(static, relationships, key, check_type, loc):
    value = static.get(key)
    if not isinstance(value, str):
        return []
    entry = relationships[key].get(value)
    if entry:
        return check_relationship_shape(entry, static, f"{loc} ({key}={value})", check_type)
    if value in relationships[key]:
        return [Issue("warning", f"{loc}: {key} '{value}' has no relationship shape declared "
                                  f"— define one, or reconsider the {key} name")]
    return []


def check_relationships(static, relationships, loc):
    return (
        check_relationship_key(static, relationships, "event.action", True, loc)
        + check_relationship_key(static, relationships, "entity.type", False, loc)
        + check_relationship_key(static, relationships, "entity.sub_type", False, loc)
    )


def validate_manifest(cfg, taxonomy):
    taxonomy_fields, relationships = taxonomy["fields"], taxonomy["relationships"]
    issues = []
    used_field_names = set()

    for key in ("manifest_version", "id", "target", "last_updated", "files", "views"):
        if key not in cfg:
            issues.append(Issue("error", f"top-level: missing '{key}'"))
    if "manifest_version" in cfg and not isinstance(cfg["manifest_version"], int):
        issues.append(Issue("error", "top-level: manifest_version must be an integer"))
    if "last_updated" in cfg and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(cfg.get("last_updated"))):
        issues.append(Issue("warning", f"top-level: last_updated '{cfg.get('last_updated')}' is not YYYY-MM-DD"))

    file_ids = set()
    for i, fs in enumerate(cfg.get("files") or []):
        loc = f"files[{i}]"
        if not isinstance(fs, dict):
            issues.append(Issue("error", f"{loc}: not a mapping"))
            continue
        fid = fs.get("id")
        if not fid:
            issues.append(Issue("error", f"{loc}: missing id"))
        elif fid in file_ids:
            issues.append(Issue("error", f"{loc}: duplicate file id '{fid}'"))
        else:
            file_ids.add(fid)
        if not fs.get("path"):
            issues.append(Issue("error", f"{loc}: missing path"))

        parser = fs.get("parser")
        if not isinstance(parser, dict):
            issues.append(Issue("error", f"{loc}: missing/invalid parser"))
            continue
        fmt = parser.get("format")
        if not fmt:
            issues.append(Issue("error", f"{loc}.parser: missing format"))
        elif fmt not in KNOWN_PARSER_FORMATS:
            issues.append(Issue("error", f"{loc}.parser: unknown format '{fmt}'"))
        dd = parser.get("drop_duplicates")
        if dd is not None:
            if not isinstance(dd, dict) or "subset" not in dd:
                issues.append(Issue("error", f"{loc}.parser.drop_duplicates: missing subset"))
            keep = dd.get("keep", "first") if isinstance(dd, dict) else None
            if keep not in KNOWN_DEDUPE_KEEP:
                issues.append(Issue("warning", f"{loc}.parser.drop_duplicates: keep '{keep}' falls back to 'first' at runtime"))

    for i, v in enumerate(cfg.get("views") or []):
        loc = f"views[{i}]"
        if not isinstance(v, dict):
            issues.append(Issue("error", f"{loc}: not a mapping"))
            continue

        file_ref = v.get("file")
        if not isinstance(file_ref, dict) or not file_ref.get("id"):
            issues.append(Issue("error", f"{loc}.file: missing id"))
        else:
            if file_ref["id"] not in file_ids:
                issues.append(Issue("error", f"{loc}.file.id: '{file_ref['id']}' matches no files[].id"))
            if file_ref.get("where") is not None:
                issues.extend(validate_where(file_ref["where"], f"{loc}.file.where"))

        static = v.get("static") or {}
        for name, kind, value in iter_view_fields(v):
            used_field_names.add(name)
            if kind == "static":
                issues.extend(check_static_value(name, value, taxonomy_fields, f"{loc}.static.{name}"))
        issues.extend(check_relationships(static, relationships, loc))

        for fi, f in enumerate(v.get("fields") or []):
            floc = f"{loc}.fields[{fi}]"
            if not isinstance(f, dict):
                issues.append(Issue("error", f"{floc}: not a mapping"))
                continue
            if not f.get("target"):
                issues.append(Issue("error", f"{floc}: missing target"))
            if not f.get("source"):
                issues.append(Issue("error", f"{floc}: missing source"))
            ftype = f.get("type")
            if ftype is not None and ftype not in KNOWN_FIELD_TYPES:
                issues.append(Issue("warning", f"{floc}: type '{ftype}' unrecognized, treated as opaque string"))
            transform = f.get("transform")
            if transform is not None and transform != "coalesce":
                issues.append(Issue("error", f"{floc}: transform '{transform}' unimplemented, silently ignored"))

    unknown_fields = sorted(n for n in used_field_names if n not in taxonomy_fields)
    if unknown_fields:
        issues.append(Issue("error", f"field(s) not in taxonomy: {', '.join(unknown_fields)} "
                                      "— add an entry in manifests/__taxonomy.yaml, or check whether an existing field is more appropriate"))
    undocumented_fields = sorted(n for n in used_field_names if n in taxonomy_fields and (taxonomy_fields[n] or {}).get("description") is None)
    if undocumented_fields:
        issues.append(Issue("warning", f"field(s) missing a taxonomy description: {', '.join(undocumented_fields)}"))

    return issues


def report_unused_taxonomy_entries(taxonomy, used_fields, used_values):
    orphaned_fields = sorted(set(taxonomy["fields"]) - set(used_fields))
    if orphaned_fields:
        print(f"taxonomy: field(s) declared but unused anywhere: {', '.join(orphaned_fields)} "
              "— safe to remove, or maybe just renamed")
    for rel_key in RELATIONSHIP_KEYS:
        orphaned = sorted(set(taxonomy["relationships"][rel_key]) - used_values.get(rel_key, set()))
        if orphaned:
            print(f"taxonomy: {rel_key} relationship(s) declared but unused anywhere: {', '.join(orphaned)} "
                  "— safe to remove, or maybe just renamed")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifests-dir", default=DEFAULT_MANIFESTS_DIR)
    parser.add_argument("--taxonomy", default=DEFAULT_TAXONOMY_PATH)
    args = parser.parse_args()

    manifests = discover_and_load(args.manifests_dir)
    if not os.path.exists(args.taxonomy):
        print(f"no taxonomy at {os.path.relpath(args.taxonomy)}")
        sys.exit(1)
    taxonomy = load_taxonomy(args.taxonomy)

    error_count = warning_count = 0
    for platform, _path, cfg, err in manifests:
        issues = [Issue("error", f"YAML parse error: {err}")] if err else validate_manifest(cfg, taxonomy)
        issues = list(dict.fromkeys(issues))
        if not issues:
            print(f"{platform}.yaml  OK")
            continue
        print(f"{platform}.yaml")
        for issue in issues:
            print(f"  {issue.severity.upper():7} {issue.message}")
            error_count += issue.severity == "error"
            warning_count += issue.severity == "warning"
        print()

    report_unused_taxonomy_entries(taxonomy, collect_used_fields(manifests), collect_used_static_values(manifests))

    print(f"\n{len(manifests)} manifest(s) — {error_count} error(s), {warning_count} warning(s)")
    sys.exit(1 if error_count else 0)


if __name__ == "__main__":
    main()
