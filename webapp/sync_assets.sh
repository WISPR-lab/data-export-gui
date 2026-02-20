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

# ── Clean previous artefacts ────────────────────────────────────────────────
rm -rf \
  "$PUBLIC/python_core" \
  "$PUBLIC/manifests" \
  "$PUBLIC/sqlite-wasm" \
  "$PUBLIC/sqlite-worker.js" \
  "$PUBLIC/pyodide-worker.js" \
  "$PUBLIC/config.yaml" \
  "$PUBLIC/schema.sql" \
  "$PUBLIC/_dynamic_py_manifest.json"

# ── Link or copy source files ───────────────────────────────────────────────
$LINK_DIR_CMD "$REPO_ROOT/python_core"                   "$PUBLIC/python_core"
$LINK_DIR_CMD "$REPO_ROOT/manifests"                     "$PUBLIC/manifests"
$LINK_FILE_CMD "$WEBAPP_DIR/src/pyodide/pyodide-worker.js"         "$PUBLIC/pyodide-worker.js"
$LINK_FILE_CMD "$WEBAPP_DIR/src/database/sqlite-worker.js"         "$PUBLIC/sqlite-worker.js"

# ── Copy assets that always need a build-time snapshot ─────────────────────
cp -r "$WEBAPP_DIR/node_modules/@sqlite.org/sqlite-wasm/dist" "$PUBLIC/sqlite-wasm"
cp    "$REPO_ROOT/config.yaml" "$PUBLIC/config.yaml"
cp    "$REPO_ROOT/schema.sql"  "$PUBLIC/schema.sql"

# ── Generate dynamic Python manifest ────────────────────────────────────────
generate_manifest() {
  local output_file="$1"
  local python_core_dir="$2"
  
  {
    echo "{"
    
    # Core files
    echo '  "core_files": ['
    find "$python_core_dir" -maxdepth 1 -name "*.py" -type f -exec basename {} \; | sort | sed 's/^/    "/' | sed 's/$/"/' | paste -sd ',' - | sed 's/,$//'
    echo "  ],"
    
    # Extractors
    echo '  "extractors": ['
    find "$python_core_dir/extractors" -maxdepth 1 -name "*.py" -type f -exec basename {} \; | sort | sed 's/^/    "/' | sed 's/$/"/' | paste -sd ',' - | sed 's/,$//'
    echo "  ],"
    
    # Semantic map
    echo '  "semantic_map": ['
    find "$python_core_dir/semantic_map" -maxdepth 1 -name "*.py" -type f -exec basename {} \; | sort | sed 's/^/    "/' | sed 's/$/"/' | paste -sd ',' - | sed 's/,$//'
    echo "  ],"
    
    # Utils
    echo '  "utils": ['
    find "$python_core_dir/utils" -maxdepth 1 -name "*.py" -type f -exec basename {} \; | sort | sed 's/^/    "/' | sed 's/$/"/' | paste -sd ',' - | sed 's/,$//'
    echo "  ]"
    
    echo "}"
  } > "$output_file"
}

generate_manifest "$PUBLIC/_dynamic_py_manifest.json" "$PYTHON_CORE_DIR"
echo "[sync-assets] Generated: _dynamic_py_manifest.json"

echo "[sync-assets] Done."
