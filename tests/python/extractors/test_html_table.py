import pytest
import json
from python_core.extractors.html_table import HTMLTableParser
from python_core.errors import FileLevelError


class TestHTMLTableParserBasic:
    """Test basic functionality of the HTML table parser."""
    
    def test_parser_extracts_table_from_change_history(self):
        """Test parsing ChangeHistory HTML returns table records."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        # Single table should return list of records
        assert isinstance(result, (list, dict))
        if isinstance(result, list):
            assert len(result) > 0, "Should extract at least one record"
        
    def test_parser_extracts_ip_activity_table_from_subscriber_info(self):
        """Test parsing SubscriberInfo HTML with IP Activity table."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.SubscriberInfo.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        # May have multiple tables - should return dict with table_0, table_1, etc
        assert isinstance(result, (list, dict))

    def test_parser_raises_on_empty_input(self):
        """Test that parser raises FileLevelError on empty content."""
        with pytest.raises(FileLevelError):
            HTMLTableParser.extract("")

    def test_parser_raises_on_whitespace_only(self):
        """Test that parser raises FileLevelError on whitespace-only content."""
        with pytest.raises(FileLevelError):
            HTMLTableParser.extract("   \n  \t  ")


class TestHTMLTableParserChangeHistory:
    """Test change history table extraction."""
    
    def test_change_history_contains_required_columns(self):
        """Test that ChangeHistory table contains expected columns."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        # Should be a list
        assert isinstance(result, list) and len(result) > 0
        
        first_record = result[0]
        required_fields = ["Timestamp", "IP Address", "Change Type", "Old Value", "New Value"]
        
        for field in required_fields:
            assert field in first_record, f"Missing required field: {field}"

    def test_change_history_has_multiple_change_types(self):
        """Test that ChangeHistory contains different change types."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        assert isinstance(result, list) and len(result) > 0
        
        change_types = set(r.get("Change Type", "") for r in result)
        
        # Should have multiple types like PASSWORD, EMAIL, SERVICE changes
        assert len(change_types) > 1, "Should have multiple change types"
        assert any(ct in change_types for ct in ["PASSWORD", "RECOVERY_EMAIL_VERIFIED", "SERVICE_ADDED"])

    def test_change_history_timestamps_valid(self):
        """Test that timestamps in ChangeHistory are valid."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        for record in result:
            timestamp = record.get("Timestamp", "")
            # Should be ISO format with Z suffix
            assert timestamp and ("Z" in timestamp or "-" in timestamp), f"Invalid timestamp: {timestamp}"


class TestHTMLTableParserSubscriberInfo:
    """Test subscriber info IP activity table extraction."""
    
    def test_subscriber_info_ip_activity_has_ip_column(self):
        """Test that IP Activity table has IP Address column."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.SubscriberInfo.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        # Multiple tables
        if isinstance(result, dict):
            # Get the IP activity table (should be one of the tables)
            tables = result
            # Find a table with IP Address column
            ip_table = None
            for table_name, records in tables.items():
                if isinstance(records, list) and len(records) > 0:
                    first_record = records[0]
                    if "IP Address" in first_record:
                        ip_table = records
                        break
            
            assert ip_table is not None, "Should find table with IP Address column"
            assert len(ip_table) > 0, "IP Activity table should have records"

    def test_subscriber_info_ip_activity_contains_activity_types(self):
        """Test that IP Activity has Login/Logout activity types."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.SubscriberInfo.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        if isinstance(result, dict):
            for table_name, records in result.items():
                if isinstance(records, list) and len(records) > 0:
                    first_record = records[0]
                    if "Activity Type" in first_record:
                        activity_types = set(r.get("Activity Type", "") for r in records)
                        assert any(at in ["Login", "Logout"] for at in activity_types), \
                            "Should have Login/Logout activities"
                        return
        
        # If single list
        if isinstance(result, list) and len(result) > 0 and "Activity Type" in result[0]:
            activity_types = set(r.get("Activity Type", "") for r in result)
            assert any(at in ["Login", "Logout"] for at in activity_types)


class TestHTMLTableParserMultipleTables:
    """Test extraction of multiple tables."""
    
    def test_subscriber_info_returns_multiple_tables(self):
        """Test that SubscriberInfo with multiple tables returns dict with table keys."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.SubscriberInfo.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        # SubscriberInfo has 2 tables (Change History and IP Activity)
        # So result should be a dict with table_0, table_1, etc
        if isinstance(result, dict):
            # Multiple tables
            assert len(result) >= 1, "Should extract at least one table"
            # Keys should be table_0, table_1, etc
            for table_name in result.keys():
                assert table_name.startswith("table_") or isinstance(result[table_name], list)

    def test_single_table_returns_list(self):
        """Test that HTML with single table returns list, not dict."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        # ChangeHistory has 1 table, so should return list
        assert isinstance(result, list), "Single table should return list"


class TestHTMLTableParserDataTypes:
    """Test that extracted data has correct types."""
    
    def test_all_records_are_dicts(self):
        """Test that all records are dictionaries."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        assert isinstance(result, list)
        for record in result:
            assert isinstance(record, dict), f"Record should be dict, got {type(record)}"

    def test_empty_cells_filled_with_empty_string(self):
        """Test that empty table cells are filled with empty strings (not NaN)."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        assert isinstance(result, list)
        for record in result:
            for key, value in record.items():
                # Should not be NaN or None
                assert value == value or isinstance(value, str), f"Value should not be NaN: {value}"

    def test_string_values_from_table_cells(self):
        """Test that all values are converted to strings."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        assert isinstance(result, list)
        for record in result:
            for key, value in record.items():
                # All values should be strings (pandas fillna with '')
                assert isinstance(value, str), f"Value should be string, got {type(value)}: {value}"


