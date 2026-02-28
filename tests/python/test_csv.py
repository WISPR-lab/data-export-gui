import pytest
import json
from extractors.csv_ import CSVParser
from conftest import validate_results


@pytest.mark.format("csv")
def test_csv_parse(test_case):
    content = test_case.read_content()
    records = CSVParser.extract(content, test_case.parser_cfg)

    if records:
        print("\n\n ==== Printing first record === \n" + json.dumps(records[0], indent=2))

    validate_results(test_case, records)


def test_csv_raises_file_level_error_on_empty_input():
    from errors import FileLevelError
    with pytest.raises(FileLevelError):
        CSVParser.extract("", {})
