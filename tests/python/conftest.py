import os
import sys
import yaml
import pytest
import tempfile
import shutil
import json
import uuid
import zipfile
from typing import Dict, Generator, Tuple
from dataclasses import dataclass, field

repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.append(repo_root)

python_core_path = os.path.join(repo_root, "python_core")
if python_core_path not in sys.path:
    sys.path.insert(0, python_core_path)

from manifest import Manifest
from db_session import DatabaseSession

def init_db(db_path: str) -> None:
    """Initialize database with schema.sql."""
    schema_path = os.path.join(repo_root, 'schema.sql')
    with DatabaseSession(db_path, schema_path=schema_path) as conn:
        pass

@dataclass
class TestFile:
    platform: str
    filename: str
    full_path: str
    parser_cfg: Dict = field(default_factory=dict)
    expected: Dict = None

    def read_content(self) -> str:
        with open(self.full_path, "r", encoding='utf-8', errors='replace') as f:
            return f.read()

    def __repr__(self):
        return f"{self.platform} | {self.filename}"

class TestFileLoader:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(__file__), "test_config.yaml")
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Test config not found at {self.config_path}")
        
        with open(self.config_path, "r") as f:
            self.config = yaml.safe_load(f)
        
        self.manifests = {}  # platform -> Manifest instance
        self._load_manifests()

    def _load_manifests(self):
        manifests_dir = os.path.join(repo_root, "manifests")
        platforms_cfg = self.config.get("platforms", {})
        for platform in platforms_cfg:
            try:
                self.manifests[platform] = Manifest(
                    platform=platform,
                    manifest_dir=manifests_dir,
                    validate=False,
                )
            except Exception as e:
                print(f"Warning: could not load manifest for {platform}: {e}")

    def yield_test_files(self, format_type: str) -> Generator[TestFile, None, None]:
        test_files = self.config.get("test_files", {}).get(format_type, [])
        platforms_cfg = self.config.get("platforms", {})

        for entry in test_files:
            platform = entry["platform"]
            rel_path = entry["path"]
            p_info = platforms_cfg.get(platform)
            if not p_info or "test_data_dir" not in p_info:
                continue

            platform_data_root = os.path.expanduser(p_info["test_data_dir"])
            inner_path = rel_path
            if inner_path.startswith(f"{platform}/"):
                inner_path = inner_path[len(platform)+1:]

            abs_path = os.path.join(platform_data_root, inner_path)
            if not os.path.exists(abs_path):
                print(f"Warning: test data not found at {abs_path}, skipping.")
                continue

            manifest = self.manifests.get(platform)
            parser_cfg = manifest.get_file_cfg(inner_path).get('parser', {}) if manifest else {}

            yield TestFile(
                platform=platform,
                filename=inner_path,
                full_path=abs_path,
                parser_cfg=parser_cfg,
                expected=entry.get("expected"),
            )

loader = TestFileLoader()

def validate_results(test_case, records: list):
    """Standard assertions for all parsers. records is a flat List[Dict]."""
    expected = test_case.expected or {}

    if not expected:
        assert len(records) > 0, f"No records parsed from {test_case.filename} and no 'expected' block provided"

    if "num_records" in expected:
        assert len(records) == expected["num_records"], (
            f"Expected {expected['num_records']} records, got {len(records)}"
        )

    if "min_records" in expected:
        assert len(records) >= expected["min_records"], (
            f"Expected at least {expected['min_records']} records, got {len(records)}"
        )

    raw_keys = expected.get("raw_keys") or []
    if raw_keys:
        assert records, "Cannot check raw_keys — no records were parsed"
        actual_keys = set(records[0].keys())
        missing = set(raw_keys) - actual_keys
        assert not missing, f"Expected raw field(s) {missing} in first record. Got: {actual_keys}"

def pytest_configure(config):
    config.addinivalue_line("markers", "format(type): parser format to test (json, csv, etc.)")

def pytest_generate_tests(metafunc):
    if "test_case" in metafunc.fixturenames:
        marker = metafunc.definition.get_closest_marker("format")
        if marker:
            fmt = marker.args[0]
            metafunc.parametrize("test_case", loader.yield_test_files(fmt), ids=str)


@pytest.fixture(scope="function")
def test_db_path():
    """Test database in tests/tmp_outputs."""
    tmpdir = os.path.join(os.path.dirname(__file__), '..', 'tmp_outputs')
    os.makedirs(tmpdir, exist_ok=True)
    db_path = os.path.join(tmpdir, 'test.db')
    if os.path.exists(db_path):
        os.remove(db_path)
    init_db(db_path)
    yield db_path

