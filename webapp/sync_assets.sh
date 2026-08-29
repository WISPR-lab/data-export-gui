#!/usr/bin/env bash
# Syncs static assets that Webpack cannot bundle into public/.
# Usage: ./sync_assets.sh



set -euo pipefail


WEBAPP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$WEBAPP_DIR/.." && pwd)"
PUBLIC="$WEBAPP_DIR/public"
PYODIDE_DIR="$PUBLIC/pyodide"
VENDOR_DIR="$PUBLIC/vendor"
UA_EXTRACT_DIR="$REPO_ROOT/UA-Extract-purepy"  # vendored, not a submodule


# pre-flight checks


if [ ! -d "$UA_EXTRACT_DIR" ]; then
  echo "[sync-assets] ERROR: 'UA-Extract-purepy/' is missing from the repository root."
  echo "It is vendored directly into this repo - re-clone or re-download the source to restore it."
  exit 1
fi

if ! command -v zip &> /dev/null || ! command -v curl &> /dev/null; then
  echo "[sync-assets] ERROR: 'zip' and 'curl' are required build dependencies."
  exit 1
fi

# -------------------------------------


echo "[sync-assets] cleaning up old assets..."
rm -rf \
  "$PUBLIC/python_core.zip" \
  "$PUBLIC/manifests" \
  "$PUBLIC/sqlite-wasm" \
  "$PUBLIC/sqlite-worker.js" \
  "$PUBLIC/pyodide-worker.js" \
  "$PUBLIC/config.yaml" \
  "$PUBLIC/schema.sql"

mkdir -p "$PYODIDE_DIR" "$PUBLIC" "$VENDOR_DIR"


# ------------------------------------- 


echo "[sync-assets] Building UA-Extract-purepy wheel..."
bash "$UA_EXTRACT_DIR/build_wheels.sh"

DIST_DIR="$UA_EXTRACT_DIR/dist"

