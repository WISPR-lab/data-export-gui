import pytest
from field_normalization.user_agent import normalize_ua_fields
from field_normalization.device import normalize_device_fields

_UA_CHROME_ANDROID = (
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"
)
_UA_SAFARI_MACOS = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
_UA_FBAN = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/21H221 "
    "[FBAN/FBIOS;FBDV/iPhone11,8;FBSN/iOS;FBSV/17.7.1;FBID/phone;FBAV/492.0]"
)
_UA_INSTAGRAM = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/20G75 "
    "Instagram 302.0.0.22.109 (iPhone14,2; iOS 16_6; en_US)"
)
_UA_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# ua_normalize: scope enforcement
# ---------------------------------------------------------------------------

def test_ua_normalize_only_writes_user_agent_namespace():
    fields = {'user_agent.original': _UA_CHROME_ANDROID}
    result = normalize_ua_fields(fields)
    written = [k for k in result if k != 'user_agent.original' and not k.startswith('user_agent.')]
    assert written == [], f"ua_normalize wrote non-user_agent fields: {written}"


def test_ua_normalize_no_ua_string_is_noop():
    fields = {'client.ip': '1.2.3.4'}
    result = normalize_ua_fields(fields)
    assert result == {'client.ip': '1.2.3.4'}


def test_ua_normalize_empty_string_is_noop():
    fields = {'user_agent.original': '   '}
    result = normalize_ua_fields(fields)
    assert set(result.keys()) == {'user_agent.original'}


# ---------------------------------------------------------------------------
# ua_normalize: standard UA parsing
# ---------------------------------------------------------------------------

def test_ua_normalize_android_chrome():
    result = normalize_ua_fields({'user_agent.original': _UA_CHROME_ANDROID})
    assert result.get('user_agent.os.name') == 'Android'
    assert result.get('user_agent.os.type') == 'android'
    assert result.get('user_agent.os.version') == '12'
    assert result.get('user_agent.device.manufacturer') == 'Samsung'
    assert result.get('user_agent.device.name') == 'Galaxy S21 5G'
    assert result.get('user_agent.device.type') == 'smartphone'


def test_ua_normalize_macos_safari():
    result = normalize_ua_fields({'user_agent.original': _UA_SAFARI_MACOS})
    assert result.get('user_agent.os.type') == 'macos'
    assert result.get('user_agent.name') == 'Safari'


def test_ua_normalize_windows():
    result = normalize_ua_fields({'user_agent.original': _UA_WINDOWS})
    assert result.get('user_agent.os.type') == 'windows'


def test_ua_normalize_fban_client_name():
    result = normalize_ua_fields({'user_agent.original': _UA_FBAN})
    assert result.get('user_agent.name') == 'Facebook'
    assert result.get('user_agent.os.type') == 'ios'


def test_ua_normalize_instagram_client_name():
    result = normalize_ua_fields({'user_agent.original': _UA_INSTAGRAM})
    assert result.get('user_agent.name') == 'Instagram'


# ---------------------------------------------------------------------------
# ua_normalize: FBAN identifier extraction
# ---------------------------------------------------------------------------

def test_ua_normalize_fban_extracts_identifier():
    result = normalize_ua_fields({'user_agent.original': _UA_FBAN})
    assert result.get('user_agent.device.model.identifier') == 'iPhone11,8'


def test_ua_normalize_non_fban_has_no_identifier():
    result = normalize_ua_fields({'user_agent.original': _UA_CHROME_ANDROID})
    assert 'user_agent.device.model.identifier' not in result


def test_ua_normalize_fban_identifier_is_additive_not_overwrite():
    # If a manifest has already set an identifier, ua_normalize must not overwrite it.
    fields = {
        'user_agent.original': _UA_FBAN,
        'user_agent.device.model.identifier': 'iPhone99,9',
    }
    result = normalize_ua_fields(fields)
    assert result['user_agent.device.model.identifier'] == 'iPhone99,9'