@pytest.fixture(autouse=True)
def inject_test_config(test_db_path):
    """Inject test DB_PATH into builtins so get_config_value() works."""
    import builtins
    original_db_path = getattr(builtins, 'DB_PATH', None)
    original_schema_path = getattr(builtins, 'SCHEMA_PATH', None)
    original_manifests = getattr(builtins, 'MANIFESTS_DIR', None)
    original_temp_zip = getattr(builtins, 'TEMP_ZIP_DATA_STORAGE', None)
    
    builtins.DB_PATH = test_db_path
    builtins.SCHEMA_PATH = os.path.join(repo_root, 'schema.sql')
    builtins.MANIFESTS_DIR = os.path.join(repo_root, 'manifests')
    builtins.TEMP_ZIP_DATA_STORAGE = tempfile.mkdtemp(prefix='pytest_temp_zip_')
    
    yield
    
    if original_db_path:
        builtins.DB_PATH = original_db_path
    elif hasattr(builtins, 'DB_PATH'):
        delattr(builtins, 'DB_PATH')
    if original_schema_path:
        builtins.SCHEMA_PATH = original_schema_path
    elif hasattr(builtins, 'SCHEMA_PATH'):
        delattr(builtins, 'SCHEMA_PATH')
    if original_manifests:
        builtins.MANIFESTS_DIR = original_manifests
    elif hasattr(builtins, 'MANIFESTS_DIR'):
        delattr(builtins, 'MANIFESTS_DIR')
    if original_temp_zip:
        builtins.TEMP_ZIP_DATA_STORAGE = original_temp_zip
    elif hasattr(builtins, 'TEMP_ZIP_DATA_STORAGE'):
        delattr(builtins, 'TEMP_ZIP_DATA_STORAGE')
    if hasattr(builtins, 'TEMP_ZIP_DATA_STORAGE') and os.path.exists(builtins.TEMP_ZIP_DATA_STORAGE):
        shutil.rmtree(builtins.TEMP_ZIP_DATA_STORAGE, ignore_errors=True)

@pytest.fixture(scope="session")
def facebook_zip_path():
    """Path to facebook.zip test data."""
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'zip_data', 'facebook.zip')
    if not os.path.exists(path):
        pytest.skip(f"facebook.zip not found at {path}")
    return path

@pytest.fixture(scope="session")
def instagram_zip_path():
    """Path to instagram.zip test data."""
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'zip_data', 'instagram.zip')
    if not os.path.exists(path):
        pytest.skip(f"instagram.zip not found at {path}")
    return path

@pytest.fixture(scope="function")
def sample_upload_with_raw_data(test_db_path, facebook_zip_path) -> Tuple[str, int]:
    """
    Extract facebook.zip to temp dir, load raw JSON files into test DB as raw_data.
    Only includes files with valid manifest_file_id entries (files with views).
    Returns (upload_id, num_files) for use by downstream tests.
    
    This fixture is used by semantic_map and other tests that need extraction input.
    Module-scoped: created once per test module, persists across tests.
    """
    manifests_dir = os.path.join(repo_root, 'manifests')
    manifest = Manifest(platform='facebook', manifest_dir=manifests_dir, validate=False)
    
    with tempfile.TemporaryDirectory(prefix='pytest_extract_') as tmpdir:
        with zipfile.ZipFile(facebook_zip_path, 'r') as z:
            z.extractall(tmpdir)
        
        upload_id = str(uuid.uuid4())
        raw_data_count = 0
        
        schema_path = os.path.join(repo_root, 'schema.sql')
        with DatabaseSession(test_db_path, schema_path=schema_path) as conn:
            conn.execute(
                'INSERT INTO uploads (id, platform, given_name) VALUES (?, ?, ?)',
                (upload_id, 'facebook', f'test-facebook')
            )
            
            for root, dirs, filenames in os.walk(tmpdir):
                for filename in filenames:
                    if filename.endswith('.json'):
                        filepath = os.path.join(root, filename)
                        rel_path = os.path.relpath(filepath, tmpdir)
                        
                        # Strip platform prefix (e.g., 'facebook/path/to/file.json' -> 'path/to/file.json')
                        if rel_path.startswith('facebook/'):
                            manifest_path = rel_path[len('facebook/'):]
                        else:
                            manifest_path = rel_path
                        
                        # Use get_file_cfg which handles path matching (including Pyodide underscore flattening)
                        file_cfg = manifest.get_file_cfg(manifest_path)
                        manifest_file_id = file_cfg.get('id')
                        
                        # Only insert files with valid manifest_file_id (files with views)
                        if manifest_file_id:
                            file_id = str(uuid.uuid4())
                            
                            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                                content = f.read()
                            
                            # Use the actual parser to extract records according to json_root
                            from python_core.extractors.json_ import JSONParser
                            from python_core.extractors.json_label_values import JSONLabelValuesParser
                            
                            parser_cfg = file_cfg.get('parser', {})
                            fmt = parser_cfg.get('format')
                            
                            parser = None
                            if fmt == 'json':
                                parser = JSONParser()
                            elif fmt == 'json_label_values':
                                parser = JSONLabelValuesParser()
                            
                            try:
                                records = parser.extract(content, parser_cfg) if parser else []
                            except Exception:
                                records = []
                            
                            if records:
                                conn.execute(
                                    'INSERT INTO uploaded_files (id, upload_id, opfs_filename, manifest_file_id) VALUES (?, ?, ?, ?)',
                                    (file_id, upload_id, filename, manifest_file_id)
                                )
                                
                                for record in records:
                                    raw_data_id = str(uuid.uuid4())
                                    conn.execute(
                                        'INSERT INTO raw_data (id, upload_id, file_id, data) VALUES (?, ?, ?, ?)',
                                        (raw_data_id, upload_id, file_id, json.dumps(record))
                                    )
                                    raw_data_count += 1
            
            conn.commit()
    
    return upload_id, raw_data_count
