#!/usr/bin/env bash
# Syncs static assets that Webpack cannot bundle into public/.
# Usage: ./sync_assets.sh



set -euo pipefail


WEBAPP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$WEBAPP_DIR/.." && pwd)"
PUBLIC="$WEBAPP_DIR/public"
WHEELS_DIR="$PUBLIC/wheels"
PYODIDE_DIR="$PUBLIC/pyodide"
VENDOR_DIR="$PUBLIC/vendor"
SUBMODULE_DIR="$REPO_ROOT/UA-Extract-purepy"


# pre-flight checks


if [ ! -d "$SUBMODULE_DIR" ]; then
  echo "[sync-assets] ERROR: Submodule 'UA-Extract-purepy' is missing."
  echo "Run: git submodule update --init --recursive"
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
  "$PUBLIC/schema.sql" \
  "$WHEELS_DIR" \
  "$PYODIDE_DIR"

mkdir -p "$WHEELS_DIR" "$PYODIDE_DIR" "$PUBLIC" "$VENDOR_DIR"


# ------------------------------------- 


echo "[sync-assets] Building UA-Extract-purepy submodule wheels..."
bash "$SUBMODULE_DIR/build_wheels.sh"

DIST_DIR="$SUBMODULE_DIR/dist"

echo "[sync-assets] Syncing UA-Extract-purepy submodule wheels..."
local_wheels=("$DIST_DIR"/*.whl)

if [ ${#local_wheels[@]} -eq 0 ]; then
echo "[sync-assets] ERROR: No .whl files found in $DIST_DIR"
exit 1
fi

for wheel in "${local_wheels[@]}"; do
cp -f "$wheel" "$WHEELS_DIR/$(basename "$wheel")"
done

if [ -f "$DIST_DIR/latest_wheel.txt" ]; then
cp -f "$DIST_DIR/latest_wheel.txt" "$WHEELS_DIR/latest_wheel.txt"
fi

echo "[sync-assets] Downloading third-party PyPI dependencies into $WHEELS_DIR..."
PIP_CMD=""
if command -v pip3 &> /dev/null; then
  PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
  PIP_CMD="pip"
elif python3 -m pip --version &> /dev/null; then
  PIP_CMD="python3 -m pip"
fi

if [ -n "$PIP_CMD" ]; then
  $PIP_CMD download -d "$WHEELS_DIR" --only-binary=:all: \
    pyyaml \
    regex \
    aiohttp \
    pytz \
    pandas \
    hjson \
    json5 \
    tenacity \
    "rich==13.7.1" \
    "typer==0.9.0" \
    exrex \
    beautifulsoup4 \
    packaging \
    tqdm \
    || true
else
  echo "[sync-assets] WARNING: Neither 'pip3' nor 'pip' found in PATH."
fi


# ------------------------------------- 


PYODIDE_VERSION="0.27.2"
echo "[sync-assets] Syncing Pyodide v${PYODIDE_VERSION} runtime binaries..."

PYODIDE_CDN="https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full"
PYODIDE_FILES=("pyodide.js" "pyodide.wasm" "pyodide-lock.json" "python_stdlib.zip")
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



echo "[sync-assets] Zipping and copying python_core..."
(cd "$REPO_ROOT" && zip -r "$PUBLIC/python_core.zip" python_core -q)



echo "[sync-assets] Copying SQLite WASM binaries and schema ..."
SQLITE_WASM_DIR="$WEBAPP_DIR/node_modules/@sqlite.org/sqlite-wasm/dist"
if [ -d "$SQLITE_WASM_DIR" ]; then
  cp -rf "$SQLITE_WASM_DIR" "$PUBLIC/sqlite-wasm"
fi



# -------------------------------------

echo "[sync-assets] Done."




