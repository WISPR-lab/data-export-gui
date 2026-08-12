"""
evaluation/efficiency/augment.py

Takes a platform's original export ZIP, repeats the entries in each parsed file
N times (with small random date shifts so records aren't identical), then writes
a new ZIP of the same shape.

Input:  evaluation/efficiency/data/<platform>_original.zip
Output: evaluation/efficiency/data/<platform>_<N>x.zip
Scratch: evaluation/efficiency/data/.tmp/  (deleted after each run)

Usage:
    uv run python -m evaluation.efficiency.augment --platform facebook --multiplier 10
    uv run python -m evaluation.efficiency.augment --platform google   --multiplier 100
    uv run python -m evaluation.efficiency.augment --platform facebook --multiplier 1000

Which files to expand, which fields hold dates, and what format each file is in
are all read from manifests/<platform>.yaml — nothing is hardcoded here.
Files the parser ignores are copied unchanged.
"""

import argparse
import copy
import fnmatch
import json
import os
import random
import re
import shutil
import sys
import zipfile

import yaml

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

JITTER_SECONDS = 7 * 24 * 3600   # ±7 days
MANIFESTS_DIR  = os.path.join(_REPO_ROOT, "manifests")


def _jitter():
    return random.randint(-JITTER_SECONDS, JITTER_SECONDS)


def _jitter_unix(value):
    try:
        return int(value) + _jitter()
    except (TypeError, ValueError):
        return value


_ISO_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})?"
)

def _jitter_isostr(s):
    from datetime import datetime, timezone, timedelta
    m = _ISO_RE.search(str(s))
    if not m:
        return s
    try:
        base   = m.group(1)
        suffix = (m.group(2) or "") + (m.group(3) or "Z")
        fmt    = "%Y-%m-%dT%H:%M:%S" if "T" in base else "%Y-%m-%d %H:%M:%S"
        dt     = datetime.strptime(base, fmt).replace(tzinfo=timezone.utc)
        dt    += timedelta(seconds=_jitter())
        return s[:m.start()] + dt.strftime(fmt) + suffix + s[m.end():]
    except Exception:
        return s


def _jitter_record(record, datetime_fields):
    """
    Return a copy of record with date fields shifted by a random ±7 days.
    Only touches fields listed in datetime_fields (taken from the manifest).
    ponytail: one-level only — matches all flat record formats we produce.
    """
    result = {}
    for k, v in record.items():
        if k == "__line_numbers":
            result[k] = v
        elif k in datetime_fields:
            if isinstance(v, (int, float)):
                result[k] = _jitter_unix(v)
            elif isinstance(v, str):
                result[k] = _jitter_unix(v) if v.strip().isdigit() else _jitter_isostr(v)
            else:
                result[k] = v
        else:
            result[k] = v
    return result


def _augment_json(content, json_root, multiplier, datetime_fields):
    data = json.loads(content)
    key = json_root.replace("[]", "").strip() if json_root else ""
    records = data.get(key) if key else data
    if not isinstance(records, list):
        return content
    cloned = [_jitter_record(copy.deepcopy(r), datetime_fields) for _ in range(multiplier) for r in records]
    if key:
        data[key] = cloned
    else:
        data = cloned
    return json.dumps(data, ensure_ascii=False, indent=2)

# ponytail: json_label_values with json_root="[]" is identical to _augment_json with empty key;
# no separate function needed.


_MYACTIVITY_DATE_RE = re.compile(
    r"([A-Z][a-z]+ \d{1,2}, \d{4},? \d{1,2}:\d{2}:\d{2}(?:\s*[AP]M)?(?:\s+[A-Z]{2,5})?)"
)

def _jitter_myactivity_date(html_str):
    from datetime import datetime, timedelta

    def shift(m):
        raw = m.group(1)
        for fmt in ["%B %d, %Y, %I:%M:%S %p", "%B %d, %Y %I:%M:%S %p", "%B %d, %Y, %H:%M:%S"]:
            try:
                dt = datetime.strptime(raw.strip(), fmt)
                dt += timedelta(seconds=_jitter())
                return dt.strftime(fmt)
            except ValueError:
                continue
        return raw

    return _MYACTIVITY_DATE_RE.sub(shift, html_str, count=1)


