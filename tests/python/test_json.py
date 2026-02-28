import pytest
from extractors.json_ import JSONParser
from extractors.jsonl_ import JSONLParser
from extractors.json_label_values import JSONLabelValuesParser
from errors import FileLevelError
from conftest import validate_results


@pytest.mark.format("json")
def test_json_parse(test_case):
    content = test_case.read_content()
    records = JSONParser.extract(content, test_case.parser_cfg)
    validate_results(test_case, records)


@pytest.mark.format("jsonl")
def test_jsonl_parse(test_case):
    content = test_case.read_content()
    records = JSONLParser.extract(content, test_case.parser_cfg)
    validate_results(test_case, records)


@pytest.mark.format("json_label_values")
def test_json_label_values_parse(test_case):
    content = test_case.read_content()
    records = JSONLabelValuesParser.extract(content, test_case.parser_cfg)
    validate_results(test_case, records)


def test_json_raises_file_level_error_on_bad_input():
    with pytest.raises(FileLevelError):
        JSONParser.extract("{{{not valid json at all", {})


def test_jsonl_raises_file_level_error_on_bad_input():
    with pytest.raises(FileLevelError):
        JSONLParser.extract("{{{not valid json at all", {})
