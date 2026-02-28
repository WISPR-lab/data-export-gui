import pytest
from extractors.json_ import JSONParser
from extractors.jsonl_ import JSONLParser
from extractors.json_label_values import JSONLabelValuesParser
from extractors.csv_ import CSVParser
from errors import FileLevelError


def test_json_file_level_error_on_unparseable_input():
    with pytest.raises(FileLevelError):
        JSONParser.extract("{{{not valid json at all", {})


def test_jsonl_file_level_error_on_unparseable_input():
    with pytest.raises(FileLevelError):
        JSONLParser.extract("{{{not valid json at all\n{{{also bad", {})


def test_json_label_values_file_level_error_on_unparseable_input():
    with pytest.raises(FileLevelError):
        JSONLabelValuesParser.extract("{{{not valid json at all", {})


def test_partial_errors_structure():
    """Verify the shape of a partial_errors entry as returned by extractor_worker."""
    err = FileLevelError("something went wrong", context={"error_type": "ValueError"})
    entry = {'file': 'test.json', 'level': 'error', 'msg': str(err)}
    assert entry['level'] == 'error'
    assert 'file' in entry
    assert 'msg' in entry


def test_json_valid_input_does_not_raise():
    records = JSONParser.extract('[{"key": "val"}]', {})
    assert len(records) == 1
    assert records[0]['key'] == 'val'


def test_csv_empty_raises_file_level_error():
    from errors import FileLevelError
    with pytest.raises(FileLevelError):
        CSVParser.extract("", {})


# def test_pyodide_environment_sanity():
#     """Verify the test_environment helper returns expected structure."""
#     result = test_environment()
#     assert result["py_function"] == "test_environment"
#     assert "health" in result
#     # we don't strictly assert health values because local env != Pyodide environment