def _augment_html_myactivity(content, multiplier):
    """Google My Activity HTML: each activity is a <div class="outer-cell"> block. Clone them N times."""
    from bs4 import BeautifulSoup

    soup        = BeautifulSoup(content, "html.parser")
    outer_cells = soup.find_all(
        "div", class_="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp"
    )
    if not outer_cells:
        return content

    container = outer_cells[0].parent
    originals  = [str(c) for c in outer_cells]
    for cell in outer_cells:
        cell.decompose()

    new_html = "".join(
        _jitter_myactivity_date(orig)
        for _ in range(multiplier)
        for orig in originals
    )
    frag = BeautifulSoup(new_html, "html.parser")
    for tag in list(frag.contents):
        container.append(copy.copy(tag))

    return str(soup)


def _augment_html_table(content, multiplier):
    """Google table HTML (ChangeHistory, SubscriberInfo): clone each data row N times, keep the header."""
    from bs4 import BeautifulSoup

    soup  = BeautifulSoup(content, "html.parser")
    table = soup.find("table")
    if not table:
        return content

    rows = table.find_all("tr")
    if len(rows) < 2:
        return content

    data_rows = rows[1:]
    originals = [str(r) for r in data_rows]
    for r in data_rows:
        r.decompose()

    frag = BeautifulSoup("".join(originals * multiplier), "html.parser")
    for tag in frag.find_all("tr"):
        table.append(copy.copy(tag))

    return str(soup)


def _augment_csv(content, multiplier):
    lines = content.splitlines(keepends=True)
    return (lines[0] + "".join(lines[1:] * multiplier)) if lines else content


def _augment_file(content, fmt, json_root, multiplier, datetime_fields):
    if fmt in ("json", "json_label_values"):
        return _augment_json(content, json_root, multiplier, datetime_fields)
    if fmt == "html_ggl_myactivity":
        return _augment_html_myactivity(content, multiplier)
    if fmt in ("html_table", "html_ggl_subscriber_info"):
        return _augment_html_table(content, multiplier)
    if fmt == "csv":
        return _augment_csv(content, multiplier)
    return content


