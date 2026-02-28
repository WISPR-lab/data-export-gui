import os
import sys
import yaml
import pytest
from typing import List, Dict, Generator, Optional
from dataclasses import dataclass, field

# repo_root: absolute path to repo root
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.append(repo_root)

python_core_path = os.path.join(repo_root, "python_core")
if python_core_path not in sys.path:
    sys.path.insert(0, python_core_path)

from manifest import Manifest

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

# Singleton instance
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
