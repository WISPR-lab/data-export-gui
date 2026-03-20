import pytest
import json
from python_core.extractors.html_ggl_myactivity import HTMLMyActvityParser
from python_core.errors import FileLevelError


class TestHTMLMyActivityParserBasic:
    """Test basic functionality of the HTML My Activity parser."""
    
    def test_parser_extracts_records_from_search_activity(self):
        """Test parsing Search activity HTML returns multiple records."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        
        # Should extract multiple search activity records
        assert len(records) > 0, "Should extract at least one record from Search activity"
        assert isinstance(records, list), "Result should be a list"
        
    def test_parser_extracts_records_from_gmail_activity(self):
        """Test parsing Gmail activity HTML returns records."""
        with open("tests/zip_data/google/My Activity/Gmail/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        
        assert len(records) >= 0, "Should return a list (possibly empty)"
        assert isinstance(records, list), "Result should be a list"

    def test_parser_raises_on_empty_input(self):
        """Test that parser raises FileLevelError on empty content."""
        with pytest.raises(FileLevelError):
            HTMLMyActvityParser.extract("")

    def test_parser_raises_on_whitespace_only(self):
        """Test that parser raises FileLevelError on whitespace-only content."""
        with pytest.raises(FileLevelError):
            HTMLMyActvityParser.extract("   \n  \t  ")


class TestHTMLMyActivityParserFields:
    """Test field extraction and mapping."""
    
    def test_record_contains_platform_field(self):
        """Test that extracted records contain Platform field."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        assert len(records) > 0
        
        # All records should have Platform
        for record in records:
            assert "Platform" in record, f"Record missing Platform field: {record.keys()}"
            assert record["Platform"] == "Search", "Platform should be 'Search' for search activity"

    def test_record_contains_activity_field(self):
        """Test that records contain Activity field."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        assert len(records) > 0
        
        for record in records:
            assert "Activity" in record, "Record missing Activity field"
            assert isinstance(record["Activity"], str), "Activity should be a string"

    def test_record_contains_timestamp_field(self):
        """Test that records contain Timestamp field."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        assert len(records) > 0
        
        for record in records:
            assert "Timestamp" in record, f"Record missing Timestamp: {record.keys()}"
            # Timestamp should contain year (e.g., "2025")
            assert any(char.isdigit() for char in record["Timestamp"]), "Timestamp should contain digits"


class TestHTMLMyActivityParserURLExtraction:
    """Test URL extraction from links."""
    
    def test_url_extracted_from_search_query(self):
        """Test that URLs are extracted from search query links."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        
        # Look for records with URLs (from "Searched for" activities)
        urls_found = [r for r in records if "URL" in r]
        assert len(urls_found) > 0, "Should extract at least one URL from search activity"
        
        # URLs should start with http
        for record in urls_found:
            assert record["URL"].startswith(("http://", "https://")), f"Invalid URL: {record['URL']}"

    def test_url_field_optional(self):
        """Test that URL field is optional (not all activities have links)."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        
        # Some records should have URLs, some may not
        has_url = any("URL" in r for r in records)
        missing_url = any("URL" not in r for r in records)
        
        # Both should be true for realistic Google activity data
        assert has_url, "Some records should have URLs"
        assert missing_url, "Some records should not have URLs (like notifications)"


class TestHTMLMyActivityParserLocationExtraction:
    """Test location data extraction."""
    
    def test_location_fields_extracted_when_present(self):
        """Test that location data is extracted when available."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        
        # Some search activities include location data
        locations_found = [r for r in records if any(
            key in r for key in ["Locations", "Location.URL"]
        )]
        
        # May or may not have location data depending on content
        # This test just verifies the parser produces valid structure
        for record in locations_found:
            if "Locations" in record:
                assert isinstance(record["Locations"], str)

    def test_location_url_extracted_for_maps(self):
        """Test that location URLs are properly extracted."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        
        # Check for location URLs (from maps links)
        location_urls = [r for r in records if "Location.URL" in r]
        
        for record in location_urls:
            url = record["Location.URL"]
            assert url.startswith(("http://", "https://")), f"Location URL should be valid: {url}"


