import pytest
from unittest.mock import patch, MagicMock
import re
from python_core.field_normalization import device


@pytest.fixture
def mock_device_lookup():
    """Mock the device_lookup module dependencies."""
    mock_lookup = {
        "APPLE_MODELS": {
            "iPhone10,6": "iPhone X",
            "iPhone12,1": "iPhone 11",
            "iPad7,1": "iPad Pro",
        },
        "COMPILED_MANUFACTURER_MODEL_MAP": {
            "Apple": [re.compile(r"iPhone|iPad|Mac"), re.compile(r"iphone|ipad|mac")],
            "Samsung": [re.compile(r"Galaxy|SM-"), re.compile(r"galaxy")],
            "Google": [re.compile(r"Pixel"), re.compile(r"pixel")],
        },
        "VARIANT_SUFFIXES": {
            "pro",
            "max",
            "plus",
            "ultra",
            "lite",
            "mini",
            "xl",
            "s",
            "se",
        },
        "GENERIC_MODEL_NAMES": {"phone", "smartphone", "tablet", "device", "unknown"},
        "ALL_MFRS_LOWER": {"apple", "samsung", "google", "microsoft"},
        "COMPILED_MANUFACTURER_ALIASES_MAP": {
            "Apple": re.compile(r"apple|cupertino|ios"),
            "Samsung": re.compile(r"samsung|samsng|galaxy"),
        },
        "OS_TYPE_MAP": {
            "ios": "Mobile OS",
            "android": "Mobile OS",
            "windows": "Desktop OS",
            "macos": "Desktop OS",
        },
    }
    with patch.dict("python_core.field_normalization.device.dl.__dict__", mock_lookup):
        yield


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

    def test_get_val_non_generic_prefers_non_generic(self, mock_device_lookup):
        """With preference='non_generic', should prefer non-generic names."""
        attrs = {"model": "phone", "user_agent_model": "iPhone 11"}
        result = device._get_val(attrs, "model", preference="non_generic")
        assert result == "iPhone 11"

    def test_get_val_non_generic_with_versions(self, mock_device_lookup):
        """Non-generic preference should prefer values with version/variant info."""
        attrs = {"model": "iPad", "user_agent_model": "iPad Pro 12.9"}
        result = device._get_val(attrs, "model", preference="non_generic")
        assert result == "iPad Pro 12.9"

    def test_get_val_non_generic_both_generic(self, mock_device_lookup):
        """If both are generic, should pick one (max by length as tiebreaker)."""
        attrs = {"model": "phone", "user_agent_model": "device"}
        result = device._get_val(attrs, "model", preference="non_generic")
        # Both are generic, so it should return the longer one
        assert result in ("phone", "device")

    def test_get_val_invalid_preference_raises(self):
        """Invalid preference value should raise ValueError."""
        attrs = {"model": "iPhone"}
        with pytest.raises(ValueError, match="Invalid preference"):
            device._get_val(attrs, "model", preference="invalid")

    def test_get_val_strips_whitespace(self):
        """Should strip leading/trailing whitespace from values."""
        attrs = {"model": "  iPhone X  "}
        result = device._get_val(attrs, "model", preference="first")
        assert result == "iPhone X"

    def test_get_val_converts_non_string_to_string(self):
        """Should convert non-string values to strings."""
        attrs = {"model": 123}
        result = device._get_val(attrs, "model", preference="first")
        assert result == "123"


