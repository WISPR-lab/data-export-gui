import pytest
from pyparser.json_ import JSONParser
from pyparser.jsonl_ import JSONLParser
from pyparser.json_label_values import JSONLabelValuesParser
from conftest import validate_results

@pytest.mark.format("json")
def test_json_parse(test_case):
    content = test_case.read_content()
    events, states, errors = JSONParser.parse(content, test_case.filename, test_case.schema)
    validate_results(test_case, events, states, errors)


@pytest.mark.format("jsonl")
def test_jsonl_parse(test_case):
    content = test_case.read_content()
    events, states, errors = JSONLParser.parse(content, test_case.filename, test_case.schema)
    validate_results(test_case, events, states, errors)


@pytest.mark.format("json_label_values")
def test_json_label_values_parse(test_case):
    content = test_case.read_content()
    events, states, errors = JSONLabelValuesParser.parse(content, test_case.filename, test_case.schema)
    validate_results(test_case, events, states, errors)
