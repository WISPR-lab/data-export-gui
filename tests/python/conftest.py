import os
import sys
import yaml
import pytest
from typing import List, Dict, Generator
from dataclasses import dataclass

# repo_root should be the absolute path to the root of the repository
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
if repo_root not in sys.path:
    sys.path.append(repo_root)

# pyparser_path should be the absolute path to the pyparser directory
pyparser_path = os.path.join(repo_root, "pyparser")
if pyparser_path not in sys.path:
    sys.path.append(pyparser_path)

import pyparser.schema_utils as schema_utils

@dataclass
class TestFile:
    platform: str
    filename: str
    full_path: str
    schema: List[Dict]
    expected: Dict = None

    def read_content(self) -> str:
        with open(self.full_path, "r") as f:
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
        
        self.grouped_schemas = {}
        self._load_all_schemas()

    def _load_all_schemas(self):
        platforms_cfg = self.config.get("platforms", {})
        errors = []
        for platform, info in platforms_cfg.items():
            rel_schema_path = info.get("schema_path")
            if not rel_schema_path: continue
                
            abs_schema_path = os.path.join(repo_root, rel_schema_path)
            if not os.path.exists(abs_schema_path):
                print(f"Warning: Schema for {platform} not found at {abs_schema_path}")
                continue
            
            with open(abs_schema_path, "r") as f:
                schema_dict = yaml.safe_load(f)
                grouped, platform_errors = schema_utils.group_by_file(schema_dict)
                self.grouped_schemas[platform] = grouped
                if platform_errors:
                    errors.extend(platform_errors)

        if errors:
            raise ValueError(f"Schema errors: {errors}")

    def yield_test_files(self, format_type: str) -> Generator[TestFile, None, None]:
        test_files = self.config.get("test_files", {}).get(format_type, [])
        platforms_cfg = self.config.get("platforms", {})

        for entry in test_files:
            platform = entry["platform"]
            rel_path = entry["path"]
            p_info = platforms_cfg.get(platform)
            if not p_info or "test_data_dir" not in p_info: continue

            platform_data_root = os.path.expanduser(p_info["test_data_dir"])
            inner_path = rel_path
            if inner_path.startswith(f"{platform}/"):
                inner_path = inner_path[len(platform)+1:]
            
            abs_test_data_dir = os.path.join(platform_data_root, inner_path)
            if not os.path.exists(abs_test_data_dir):
                raise FileNotFoundError(f"Test data file not found at {abs_test_data_dir}")
                continue

            manifest_key = inner_path
            schema = self.grouped_schemas.get(platform, {}).get(manifest_key, [])
            if not schema:
                basename = os.path.basename(rel_path)
                schema = self.grouped_schemas.get(platform, {}).get(basename, [])
                
            if not schema: continue

            yield TestFile(
                platform=platform,
                filename=manifest_key,
                full_path=abs_test_data_dir,
                schema=schema,
                expected=entry.get("expected")
            )

# Singleton instance
loader = TestFileLoader()





def validate_results(test_case, events, states, errors):
    # standard assertions for all parsers
    all_rows = events + states
    expected = test_case.expected or {}

    # basic sanity check
    if not expected:
        assert len(all_rows) > 0, "No data parsed and no 'expected' block provided"
    
    # count # elems
    if "num_events" in expected:
        assert len(events) == expected["num_events"]
    if "num_states" in expected:
        assert len(states) == expected["num_states"]
    
    # make sure required keys are there
    expected_keys = expected.get("keys") or expected.get("expected_keys")
    if expected_keys:
        actual_keys = set()
        if all_rows:
            actual_keys.update(all_rows[0].keys())
        assert set(expected_keys).issubset(actual_keys)

    # make sure original_record field is correct
    if "original_record" in expected:
        assert all_rows, "Cannot check original_record because no rows were parsed"
        search_term = str(expected["original_record"])
        actual_raw = str(all_rows[0].get("original_record", ""))
        assert search_term in actual_raw, f"Could not find '{search_term}' in the first row's original_record"

    # make sure categories are correct
    if "categories" in expected:
        actual_categories = {row.get("category") for row in all_rows if row.get("category")}
        expected_categories = set(expected["categories"])
        assert expected_categories.issubset(actual_categories)



def pytest_configure(config):
    # custom pytest markers
    config.addinivalue_line("markers", "format(type): parser format to test (json, csv, etc.)")

def pytest_generate_tests(metafunc):
    # global hook for pytest
    if "test_case" in metafunc.fixturenames:
        marker = metafunc.definition.get_closest_marker("format")
        if marker:
            fmt = marker.args[0]
            metafunc.parametrize("test_case", loader.yield_test_files(fmt), ids=str)
