# Tests

The test suite is Pytest only. Run it from the project root:

```bash
# via Docker
docker compose run --rm test tests/python                        # everything
docker compose run --rm test tests/python/test_device_grouping2.py  # one file

# without Docker
uv sync
uv run pytest tests/python
uv run pytest tests/python/test_device_grouping2.py
```

## Structure

- `python/`: parser, semantic-map, normalization, and device-grouping tests.
- `python/conftest.py`: shared fixtures, plus the `TestFileLoader` that drives the real-data tests below.
- `python/test_config.yaml`: maps parser formats to real export files on your machine (see below).
- `zip_data/`, `tmp_outputs/`: git-ignored scratch directories for real archives and debug dumps.

Most tests are self-contained and use inline fixtures. The parser tests under `python/extractors/` are the
exception: they are parameterized over `test_config.yaml` and need real data.

## Running the parser tests against real exports

`test_config.yaml` has two sections. `platforms:` gives a directory per platform, and `test_files:` lists
individual files within those directories grouped by parser format, each with the record count and raw keys
the parser should produce:

```yaml
platforms:
  facebook:
    test_data_dir: "~/takeout-test-data/facebook"

test_files:
  json:
    - path: "facebook/security_and_login_information/account_activity.json"
      platform: "facebook"
      expected:
        num_records: 59
        raw_keys: ['action', 'timestamp', 'ip_address']
```

**No export data ships with this repository.** The paths above are placeholders, so point `test_data_dir` at
your own unpacked exports. Any file that isn't found is skipped with a `Warning: test data not found at ...`
line rather than failing, so a clean checkout reports these tests as passing while actually running none of
them. Check the warnings if you expect real coverage.

Supported `expected:` keys are `num_records` (exact), `min_records` (lower bound), and `raw_keys` (fields
that must appear in the first parsed record). A file with no `expected:` block only asserts that at least
one record came out.

If you want data to point this at, the two synthetic exports in `evaluation/efficiency/data/` unpack into
the right shape. See the *Sample Data* section of the root `README.md`.
