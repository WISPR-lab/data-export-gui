#!/usr/bin/env bash
# Syncs static assets that Webpack cannot bundle into public/.
# By default uses symlinks so edits in src/ are reflected immediately.
# For CI/build, use --copy to create actual copies instead.
# Usage: ./sync_assets.sh [--symlink|--copy]

set -euo pipefail

WEBAPP_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$WEBAPP_DIR/.." && pwd)"
PUBLIC="$WEBAPP_DIR/public"
PYTHON_CORE_DIR="$REPO_ROOT/python_core"

# Parse mode argument
LINK_MODE="${1:---symlink}"

case "$LINK_MODE" in
  --symlink)
    LINK_DIR_CMD="ln -sf"
    LINK_FILE_CMD="ln -sf"
    echo "[sync-assets] Using symlinks (dev mode)"
    ;;
  --copy)
    LINK_DIR_CMD="cp -r"
    LINK_FILE_CMD="cp"
    echo "[sync-assets] Using copies (build mode)"
    ;;
  *)
    echo "Usage: $0 [--symlink|--copy]"
    echo "  --symlink  Use symlinks (default, for development)"
    echo "  --copy     Use copies (for CI/production builds)"
    exit 1
    ;;
esac


if [ ! -d "$REPO_ROOT/UA-Extract-purepy" ]; then
  echo "[sync-assets] ERROR: UA-Extract-purepy submodule not found!"
  echo ""
  echo "To initialize the submodule, run:"
  echo "  cd $REPO_ROOT"
  echo "  git submodule update --init --recursive"
  echo ""
  exit 1
fi

bash "$REPO_ROOT/UA-Extract-purepy/build_wheels.sh"


rm -rf \
  "$PUBLIC/python_core.zip" \
  "$PUBLIC/manifests" \
  "$PUBLIC/sqlite-wasm" \
  "$PUBLIC/sqlite-worker.js" \
  "$PUBLIC/pyodide-worker.js" \
  "$PUBLIC/config.yaml" \
  "$PUBLIC/schema.sql" \
  "$PUBLIC/wheels"


# Create wheels directory and copy .whl AND the pointer file
mkdir -p "$PUBLIC/wheels"
DIST_DIR="$REPO_ROOT/UA-Extract-purepy/dist"

if [ "$LINK_MODE" = "--symlink" ]; then
  # Link wheels
  for wheel in "$DIST_DIR"/*.whl; do
    [ -f "$wheel" ] && ln -sf "$wheel" "$PUBLIC/wheels/$(basename "$wheel")"
  done
  # Link the pointer file so the worker knows which version to load
  ln -sf "$DIST_DIR/latest_wheel.txt" "$PUBLIC/wheels/latest_wheel.txt"
else
  # Copy wheels and pointer
  cp "$DIST_DIR"/*.whl "$PUBLIC/wheels/" 2>/dev/null || true
  cp "$DIST_DIR/latest_wheel.txt" "$PUBLIC/wheels/" 2>/dev/null || true
fi

$LINK_DIR_CMD "$REPO_ROOT/manifests"                     "$PUBLIC/manifests"
$LINK_FILE_CMD "$WEBAPP_DIR/src/pyodide/pyodide-worker.js"         "$PUBLIC/pyodide-worker.js"
$LINK_FILE_CMD "$WEBAPP_DIR/src/database/sqlite-worker.js"         "$PUBLIC/sqlite-worker.js"


(cd "$REPO_ROOT" && zip -r "$PUBLIC/python_core.zip" python_core -q)
echo "[sync-assets] Created: python_core.zip"


cp -r "$WEBAPP_DIR/node_modules/@sqlite.org/sqlite-wasm/dist" "$PUBLIC/sqlite-wasm"
cp    "$REPO_ROOT/config.yaml" "$PUBLIC/config.yaml"
cp    "$REPO_ROOT/schema.sql"  "$PUBLIC/schema.sql"

echo "[sync-assets] Done."