# ---------------------------------------------------------------------------
# ua_normalize: merge rules
# ---------------------------------------------------------------------------

def test_ua_normalize_manifest_value_wins_on_name():
    # user_agent.name is already set by a manifest (non-overwrite rule)
    fields = {'user_agent.original': _UA_FBAN, 'user_agent.name': 'FBIOS'}
    result = normalize_ua_fields(fields)
    assert result['user_agent.name'] == 'FBIOS'


def test_ua_normalize_more_specific_device_name_wins():
    # Manifest has "iPhone", UA derives "iPhone XR" — longer wins.
    fields = {'user_agent.original': _UA_FBAN, 'user_agent.device.name': 'iPhone'}
    result = normalize_ua_fields(fields)
    assert result['user_agent.device.name'] == 'iPhone XR'


def test_ua_normalize_manifest_longer_device_name_kept():
    # Manifest already has a longer/more specific name — must not be downgraded.
    fields = {'user_agent.original': _UA_FBAN, 'user_agent.device.name': 'iPhone XR (custom label)'}
    result = normalize_ua_fields(fields)
    assert result['user_agent.device.name'] == 'iPhone XR (custom label)'


def test_ua_normalize_more_version_components_wins():
    # Manifest has partial version, UA derives more specific one.
    fields = {'user_agent.original': _UA_FBAN, 'user_agent.os.version': '17'}
    result = normalize_ua_fields(fields)
    assert result['user_agent.os.version'] == '17.7.1'


def test_ua_normalize_manifest_full_version_not_downgraded():
    # Manifest already has the more-specific version.
    fields = {'user_agent.original': _UA_FBAN, 'user_agent.os.version': '17.7.1.3'}
    result = normalize_ua_fields(fields)
    assert result['user_agent.os.version'] == '17.7.1.3'


# ---------------------------------------------------------------------------
# ua_normalize: robustness
# ---------------------------------------------------------------------------

def test_ua_normalize_garbage_input_no_crash():
    result = normalize_ua_fields({'user_agent.original': 'not-a-ua-string-@@##!!'})
    # Must not raise; original is preserved; nothing critical added
    assert result.get('user_agent.original') == 'not-a-ua-string-@@##!!'


# ---------------------------------------------------------------------------
# device_normalize: user_agent.device.* → device.* promotion
# ---------------------------------------------------------------------------

def test_device_normalize_promotes_manufacturer():
    fields = {'user_agent.device.manufacturer': 'Samsung'}
    result = normalize_device_fields(fields)
    assert result['device.manufacturer'] == 'Samsung'


def test_device_normalize_promotes_type():
    fields = {'user_agent.device.type': 'smartphone'}
    result = normalize_device_fields(fields)
    assert result['device.type'] == 'smartphone'


def test_device_normalize_promotes_identifier():
    fields = {'user_agent.device.model.identifier': 'iPhone11,8'}
    result = normalize_device_fields(fields)
    assert result['device.model.identifier'] == 'iPhone11,8'


def test_device_normalize_manifest_device_wins_over_ua():
    # A manifest-direct device.manufacturer must not be overwritten.
    fields = {
        'user_agent.device.manufacturer': 'Apple',
        'device.manufacturer': 'ACME Corp',
    }
    result = normalize_device_fields(fields)
    assert result['device.manufacturer'] == 'ACME Corp'


def test_device_normalize_ua_device_name_fills_model_name():
    fields = {'user_agent.device.name': 'Galaxy S21 5G'}
    result = normalize_device_fields(fields)
    assert result['device.model.name'] == 'Galaxy S21 5G'


def test_device_normalize_ua_device_name_specificity_longer_wins():
    fields = {
        'user_agent.device.name': 'iPhone XR',
        'device.model.name': 'iPhone',
    }
    result = normalize_device_fields(fields)
    assert result['device.model.name'] == 'iPhone XR'