class TestDecomposeOsVersion:
    """Test the _decompose_os_version function."""

    @pytest.mark.parametrize(
        "raw_version,expected_version,expected_name",
        [
            ("iOS 15.7", "15.7", "iOS"),
            ("iOS 15.7.1", "15.7.1", "iOS"),
            ("android 12", "12", "android"),
            ("Android 11.0.1", "11.0.1", "Android"),
            ("Windows_NT_10_0", "10.0", "Windows_NT"),
            ("10.15.7", "10.15.7", None),
            ("macOS 12.6.5", "12.6.5", "macOS"),
            ("Windows_10_0_19041", "10.0.19041", "Windows"),
        ],
    )
    def test_decompose_os_version_valid_versions(
        self, raw_version, expected_version, expected_name
    ):
        """Should correctly extract version number and OS name."""
        version, name = device._decompose_os_version(raw_version)
        assert version == expected_version
        assert name == expected_name

    @pytest.mark.parametrize(
        "raw_version",
        [
            "",
            None,
            "   ",
        ],
    )
    def test_decompose_os_version_empty_returns_none(self, raw_version):
        """Empty/None versions should return (None, None)."""
        version, name = device._decompose_os_version(raw_version)
        assert version is None
        assert name is None

    def test_decompose_os_version_no_digits(self):
        """Version with no digits should return (None, text_part)."""
        version, name = device._decompose_os_version("MacOS")
        assert version is None
        assert name == "MacOS"

    def test_decompose_os_version_underscore_normalization(self):
        """Underscores should be converted to dots."""
        version, name = device._decompose_os_version("Windows_10_0_19041")
        # After replacing _ with ., we get Windows.10.0.19041
        # The regex should extract 10.0.19041, not .10.0.19041 or .
        assert version == "10.0.19041", f"Expected '10.0.19041' but got '{version}'"
        assert name == "Windows"

    def test_decompose_os_version_leading_text_extraction(self):
        """Should extract leading non-numeric text as OS name."""
        version, name = device._decompose_os_version("Ubuntu-20.04")
        assert version == "20.04"
        assert name == "Ubuntu"


class TestCompositeClientName:
    """Test the _composite_client_name function."""

    def test_composite_client_name_primary_only(self):
        """Should return primary client name if secondary is missing."""
        attrs = {"user_agent_client_name": "Chrome"}
        result = device._composite_client_name(attrs)
        assert result == "Chrome"

    def test_composite_client_name_both_different(self):
        """Should combine different client names with ' :: '."""
        attrs = {
            "user_agent_client_name": "Chrome",
            "user_agent_secondary_client_name": "WebView",
        }
        result = device._composite_client_name(attrs)
        assert result == "Chrome :: WebView"

    def test_composite_client_name_case_insensitive_match(self):
        """Should detect identical names regardless of casing."""
        attrs = {
            "user_agent_client_name": "Chrome",
            "user_agent_secondary_client_name": "chrome",
        }
        result = device._composite_client_name(attrs)
        # Should return just the primary (as they're considered the same)
        assert result == "Chrome"

    def test_composite_client_name_missing_primary(self):
        """Should return None if primary client name is missing."""
        attrs = {"user_agent_secondary_client_name": "WebView"}
        result = device._composite_client_name(attrs)
        assert result is None

    def test_composite_client_name_empty_primary(self):
        """Should return None if primary client name is empty."""
        attrs = {
            "user_agent_client_name": "",
            "user_agent_secondary_client_name": "WebView",
        }
        result = device._composite_client_name(attrs)
        assert result is None

    def test_composite_client_name_empty_secondary_ignored(self):
        """Should ignore empty secondary client name."""
        attrs = {
            "user_agent_client_name": "Safari",
            "user_agent_secondary_client_name": "",
        }
        result = device._composite_client_name(attrs)
        assert result == "Safari"

    def test_composite_client_name_whitespace_handling(self):
        """Should strip whitespace from both client names."""
        attrs = {
            "user_agent_client_name": "  Firefox  ",
            "user_agent_secondary_client_name": "  Mozilla  ",
        }
        result = device._composite_client_name(attrs)
        assert result == "Firefox :: Mozilla"