echo "[sync-assets] Syncing UA-Extract-purepy wheel..."
local_wheels=("$DIST_DIR"/*.whl)

# An unmatched glob stays literal, so test the first entry rather than the array length.
if [ ! -e "${local_wheels[0]}" ]; then
echo "[sync-assets] ERROR: No .whl files found in $DIST_DIR"
echo "[sync-assets] build_wheels.sh ran but produced nothing - check its output above."
exit 1
fi

for wheel in "${local_wheels[@]}"; do
cp -f "$wheel" "$PYODIDE_DIR/$(basename "$wheel")"
done



PYODIDE_VERSION="0.27.2"
PYODIDE_CDN="https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full"

# Top-level Pyodide-native packages (transitive deps resolved automatically from lock file)
# These go to $PYODIDE_DIR so loadPackage(indexURL=/pyodide/) can find them.
PYODIDE_NATIVE_PACKAGES=(
  "sqlite3" "pandas" "pyyaml" "numpy" "micropip" "packaging"
  "python-dateutil" "pytz" "tzdata"
  "beautifulsoup4" "soupsieve"
  "tqdm"
  "rich" "pygments"
  "click"
  "typing-extensions"
  "regex"
  "aiohttp" "aiosignal" "async-timeout" "attrs"
  "charset-normalizer" "frozenlist" "idna" "multidict" "yarl"
  "future"
)

# Pure-Python packages not in Pyodide's distribution — installed via micropip from $PYODIDE_DIR
PURE_PYTHON_PACKAGES=("hjson==3.1.0" "json5==0.9.16" "typer==0.9.0" "tenacity>=8.3.0" "exrex==0.12.0" "ahocorapy==1.6.2")


echo "[sync-assets] Resolving Pyodide package tree (including transitive deps)..."
LOCK_FILE_TMP="/tmp/pyodide-lock-${PYODIDE_VERSION}.json"
if [ ! -f "$LOCK_FILE_TMP" ]; then
  curl -sL "$PYODIDE_CDN/pyodide-lock.json" -o "$LOCK_FILE_TMP"
fi

# Resolve all transitive deps and print filenames, one per line
python3 - "$LOCK_FILE_TMP" "${PYODIDE_NATIVE_PACKAGES[@]}" > /tmp/pyodide_resolved_files.txt 2>/tmp/pyodide_resolve_warn.txt <<'PYEOF'
import json, sys

with open(sys.argv[1]) as f:
    lock = json.load(f)

pkgs = lock.get('packages', {})

def norm(name):
    return name.lower().replace('-', '_')

def resolve(pkg_name, visited):
    key = norm(pkg_name)
    if key in visited:
        return
    match = next((v for k, v in pkgs.items() if norm(k) == key), None)
    if match is None:
        print(f"[WARN] {pkg_name} not in pyodide-lock.json", file=sys.stderr)
        return
    visited.add(key)
    for dep in match.get('depends', []):
        resolve(dep, visited)

requested = sys.argv[2:]
visited = set()
for p in requested:
    resolve(p, visited)

for key in sorted(visited):
    match = next((v for k, v in pkgs.items() if norm(k) == key), None)
    if match:
        print(match['file_name'])
PYEOF

cat /tmp/pyodide_resolve_warn.txt >&2

echo "[sync-assets] Downloading Pyodide packages (+ transitive deps) to $PYODIDE_DIR..."
while IFS= read -r filename; do
  [ -z "$filename" ] && continue
  if [ ! -f "$PYODIDE_DIR/$filename" ]; then
    echo "  -> $filename"
    curl -sL "$PYODIDE_CDN/$filename" -o "$PYODIDE_DIR/$filename"
  fi
done < /tmp/pyodide_resolved_files.txt

# Write package name index for the worker to call loadPackage([...names...])
python3 -c "import json, sys; print(json.dumps(sys.argv[1:]))" "${PYODIDE_NATIVE_PACKAGES[@]}" > "$PYODIDE_DIR/pyodide_packages_index.json"


echo "[sync-assets] Downloading pure-Python packages via pip..."
PIP_CMD=""
if command -v pip3 &> /dev/null; then
  PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
  PIP_CMD="pip"
elif python3 -m pip --version &> /dev/null; then
  PIP_CMD="python3 -m pip"
fi

if [ -n "$PIP_CMD" ]; then
  for pkg in "${PURE_PYTHON_PACKAGES[@]}"; do
    echo "  -> $pkg"
    $PIP_CMD download "$pkg" --no-deps -d "$PYODIDE_DIR" \
      --python-version 3.12 --implementation py --abi none --platform any \
      --only-binary=:all: -q
  done
else
  echo "[sync-assets] WARNING: pip not found — skipping pure-Python packages."
fi


echo "[sync-assets] Generating wheels_index.json manifest..."
(cd "$PYODIDE_DIR" && python3 -c 'import os, json; print(json.dumps(sorted([f for f in os.listdir(".") if f.endswith(".whl")])))' > wheels_index.json)



# ------------------------------------- 


echo "[sync-assets] Syncing Pyodide v${PYODIDE_VERSION} runtime binaries..."

PYODIDE_FILES=("pyodide.js" "pyodide.asm.js" "pyodide.asm.wasm" "pyodide-lock.json" "python_stdlib.zip" "micropip-0.8.0-py3-none-any.whl" "packaging-24.2-py3-none-any.whl")
for file in "${PYODIDE_FILES[@]}"; do
  if [ ! -f "$PYODIDE_DIR/$file" ]; then
    echo "  -> Downloading $file"
    curl -sL "$PYODIDE_CDN/$file" -o "$PYODIDE_DIR/$file"
  fi
done


# -------------------------------------


echo "[sync-assets] Copying manifests, worker scripts, and schema..."
mkdir -p "$PUBLIC/manifests"
manifest_files=("$REPO_ROOT/manifests"/*.yaml)
if [ ${#manifest_files[@]} -gt 0 ]; then
  cp -f "${manifest_files[@]}" "$PUBLIC/manifests/"
fi

cp -f "$WEBAPP_DIR/src/pyodide/pyodide-worker.js" "$PUBLIC/pyodide-worker.js"
cp -f "$WEBAPP_DIR/src/database/sqlite-worker.js" "$PUBLIC/sqlite-worker.js"
cp -f "$REPO_ROOT/config.yaml" "$PUBLIC/config.yaml"
cp -f "$REPO_ROOT/schema.sql"  "$PUBLIC/schema.sql"

# PERFORMANCE_MEMORY_SAMPLING=1 (or "true") flips memory_sampling_enabled on in the *public* config.yaml copy only.
if [ "${PERFORMANCE_MEMORY_SAMPLING:-}" = "1" ] || [ "${PERFORMANCE_MEMORY_SAMPLING:-}" = "true" ]; then
  echo "[sync-assets] PERFORMANCE_MEMORY_SAMPLING set — enabling memory_sampling_enabled in public/config.yaml"
  sed -i.bak 's/memory_sampling_enabled: false/memory_sampling_enabled: true/' "$PUBLIC/config.yaml"
  rm -f "$PUBLIC/config.yaml.bak"
fi



echo "[sync-assets] Zipping and copying python_core..."
(cd "$REPO_ROOT" && zip -r "$PUBLIC/python_core.zip" python_core -q)



echo "[sync-assets] Copying SQLite WASM binaries and schema ..."
SQLITE_WASM_DIR="$WEBAPP_DIR/node_modules/@sqlite.org/sqlite-wasm/dist"
if [ -d "$SQLITE_WASM_DIR" ]; then
  cp -rf "$SQLITE_WASM_DIR" "$PUBLIC/sqlite-wasm"
fi



echo "[sync-assets] Copying vendor dependencies from node_modules..."
mkdir -p "$VENDOR_DIR"
if [ -f "$WEBAPP_DIR/node_modules/js-yaml/dist/js-yaml.min.js" ]; then
  cp -f "$WEBAPP_DIR/node_modules/js-yaml/dist/js-yaml.min.js" "$VENDOR_DIR/js-yaml.min.js"
fi
if [ -f "$WEBAPP_DIR/node_modules/coi-serviceworker/coi-serviceworker.min.js" ]; then
  # cp -f "$WEBAPP_DIR/node_modules/coi-serviceworker/coi-serviceworker.min.js" "$VENDOR_DIR/coi-serviceworker.min.js"
  cp -f "$WEBAPP_DIR/node_modules/coi-serviceworker/coi-serviceworker.min.js" "$WEBAPP_DIR/public/coi-serviceworker.min.js"
fi

# -------------------------------------

echo "[sync-assets] Done."