def test_device_normalize_manifest_model_name_not_downgraded():
    fields = {
        'user_agent.device.name': 'iPhone',
        'device.model.name': 'iPhone XR (unlocked)',
    }
    result = normalize_device_fields(fields)
    assert result['device.model.name'] == 'iPhone XR (unlocked)'


# ---------------------------------------------------------------------------
# device_normalize: Apple identifier lookup
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("identifier,expected_name", [
    ('iPhone11,8', 'iPhone XR'),
    ('iPhone14,5', 'iPhone 13'),
    ('iPhone17,3', 'iPhone 16'),
    ('iPad14,1',   'iPad mini (6th gen)'),
    ('iPod9,1',    'iPod touch (7th gen)'),
])
def test_device_normalize_apple_identifier_lookup(identifier, expected_name):
    result = normalize_device_fields({'device.model.identifier': identifier})
    assert result['device.model.name'] == expected_name


def test_device_normalize_apple_lookup_skipped_if_name_present():
    # If device.model.name already set, identifier lookup must not overwrite.
    fields = {'device.model.identifier': 'iPhone11,8', 'device.model.name': 'My Custom Phone'}
    result = normalize_device_fields(fields)
    assert result['device.model.name'] == 'My Custom Phone'


def test_device_normalize_unknown_identifier_no_crash():
    fields = {'device.model.identifier': 'Bogus99,99'}
    result = normalize_device_fields(fields)
    assert 'device.model.name' not in result


def test_device_normalize_android_identifier_no_lookup():
    # Android identifiers (OEM build codes) are NOT in _APPLE_MODELS.
    fields = {'device.model.identifier': 'SM-G991B'}
    result = normalize_device_fields(fields)
    assert 'device.model.name' not in result


# ---------------------------------------------------------------------------
# Combined pipeline
# ---------------------------------------------------------------------------

def test_pipeline_fban_ua_full():
    fields = {'user_agent.original': _UA_FBAN}
    fields = normalize_ua_fields(fields)
    fields = normalize_device_fields(fields)

    assert fields.get('user_agent.name') == 'Facebook'
    assert fields.get('user_agent.os.type') == 'ios'
    assert fields.get('user_agent.device.model.identifier') == 'iPhone11,8'
    # device_normalize should have promoted and resolved these:
    assert fields.get('device.model.identifier') == 'iPhone11,8'
    assert fields.get('device.model.name') == 'iPhone XR'
    assert fields.get('device.manufacturer') == 'Apple'
    assert fields.get('device.type') == 'smartphone'


def test_pipeline_manifest_only_identifier_resolves():
    # No UA string — just a raw identifier from a manifest field (e.g. apple_messaging_devices).
    fields = {'device.model.identifier': 'iPhone16,1'}
    fields = normalize_device_fields(fields)
    assert fields['device.model.name'] == 'iPhone 15 Pro'


def test_pipeline_manifest_model_name_beats_ua():
    # Manifest sets device.model.name = "iPhone", UA would derive "iPhone XR".
    # device_normalize specificity rule: "iPhone XR" (longer) wins.
    fields = {
        'user_agent.original': _UA_FBAN,
        'device.model.name': 'iPhone',
    }
    fields = normalize_ua_fields(fields)
    fields = normalize_device_fields(fields)
    assert fields['device.model.name'] == 'iPhone XR'


def test_pipeline_ua_fields_preserved_alongside_device_fields():
    # After the full pipeline, user_agent.device.* must still be present
    # so callers can see provenance.
    fields = {'user_agent.original': _UA_CHROME_ANDROID}
    fields = normalize_ua_fields(fields)
    fields = normalize_device_fields(fields)

    assert 'user_agent.device.manufacturer' in fields
    assert 'user_agent.device.name' in fields
    assert fields['device.manufacturer'] == fields['user_agent.device.manufacturer']
    assert fields['device.model.name'] == fields['user_agent.device.name']
