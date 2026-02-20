#!/usr/bin/env bash
# Syncs static assets that Webpack cannot bundle into public/.
# Symlinks are used so edits in src/ are reflected immediately without re-running.
# Called automatically by `yarn serve` and `yarn build`.

set -euo pipefail

WEBAPP_DIR="$(cd "$(dirname "$0")" && pwd)"
PUBLIC="$WEBAPP_DIR/public"
PYTHON_CORE_DIR="$WEBAPP_DIR/../python_core"

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

# ── Symlink source files (edits are live immediately) ───────────────────────
ln -s "../../python_core"                        "$PUBLIC/python_core"
ln -s "../../manifests"                          "$PUBLIC/manifests"
ln -s "../src/pyodide/pyodide-worker.js"         "$PUBLIC/pyodide-worker.js"
ln -s "../src/database/sqlite-worker.js"          "$PUBLIC/sqlite-worker.js"

# ── Copy assets that need a build-time snapshot ─────────────────────────────
cp -r "$WEBAPP_DIR/node_modules/@sqlite.org/sqlite-wasm/dist" "$PUBLIC/sqlite-wasm"
cp    "$WEBAPP_DIR/../config.yaml" "$PUBLIC/config.yaml"
cp    "$WEBAPP_DIR/../schema.sql"  "$PUBLIC/schema.sql"

# ── Generate dynamic Python manifest ─────────────────────────────────────────
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
