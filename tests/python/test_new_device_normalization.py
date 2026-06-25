import pytest
import re
from python_core.field_normalization import device


class TestGetVal:
    """Test the _get_val function with various preference modes."""

    def test_get_val_first_preference_returns_first_non_empty(self):
        """With preference='first', should return first non-empty value."""
        attrs = {"model": "iPhone X", "user_agent_model": "ignored"}
        result = device._get_val(attrs, "model", preference="first")
        assert result == "iPhone X"

    def test_get_val_first_preference_falls_back_to_user_agent(self):
        """With preference='first', should fall back to user_agent_ variant."""
        attrs = {"user_agent_model": "iPhone 12"}
        result = device._get_val(attrs, "model", preference="first")
        assert result == "iPhone 12"

    @pytest.mark.parametrize(
        "attrs,expected",
        [
            ({}, None),
            ({"model": ""}, None),
            ({"model": "  "}, None),
            ({"model": None}, None),
        ],
    )
    def test_get_val_missing_and_empty_values(self, attrs, expected):
        """Should return None for missing, empty, or whitespace-only values."""
        result = device._get_val(attrs, "model", preference="first")
        assert result is expected

    def test_get_val_longest_preference_returns_longer_value(self):
        """With preference='longest', should return the longer string."""
        attrs = {"model": "iPhone", "user_agent_model": "iPhone 12 Pro Max"}
        result = device._get_val(attrs, "model", preference="longest")
        assert result == "iPhone 12 Pro Max"

    def test_get_val_longest_preference_both_values(self):
        """With preference='longest', should compare both key and user_agent_ key."""
        attrs = {"model": "short", "user_agent_model": "longer value here"}
        result = device._get_val(attrs, "model", preference="longest")
        assert result == "longer value here"

    def test_get_val_non_generic_prefers_non_generic(self):
        """With preference='non_generic', should prefer non-generic names."""
        attrs = {"model": "phone", "user_agent_model": "iPhone 11"}
        result = device._get_val(attrs, "model", preference="non_generic")
        assert result == "iPhone 11"

    def test_get_val_non_generic_with_versions(self):
        """Non-generic preference should prefer values with version/variant info."""
        attrs = {"model": "iPad", "user_agent_model": "iPad Pro 12.9"}
        result = device._get_val(attrs, "model", preference="non_generic")
        assert result == "iPad Pro 12.9"


class TestNormalizeDeviceFields:
    """Test the normalize_device_fields function against the real lookups."""

    def test_normalize_device_fields_apple_model_resolution(self):
        """Should resolve Apple model identifiers to model names."""
        attrs = {"device_model_identifier": "iPhone10,6"}
        result = device.normalize_device_fields(attrs)
        assert result["device_model_name"] == "iPhone X"
        assert result["norm__model_identifier"] == "iphone10,6"

    def test_normalize_device_fields_manufacturer_inference(self):
        """Should infer manufacturer from model name."""
        attrs = {"device_model_name": "iPhone 12"}
        result = device.normalize_device_fields(attrs)
        assert result["norm__manufacturer"] == "apple"

    def test_normalize_device_fields_manufacturer_alias_resolution(self):
        """Should resolve manufacturer aliases."""
        attrs = {"device_manufacturer": "samsng"}
        result = device.normalize_device_fields(attrs)
        assert result["norm__manufacturer"] == "samsung"

    def test_normalize_device_fields_explicit_manufacturer_preferred(self):
        """Explicit manufacturer should be preferred over inference."""
        attrs = {"device_model_name": "Galaxy S20", "device_manufacturer": "Samsung"}
        result = device.normalize_device_fields(attrs)
        assert result["norm__manufacturer"] == "samsung"

    def test_normalize_device_fields_os_name_inference_from_version(self):
        """Should infer OS name from version string."""
        attrs = {"os_version": "iOS 15.7"}
        result = device.normalize_device_fields(attrs)
        assert result["norm__os_name"] == "ios"
        assert result["norm__os_version"] == "15.7"

    def test_normalize_device_fields_os_type_mapping(self):
        """Should map OS name to OS type."""
        attrs = {"os_name": "iOS"}
        result = device.normalize_device_fields(attrs)
        assert result["norm__os_type"] == "ios"

    def test_normalize_device_fields_all_lowercase(self):
        """All normalized fields should be lowercase."""
        attrs = {
            "device_model_name": "iPhone X",
            "device_manufacturer": "Apple",
            "os_name": "iOS",
            "os_version": "15.7",
        }
        result = device.normalize_device_fields(attrs)
        assert result["norm__model_name"] == "iphone x"
        assert result["norm__manufacturer"] == "apple"
        assert result["norm__os_name"] == "ios"

    def test_normalize_device_fields_with_composite_client(self):
        """Should normalize composite client names."""
        attrs = {
            "user_agent_client_name": "Chrome",
            "user_agent_secondary_client_name": "WebView",
        }
        result = device.normalize_device_fields(attrs)
        assert result["norm__client_name"] == "chrome :: webview"

    def test_normalize_device_fields_missing_fields(self):
        """Should handle missing fields gracefully."""
        attrs = {}
        result = device.normalize_device_fields(attrs)
        norm_keys = [k for k in result.keys() if k.startswith("norm__")]
        assert len(norm_keys) == 0

    def test_normalize_device_fields_empty_string_ignored(self):
        """Empty string values should not create normalized fields."""
        attrs = {"device_model_name": "", "device_manufacturer": "  "}
        result = device.normalize_device_fields(attrs)
        norm_keys = [k for k in result.keys() if k.startswith("norm__")]
        assert len(norm_keys) == 0

    def test_normalize_device_fields_cascading_fallback(self):
        """OS name should cascade: explicit > inferred from version > OS type."""
        attrs = {"os_version": "Android 12", "os_type": "MobileOS"}
        result = device.normalize_device_fields(attrs)
        assert result["norm__os_name"] == "android"

    def test_normalize_device_fields_preserves_original_attrs(self):
        """Should preserve original attributes while adding norm__ fields."""
        attrs = {"device_model_name": "Pixel 6"}
        result = device.normalize_device_fields(attrs)
        assert result["device_model_name"] == "Pixel 6"
        assert result["norm__model_name"] == "pixel 6"

    @pytest.mark.parametrize(
        "input_attrs,expected_norm_keys",
        [
            (
                {
                    "device_model_identifier": "iPhone10,6",
                    "device_model_name": "iPhone X",
                },
                {"norm__model_identifier", "norm__model_name", "norm__manufacturer"},
            ),
            (
                {"device_manufacturer": "Apple", "os_name": "iOS"},
                {"norm__manufacturer", "norm__os_name", "norm__os_type"},
            ),
            (
                {"os_version": "12.0", "user_agent_client_name": "Safari"},
                {"norm__os_version", "norm__client_name"},
            ),
        ],
    )
    def test_normalize_device_fields_parametrized(
        self, input_attrs, expected_norm_keys
    ):
        """Parametrized test for various attribute combinations."""
        result = device.normalize_device_fields(input_attrs)
        actual_norm_keys = {k for k in result.keys() if k.startswith("norm__")}
        assert actual_norm_keys == expected_norm_keys, (
            f"Expected {expected_norm_keys} but got {actual_norm_keys}"
        )
