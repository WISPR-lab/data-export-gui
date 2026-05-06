import pytest
from python_core.extractors.jsonl_ import JSONLParser
from python_core.extractors.json_ import JSONParser
from python_core.extractors.csv_ import CSVParser
from python_core.extractors.csv_multi import CSVMultiParser
from python_core.extractors.html_table import HTMLTableParser
from python_core.extractors.html_ggl_myactivity import HTMLMyActvityParser
from python_core.extractors.json_label_values import JSONLabelValuesParser


class TestJSONLLineNumbers:
    def test_single_line(self):
        content = '{"key": "value"}'
        records = JSONLParser.extract(content)
        assert len(records) == 1
        assert records[0]["__line_numbers"] == [1, 1]

    def test_multiple_lines(self):
        content = '{"a": 1}\n{"b": 2}\n{"c": 3}'
        records = JSONLParser.extract(content)
        assert len(records) == 3
        assert records[0]["__line_numbers"] == [1, 1]
        assert records[1]["__line_numbers"] == [2, 2]
        assert records[2]["__line_numbers"] == [3, 3]

    def test_with_empty_lines(self):
        content = '{"a": 1}\n\n{"b": 2}'
        records = JSONLParser.extract(content)
        assert len(records) == 2
        assert records[0]["__line_numbers"] == [1, 1]
        assert records[1]["__line_numbers"] == [3, 3]


class TestJSONLineNumbers:
    def test_single_line_json(self):
        content = '{"key": "value"}'
        records = JSONParser.extract(content)
        assert len(records) == 1
        assert records[0]["__line_numbers"] == [1, 1]

    def test_multiline_json(self):
        content = '{\n  "key": "value",\n  "nested": {\n    "inner": 1\n  }\n}'
        records = JSONParser.extract(content)
        assert len(records) == 1
        assert records[0]["__line_numbers"] == [1, 6]

    def test_json_array(self):
        content = '[\n  {"a": 1},\n  {"b": 2}\n]'
        records = JSONParser.extract(content)
        assert len(records) == 2
        # All records in the array share the full file range
        assert records[0]["__line_numbers"] == [1, 4]
        assert records[1]["__line_numbers"] == [1, 4]


class TestCSVLineNumbers:
    def test_single_row_csv(self):
        content = 'Name,Age\nAlice,30'
        records = CSVParser.extract(content)
        assert len(records) == 1
        assert records[0]["__line_numbers"] == [2, 2]

    def test_multiple_rows_csv(self):
        content = 'Name,Age\nAlice,30\nBob,25'
        records = CSVParser.extract(content)
        assert len(records) == 2
        assert records[0]["__line_numbers"] == [2, 2]
        assert records[1]["__line_numbers"] == [3, 3]

    def test_multiline_csv_value(self):
        # CSV with quoted value containing newline
        content = 'Name,Age,Notes\nAlice,30,"Line 1\nLine 2"\nBob,25,""'
        records = CSVParser.extract(content)
        assert len(records) == 2
        # Alice's record spans lines 2-3 (quoted multiline value)
        assert records[0]["__line_numbers"] == [2, 3]
        # Bob's record is line 4
        assert records[1]["__line_numbers"] == [4, 4]

    def test_google_device_csv(self):
        # Simulates the weird Google CSV with multiline device location
        content = '''Device Type,Brand Name,OS
MOBILE,Apple,iOS
MOBILE,Google,"Country: US
Last Activity: 2025-02-19"
MOBILE,Apple,iOS'''
        records = CSVParser.extract(content)
        assert len(records) == 3
        assert records[0]["__line_numbers"] == [2, 2]
        assert records[1]["__line_numbers"] == [3, 4]  # spans multiline value
        assert records[2]["__line_numbers"] == [5, 5]


class TestCSVMultiLineNumbers:
    def test_concatenated_csv(self):
        content = '''Devices
Device Type,Brand
MOBILE,Apple
MOBILE,Google


Locations
City,Country
NYC,USA
LA,USA'''
        records = CSVMultiParser.extract(content)
        # Should have 4 records total (2 devices + 2 locations)
        assert len(records) == 4
        # Verify all records have line numbers
        for record in records:
            assert "__line_numbers" in record
            assert isinstance(record["__line_numbers"], list)


class TestHTMLTableLineNumbers:
    def test_single_line_html_table(self):
        # HTML all on one line
        content = '<table><tr><th>Name</th><th>Age</th></tr><tr><td>Alice</td><td>30</td></tr></table>'
        records = HTMLTableParser.extract(content)
        assert len(records) == 1
        assert records[0]["__line_numbers"] == [1, 1]

    def test_multiline_html_table(self):
        content = '''<table>
  <tr><th>Name</th><th>Age</th></tr>
  <tr><td>Alice</td><td>30</td></tr>
  <tr><td>Bob</td><td>25</td></tr>
</table>'''
        records = HTMLTableParser.extract(content)
        assert len(records) == 2
        # All rows share the full HTML file range
        assert records[0]["__line_numbers"] == [1, 5]
        assert records[1]["__line_numbers"] == [1, 5]

    def test_multiple_tables_html(self):
        content = '''<table>
  <tr><th>Name</th></tr>
  <tr><td>Alice</td></tr>
</table>
<table>
  <tr><th>City</th></tr>
  <tr><td>NYC</td></tr>
</table>'''
        records = HTMLTableParser.extract(content)
        assert len(records) == 2
        assert records[0]["__line_numbers"] == [1, 8]
        assert records[1]["__line_numbers"] == [1, 8]


class TestHTMLMyActivityLineNumbers:
    def test_single_line_myactivity(self):
        # All on one line
        content = '<div class="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp"><div class="header-cell mdl-cell mdl-cell--12-col">Maps</div><div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1"><a href="http://example.com">Visited Place</a></div><div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">2025-02-19</div></div>'
        records = HTMLMyActvityParser.extract(content)
        assert len(records) >= 1
        assert records[0]["__line_numbers"] == [1, 1]

    def test_multiline_myactivity(self):
        content = '''<div class="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp">
  <div class="header-cell mdl-cell mdl-cell--12-col">Maps</div>
  <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
    <a href="http://example.com">Visited Place</a>
  </div>
  <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">2025-02-19</div>
</div>'''
        records = HTMLMyActvityParser.extract(content)
        assert len(records) >= 1
        assert records[0]["__line_numbers"] == [1, 7]


class TestJSONLabelValuesLineNumbers:
    def test_single_line_lv(self):
        content = '{"label_values": [{"label": "Key", "value": "Val"}]}'
        records = JSONLabelValuesParser.extract(content)
        assert len(records) == 1
        assert records[0]["__line_numbers"] == [1, 1]

    def test_multiline_lv(self):
        content = '''{"label_values": [
  {"label": "Key1", "value": "Val1"},
  {"label": "Key2", "value": "Val2"}
]}'''
        records = JSONLabelValuesParser.extract(content)
        # JSONLabelValuesParser flattens all label_values into one record
        assert len(records) == 1
        assert records[0]["Key1"] == "Val1"
        assert records[0]["Key2"] == "Val2"
        assert records[0]["__line_numbers"] == [1, 4]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
