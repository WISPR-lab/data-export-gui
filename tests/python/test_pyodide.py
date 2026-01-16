import pytest
import os
import yaml
from pyparser.pyodide import parse

@pytest.mark.format("json")
def test_pyodide_json_sanity(test_case):
    # Basic sanity check for the pyodide bridge with json data
    from conftest import loader, repo_root
    
    # full schema string for the platform
    platform_info = loader.config["platforms"][test_case.platform]
    schema_path = os.path.join(repo_root, platform_info["schema_path"])
    
    with open(schema_path, "r") as f:
        schema_str = f.read()

    content = test_case.read_content()
    
    # main pyodide entry point
    result = parse(schema_str, content, test_case.filename)
    
    assert "fatal" in result, "Result should have 'fatal' key"
    assert result.get("fatal") is False, f"Fatal error occurred: {result.get('errors')}"
    
    total_records = len(result.get("events", [])) + len(result.get("states", []))
    assert total_records > 0, f"No records parsed for {test_case.filename} via Pyodide bridge"



@pytest.mark.format("csv")
def test_pyodide_csv_sanity(test_case):
    # Basic sanity check for the pyodide bridge with csv data
    from conftest import loader, repo_root
    
    # full schema string for the platform
    platform_info = loader.config["platforms"][test_case.platform]
    schema_path = os.path.join(repo_root, platform_info["schema_path"])
    
    with open(schema_path, "r") as f:
        schema_str = f.read()

    content = test_case.read_content()

    # main pyodide entry point
    result = parse(schema_str, content, test_case.filename)
    
    assert result.get("fatal") is False, f"Fatal error occurred: {result.get('errors')}"
    
    total_records = len(result.get("events", [])) + len(result.get("states", []))
    assert total_records > 0, f"No records parsed for {test_case.filename} via Pyodide bridge"


# def test_pyodide_environment_sanity():
#     """Verify the test_environment helper returns expected structure."""
#     result = test_environment()
#     assert result["py_function"] == "test_environment"
#     assert "health" in result
#     # we don't strictly assert health values because local env != Pyodide environment
