#!/usr/bin/env bash
# Syncs static assets that Webpack cannot bundle into public/.
# Symlinks are used so edits in src/ are reflected immediately without re-running.
# Called automatically by `yarn serve` and `yarn build`.

set -euo pipefail

WEBAPP_DIR="$(cd "$(dirname "$0")" && pwd)"
PUBLIC="$WEBAPP_DIR/public"

# ── Clean previous artefacts ────────────────────────────────────────────────
rm -rf \
  "$PUBLIC/python_core" \
  "$PUBLIC/manifests" \
  "$PUBLIC/sqlite-wasm" \
  "$PUBLIC/sqlite-worker.js" \
  "$PUBLIC/pyodide-worker.js" \
  "$PUBLIC/config.yaml" \
  "$PUBLIC/schema.sql"

# ── Symlink source files (edits are live immediately) ───────────────────────
ln -s "../../python_core"                        "$PUBLIC/python_core"
ln -s "../../manifests"                          "$PUBLIC/manifests"
ln -s "../src/pyodide/pyodide-worker.js"         "$PUBLIC/pyodide-worker.js"
ln -s "../src/database/sqlite-worker.js"          "$PUBLIC/sqlite-worker.js"

# ── Copy assets that need a build-time snapshot ─────────────────────────────
cp -r "$WEBAPP_DIR/node_modules/@sqlite.org/sqlite-wasm/dist" "$PUBLIC/sqlite-wasm"
cp    "$WEBAPP_DIR/../config.yaml" "$PUBLIC/config.yaml"
cp    "$WEBAPP_DIR/../schema.sql"  "$PUBLIC/schema.sql"

echo "[sync-assets] Done."
