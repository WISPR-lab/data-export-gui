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
