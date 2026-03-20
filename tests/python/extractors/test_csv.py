import pytest
import json
from python_core.extractors.csv_ import CSVParser
from python_core.errors import FileLevelError
from conftest import validate_results


@pytest.mark.format("csv")
def test_csv_parse(test_case):
    content = test_case.read_content()
    records = CSVParser.extract(content, test_case.parser_cfg)

    if records:
        print("\n\n ==== Printing first record === \n" + json.dumps(records[0], indent=2))

    validate_results(test_case, records)


def test_csv_raises_file_level_error_on_empty_input():

    with pytest.raises(FileLevelError):
        CSVParser.extract("", {})


def test_access_log_devices_csv_has_2_rows():
    """Test that Access Log Devices CSV has exactly 2 device records."""
    with open("tests/zip_data/google/Access Log Activity/Devices - A list of devices (i.e. Nest, Pixel, iPh.csv", "r", encoding='utf-8') as f:
        content = f.read()
    
    records = CSVParser.extract(content, {})
    
    assert isinstance(records, list), f"Expected list, got {type(records)}"
    assert len(records) == 2, f"Expected 2 device records, got {len(records)}"
    
    # Verify expected fields exist
    expected_fields = {"Device Type", "Brand Name", "Marketing Name", "OS", "OS Version", "Device Model", "User Given Name", "Device Last Location", "Gaia ID"}
    for record in records:
        assert set(record.keys()) == expected_fields, f"Fields don't match expected: {set(record.keys())}"
