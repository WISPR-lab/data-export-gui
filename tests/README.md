# Tests

Standard tests (Run from `webapp` directory):
```bash
cd webapp
yarn vitest
```

## Testing with real files
1. Put ZIPs in `tests/zip_data/`.
2. Name them `facebook.zip`, `apple.zip`, etc. (see/edit `REAL_DATA_MAPPING` in `tests/js/upload.test.js` for more config)
3. Run (from project root):
   ```bash
   cd webapp
   yarn vitest run ../tests/js/upload.test.js
   ```

## Structure
- `js/`: Frontend logic tests (Vitest).
- `python/`: Backend/Parser tests.
- `zip_data/`: Git-ignored directory for real ZIP archive testing.
- `tmp_outputs/`: Directory for debug logs and JSON output dumps.

The test uses the mapping at the top of `upload.test.js`. Everything in `zip_data/` is git-ignored.