class TestNormalizeDeviceFields:
    """Test the normalize_device_fields function."""

    def test_normalize_device_fields_apple_model_resolution(self, mock_device_lookup):
        """Should resolve Apple model identifiers to model names."""
        attrs = {"device_model_identifier": "iPhone10,6"}
        result = device.normalize_device_fields(attrs)
        assert result["device_model_name"] == "iPhone X"
        assert result["norm__model_identifier"] == "iphone10,6"

    def test_normalize_device_fields_manufacturer_inference(self, mock_device_lookup):
        """Should infer manufacturer from model name."""
        attrs = {"device_model_name": "iPhone 12"}
        result = device.normalize_device_fields(attrs)
        assert result["norm__manufacturer"] == "apple"

    def test_normalize_device_fields_manufacturer_alias_resolution(
        self, mock_device_lookup
    ):
        """Should resolve manufacturer aliases."""
        attrs = {"device_manufacturer": "cupertino"}
        result = device.normalize_device_fields(attrs)
        assert result["norm__manufacturer"] == "apple"

    def test_normalize_device_fields_explicit_manufacturer_preferred(
        self, mock_device_lookup
    ):
        """Explicit manufacturer should be preferred over inference."""
        attrs = {"device_model_name": "Galaxy S20", "device_manufacturer": "Samsung"}
        result = device.normalize_device_fields(attrs)
        assert result["norm__manufacturer"] == "samsung"

    def test_normalize_device_fields_os_name_inference_from_version(
        self, mock_device_lookup
    ):
        """Should infer OS name from version string."""
        attrs = {"os_version": "iOS 15.7"}
        result = device.normalize_device_fields(attrs)
        assert result["norm__os_name"] == "ios"
        assert result["norm__os_version"] == "15.7"

    def test_normalize_device_fields_os_type_mapping(self, mock_device_lookup):
        """Should map OS name to OS type."""
        attrs = {"os_name": "iOS"}
        result = device.normalize_device_fields(attrs)
        assert result["norm__os_type"] == "mobile os"

    def test_normalize_device_fields_all_lowercase(self, mock_device_lookup):
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

    def test_normalize_device_fields_with_composite_client(self, mock_device_lookup):
        """Should normalize composite client names."""
        attrs = {
            "user_agent_client_name": "Chrome",
            "user_agent_secondary_client_name": "WebView",
        }
        result = device.normalize_device_fields(attrs)
        assert result["norm__client_name"] == "chrome :: webview"

    def test_normalize_device_fields_missing_fields(self, mock_device_lookup):
        """Should handle missing fields gracefully."""
        attrs = {}
        result = device.normalize_device_fields(attrs)
        # Should not create norm__ keys for missing fields
        norm_keys = [k for k in result.keys() if k.startswith("norm__")]
        assert len(norm_keys) == 0

    def test_normalize_device_fields_empty_string_ignored(self, mock_device_lookup):
        """Empty string values should not create normalized fields."""
        attrs = {"device_model_name": "", "device_manufacturer": "  "}
        result = device.normalize_device_fields(attrs)
        norm_keys = [k for k in result.keys() if k.startswith("norm__")]
        assert len(norm_keys) == 0

    def test_normalize_device_fields_cascading_fallback(self, mock_device_lookup):
        """OS name should cascade: explicit > inferred from version > OS type."""
        attrs = {"os_version": "Android 12", "os_type": "MobileOS"}
        result = device.normalize_device_fields(attrs)
        # Should use inferred "android" from version, not "MobileOS"
        assert result["norm__os_name"] == "android"

    def test_normalize_device_fields_preserves_original_attrs(self, mock_device_lookup):
        """Should preserve original attributes while adding norm__ fields."""
        attrs = {"device_model_name": "Pixel 6"}
        result = device.normalize_device_fields(attrs)
        assert result["device_model_name"] == "Pixel 6"  # Original preserved
        assert result["norm__model_name"] == "pixel 6"  # Normalized added

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
        self, mock_device_lookup, input_attrs, expected_norm_keys
    ):
        """Parametrized test for various attribute combinations."""
        result = device.normalize_device_fields(input_attrs)
        actual_norm_keys = {k for k in result.keys() if k.startswith("norm__")}
        assert actual_norm_keys == expected_norm_keys, (
            f"Expected {expected_norm_keys} but got {actual_norm_keys}"
        )
