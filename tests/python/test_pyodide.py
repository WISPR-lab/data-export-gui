import pytest
import os
import yaml
from pyparser.pyodide import parse

@pytest.mark.format("json")
def test_pyodide_json_sanity(test_case):
    """Verify JSON parsing returns expected structure with records."""
    from conftest import loader, repo_root
    
    # Load schema
    platform_info = loader.config["platforms"][test_case.platform]
    schema_path = os.path.join(repo_root, platform_info["schema_path"])
    with open(schema_path, "r") as f:
        schema_str = f.read()

    # Load test data
    content = test_case.read_content()
    
    # Parse via pyodide bridge
    result = parse(schema_str, content, test_case.filename)
    
    # Verify result structure
    assert "success" in result, "Result should have 'success' key"
    assert "events" in result, "Result should have 'events' key"
    assert "states" in result, "Result should have 'states' key"
    assert "errors" in result, "Result should have 'errors' key"
    
    # Verify parse succeeded
    success = result.get("success")
    assert success is True, f"Parse should succeed. Success={success}, Errors={result.get('errors')}"
    
    # Verify records were extracted
    events = result.get("events", [])
    states = result.get("states", [])
    total_records = len(events) + len(states)
    assert total_records > 0, f"Should extract records from {test_case.filename}"



@pytest.mark.format("csv")
def test_pyodide_csv_sanity(test_case):
    """Verify CSV parsing returns expected structure with records."""
    from conftest import loader, repo_root
    
    # Load schema
    platform_info = loader.config["platforms"][test_case.platform]
    schema_path = os.path.join(repo_root, platform_info["schema_path"])
    with open(schema_path, "r") as f:
        schema_str = f.read()

    # Load test data
    content = test_case.read_content()

    # Parse via pyodide bridge
    result = parse(schema_str, content, test_case.filename)
    
    # Verify result structure
    assert "success" in result, "Result should have 'success' key"
    assert "events" in result, "Result should have 'events' key"
    assert "states" in result, "Result should have 'states' key"
    assert "errors" in result, "Result should have 'errors' key"
    
    # Verify parse succeeded
    success = result.get("success")
    assert success is True, f"Parse should succeed. Success={success}, Errors={result.get('errors')}"
    
    # Verify records were extracted
    events = result.get("events", [])
    states = result.get("states", [])
    total_records = len(events) + len(states)
    assert total_records > 0, f"Should extract records from {test_case.filename}"


# def test_pyodide_environment_sanity():
#     """Verify the test_environment helper returns expected structure."""
#     result = test_environment()
#     assert result["py_function"] == "test_environment"
#     assert "health" in result
#     # we don't strictly assert health values because local env != Pyodide environment