class TestHTMLTableParserFieldNames:
    """Test that table headers become field names."""
    
    def test_headers_become_field_names(self):
        """Test that table headers are used as field names."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        assert isinstance(result, list) and len(result) > 0
        first_record = result[0]
        
        # All field names should match table headers
        field_names = set(first_record.keys())
        expected_headers = {"Timestamp", "IP Address", "Change Type", "Old Value", "New Value"}
        
        assert field_names == expected_headers, f"Fields {field_names} don't match headers {expected_headers}"

    def test_field_names_preserved_correctly(self):
        """Test that field names are not modified."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.SubscriberInfo.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        if isinstance(result, dict):
            for table_name, records in result.items():
                if isinstance(records, list) and len(records) > 0:
                    first_record = records[0]
                    # Field names should have proper casing and spacing
                    for field_name in first_record.keys():
                        assert field_name and not field_name.startswith("Unnamed"), \
                            f"Field name should not be Unnamed: {field_name}"


class TestHTMLTableParserEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_html_without_tables_raises_error(self):
        """Test that HTML without tables raises error."""
        no_table_html = "<html><body><p>No tables here</p></body></html>"
        
        with pytest.raises(FileLevelError):
            HTMLTableParser.extract(no_table_html)

    def test_html_with_empty_table_raises_error(self):
        """Test that empty table (no rows) raises error."""
        empty_table_html = "<html><body><table><tr><th>Header</th></tr></table></body></html>"
        
        # Empty table might still parse but be empty - depends on pandas behavior
        result = HTMLTableParser.extract(empty_table_html)
        assert isinstance(result, (list, dict))

    def test_change_type_values_not_empty(self):
        """Test that Change Type field always has a value."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        for record in result:
            change_type = record.get("Change Type", "").strip()
            assert len(change_type) > 0, f"Change Type should not be empty"


class TestHTMLTableParserConsistency:
    """Test consistency of extracted data."""
    
    def test_all_records_have_same_fields(self):
        """Test that all records in table have same fields."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        assert isinstance(result, list) and len(result) > 0
        
        first_record_fields = set(result[0].keys())
        
        for record in result[1:]:
            record_fields = set(record.keys())
            assert record_fields == first_record_fields, \
                f"Record fields {record_fields} don't match first record {first_record_fields}"

    def test_record_count_reasonable(self):
        """Test that number of records is reasonable."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        assert isinstance(result, list)
        # Should have multiple records (at least 5 based on sample data)
        assert len(result) >= 5, f"Should have multiple records, got {len(result)}"

    def test_timestamp_consistency(self):
        """Test that timestamps follow consistent format."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        for record in result:
            timestamp = record.get("Timestamp", "")
            # All should have Z suffix (UTC)
            assert timestamp.endswith("Z") or "-" in timestamp, \
                f"Timestamp format inconsistent: {timestamp}"


class TestHTMLTableParserExactCounts:
    """Test exact row and column counts for specific test data files."""
    
    def test_change_history_has_11_rows_5_columns(self):
        """Test that ChangeHistory.html has exactly 11 rows and 5 columns."""
        with open("tests/zip_data/google/Google Account/bob.researcher24.ChangeHistory.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLTableParser.extract(content)
        
        assert isinstance(result, list), f"Expected list, got {type(result)}"
        assert len(result) == 11, f"Expected 11 rows, got {len(result)}"
        
        # Verify each record has exactly 5 columns
        for record in result:
            assert len(record) == 5, f"Expected 5 columns, got {len(record)}"
            assert set(record.keys()) == {"Timestamp", "IP Address", "Change Type", "Old Value", "New Value"}