def load_manifest(platform):
    with open(os.path.join(MANIFESTS_DIR, f"{platform}.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_whitelist_index(manifest):
    # Map file_id -> set of datetime field names across all views
    dt_fields_by_file = {}
    for v in manifest.get("views", []):
        fid = (v.get("file") or {}).get("id")
        if not fid: continue
        dt_fields_by_file.setdefault(fid, set())
        for f in v.get("fields") or []:
            if isinstance(f, dict) and f.get("type") == "datetime":
                src = f.get("source")
                sources = src if isinstance(src, list) else ([src] if src else [])
                for s in sources:
                    dt_fields_by_file[fid].add(s.split(".")[0])

    return [
        {
            "pattern":         e["path"],
            "format":          e.get("parser", {}).get("format", ""),
            "json_root":       e.get("parser", {}).get("json_root", ""),
            "datetime_fields": dt_fields_by_file.get(e["id"], set()),
        }
        for e in manifest.get("files", [])
    ]


def match_whitelist(rel_path, index):
    """
    Returns the matching entry if rel_path ends with a manifest path pattern,
    ignoring any leading folder name in the zip.
    Example: "takeout-export/security/foo.json" matches pattern "security/foo.json".
    Same logic as the JS upload handler in opfs_manager.js.
    """
    norm = rel_path.replace("\\", "/").lower()
    for entry in index:
        pat = entry["pattern"].lower()
        if fnmatch.fnmatch(norm, pat) or fnmatch.fnmatch(norm, "*/" + pat):
            return entry
    return None


def augment_zip(source_zip, output_zip, platform, multiplier):
    """
    Unzip source_zip, expand the parsed files N times, re-zip to output_zip.
    Scratch space is data/.tmp/ and is deleted whether or not the run succeeds.
    """
    data_dir = os.path.dirname(source_zip)
    tmp_src  = os.path.join(data_dir, ".tmp", f"{platform}_src")
    tmp_out  = os.path.join(data_dir, ".tmp", f"{platform}_out")

    manifest = load_manifest(platform)
    index    = build_whitelist_index(manifest)

    try:
        if os.path.exists(tmp_src):
            shutil.rmtree(tmp_src)
        with zipfile.ZipFile(source_zip, "r") as zf:
            zf.extractall(tmp_src)

        # If the zip has a single top-level folder (the common case), step into it.
        entries = os.listdir(tmp_src)
        src_root = (os.path.join(tmp_src, entries[0])
                    if len(entries) == 1 and os.path.isdir(os.path.join(tmp_src, entries[0]))
                    else tmp_src)

        # Copy files from src_root to tmp_out, expanding parsed files N times.
        if os.path.exists(tmp_out):
            shutil.rmtree(tmp_out)
        os.makedirs(tmp_out)

        wl_bytes_in = wl_bytes_out = total_bytes_out = 0
        _SKIP = {"__MACOSX", ".DS_Store"}

        for root, dirs, files in os.walk(src_root):
            dirs[:] = [d for d in sorted(dirs) if d not in _SKIP]
            for fname in sorted(files):
                if fname in _SKIP:
                    continue
                src = os.path.join(root, fname)
                rel = os.path.relpath(src, src_root)
                dst = os.path.join(tmp_out, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)

                entry = match_whitelist(rel, index)
                if entry:
                    wl_bytes_in += os.path.getsize(src)
                    with open(src, encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    out = _augment_file(
                        content, entry["format"], entry["json_root"],
                        multiplier, entry["datetime_fields"]
                    )
                    with open(dst, "w", encoding="utf-8") as f:
                        f.write(out)
                    wl_bytes_out += os.path.getsize(dst)
                else:
                    shutil.copy2(src, dst)

                total_bytes_out += os.path.getsize(dst)

        if os.path.exists(output_zip):
            os.remove(output_zip)
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(tmp_out):
                dirs.sort()
                for fname in sorted(files):
                    fp  = os.path.join(root, fname)
                    arc = os.path.relpath(fp, tmp_out)
                    zf.write(fp, arc)

        zip_size = os.path.getsize(output_zip)
        return wl_bytes_in, wl_bytes_out, total_bytes_out, zip_size

    finally:
        shutil.rmtree(os.path.join(data_dir, ".tmp"), ignore_errors=True)


def _fmt(b):
    if b < 1024:
        return f"{b} B"
    if b < 1024 ** 2:
        return f"{b/1024:.1f} KB"
    return f"{b/1024/1024:.2f} MB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform",   required=True, choices=["facebook", "google"])
    ap.add_argument("--multiplier", required=True, type=int)
    ap.add_argument("--data-dir",   default=None,
                    help="Directory containing *_original.zip files (default: evaluation/efficiency/data)")
    args = ap.parse_args()

    data_dir   = args.data_dir or os.path.join(_REPO_ROOT, "evaluation", "efficiency", "data")
    source_zip = os.path.join(data_dir, f"{args.platform}_original.zip")
    output_zip = os.path.join(data_dir, f"{args.platform}_{args.multiplier}x.zip")

    print(f"Augmenting {args.platform} x{args.multiplier}")
    print(f"  input:  {source_zip}")
    print(f"  output: {output_zip}")

    wl_in, wl_out, total_out, zip_size = augment_zip(
        source_zip, output_zip, args.platform, args.multiplier
    )

    w = 24
    print()
    print(f"{'':─<{w*3+4}}")
    print(f"  {'Metric':<{w}} {'Original':<{w}} {'Augmented (x{})'.format(args.multiplier)}")
    print(f"{'':─<{w*3+4}}")
    print(f"  {'Whitelisted (uncompressed)':<{w}} {_fmt(wl_in):<{w}} {_fmt(wl_out)}")
    print(f"  {'All files (uncompressed)':<{w}} {'—':<{w}} {_fmt(total_out)}")
    print(f"  {'ZIP size':<{w}} {_fmt(os.path.getsize(source_zip)):<{w}} {_fmt(zip_size)}")
    print(f"{'':─<{w*3+4}}")
    print(f"\nWritten: {output_zip}")


if __name__ == "__main__":
    main()
