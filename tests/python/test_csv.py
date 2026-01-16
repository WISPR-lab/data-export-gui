import pytest
import json
from pyparser.csv_ import CSVParser
from conftest import validate_results

@pytest.mark.format("csv")
def test_csv_parse(test_case):
    content = test_case.read_content()
    result = CSVParser.parse(content, test_case.filename, test_case.schema)
    events = result.events
    states = result.states
    errors = result.errors

    if events:
        print("\n\n ==== Printing first event === \n" + json.dumps(events[0], indent=2))
    if states:
        print("\n\n ==== Printing first state ===\n" + json.dumps(states[0], indent=2))
    validate_results(test_case, events, states, errors)


    