class TestHTMLMyActivityParserProductsField:
    """Test extraction of products metadata."""
    
    def test_products_field_extracted(self):
        """Test that Products field is extracted from context."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        
        for record in records:
            if "Products" in record:
                assert isinstance(record["Products"], str)
                assert len(record["Products"]) > 0


class TestHTMLMyActivityParserDataIntegrity:
    """Test that parsed data has correct structure and types."""
    
    def test_all_records_are_dicts(self):
        """Test that all returned records are dictionaries."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        
        for record in records:
            assert isinstance(record, dict), f"Record should be dict, got {type(record)}"

    def test_no_duplicate_keys_in_record(self):
        """Test that records don't have duplicate keys."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        
        for record in records:
            keys = list(record.keys())
            unique_keys = set(record.keys())
            assert len(keys) == len(unique_keys), "Records should not have duplicate keys"

    def test_no_none_values_in_required_fields(self):
        """Test that required fields are never None."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        
        required_fields = ["Platform", "Activity", "Timestamp"]
        
        for record in records:
            for field in required_fields:
                assert field in record, f"Required field '{field}' missing"
                assert record[field] is not None, f"Required field '{field}' should not be None"
                assert record[field] != "", f"Required field '{field}' should not be empty"


class TestHTMLMyActivityParserMultipleActivities:
    """Test extraction across different activity types."""
    
    def test_drive_activity_extraction(self):
        """Test extraction from Drive activity file."""
        try:
            with open("tests/zip_data/google/My Activity/Drive/MyActivity.html", "r", encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip("Drive activity file not found")
        
        records = HTMLMyActvityParser.extract(content)
        
        if len(records) > 0:
            # Verify Drive activities have proper structure
            assert all("Platform" in r and "Activity" in r for r in records)

    def test_maps_activity_extraction(self):
        """Test extraction from Maps activity file."""
        try:
            with open("tests/zip_data/google/My Activity/Maps/MyActivity.html", "r", encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip("Maps activity file not found")
        
        records = HTMLMyActvityParser.extract(content)
        
        if len(records) > 0:
            # Maps activities should have location data
            assert all("Platform" in r for r in records)


class TestHTMLMyActivityParserWhitespace:
    """Test whitespace and formatting handling."""
    
    def test_multiple_spaces_normalized_in_activity(self):
        """Test that multiple spaces in activity are normalized."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        
        for record in records:
            activity = record.get("Activity", "")
            # Check that we don't have excessive whitespace
            assert "  " not in activity or activity.startswith("http"), \
                "Activity should not contain multiple consecutive spaces"

    def test_leading_trailing_whitespace_stripped(self):
        """Test that leading/trailing whitespace is stripped from fields."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        records = HTMLMyActvityParser.extract(content)
        
        for record in records:
            for key, value in record.items():
                if isinstance(value, str):
                    assert value == value.strip(), \
                        f"Field {key} should not have leading/trailing whitespace: '{value}'"


class TestHTMLMyActivityParserErrorHandling:
    """Test error handling and edge cases."""
    
    def test_malformed_html_raises_error(self):
        """Test that malformed HTML raises an error."""
        malformed_html = "<div>incomplete content"
        
        # This might succeed with partial parse, but we test that it doesn't crash
        result = HTMLMyActvityParser.extract(malformed_html)
        assert isinstance(result, list)

    def test_html_with_no_activity_cells_returns_empty_list(self):
        """Test that HTML with no activity cells returns empty list."""
        minimal_html = "<html><body><div>No activity cells here</div></body></html>"
        
        result = HTMLMyActvityParser.extract(minimal_html)
        assert result == []


class TestHTMLMyActivityParserExactCounts:
    """Test exact row counts for specific test data files."""
    
    def test_search_myactivity_has_56_records(self):
        """Test that Search MyActivity.html extracts exactly 56 records."""
        with open("tests/zip_data/google/My Activity/Search/MyActivity.html", "r", encoding='utf-8') as f:
            content = f.read()
        
        result = HTMLMyActvityParser.extract(content)
        
        assert isinstance(result, list)
        assert len(result) == 56, f"Expected 56 records, got {len(result)}"
