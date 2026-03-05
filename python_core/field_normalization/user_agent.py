import re
from device_detector import DeviceDetector

_FBAN_TOKEN_RE = re.compile(r'FB([A-Z]+)/([^;\]]+)')
_GENERIC = {'other', 'unknown', 'generic smartphone', 'generic feature phone', 'spider', ''}

# ua_normalize writes ONLY user_agent.* fields.
# custom fields follow the rule: suffix after 'user_agent.' must be a valid ECS field.
#   user_agent.device.name        (ECS native: user_agent.device.name)
#   user_agent.device.manufacturer (suffix: device.manufacturer)
#   user_agent.device.model.identifier (suffix: device.model.identifier)
#   user_agent.device.type        (suffix: device.type)
# then resolved into device.* by device_normalize.py.

_PREFER_MORE_SPECIFIC = {'user_agent.device.name'}
_PREFER_MORE_VERSION = {'user_agent.os.version'}
_ALWAYS_ADDITIVE = {'user_agent.device.model.identifier'}

_OS_TYPE_MAP = {
    'ios': 'ios', 'ipados': 'ios',
    'android': 'android', 'android tv': 'android', 'fire os': 'android', 'wear os': 'android', 'kaios': 'android',
    'mac': 'macos', 'macos': 'macos', 'mac os x': 'macos',
    'windows': 'windows', 'windows ce': 'windows', 'windows mobile': 'windows', 'windows phone': 'windows', 'windows rt': 'windows',
    'linux': 'linux', 'ubuntu': 'linux', 'debian': 'linux', 'fedora': 'linux', 'centos': 'linux',
    'chrome os': 'linux', 'chromium os': 'linux',
}


def _os_type(os_name: str) -> str:
    return _OS_TYPE_MAP.get(os_name.lower(), '')


def _nonempty(v: str) -> str:
    return v if v and v.lower() not in _GENERIC else ''


def _more_specific(existing: str, derived: str) -> str:
    e, d = (existing or '').strip(), (derived or '').strip()
    return d if d and len(d) > len(e) else (e or d)


def _more_version(existing: str, derived: str) -> str:
    e, d = (existing or '').strip(), (derived or '').strip()
    return d if d and d.count('.') > e.count('.') else (e or d)


# ---- FACEBOOK-SPECIFIC -------------------------------------------------------
# Facebook/Instagram embed FBDV (Apple hardware model ID) in the UA string, e.g.:
#   [FBAN/FBIOS;FBDV/iPhone11,8;...]
# DeviceDetector resolves FBDV into a display name ("iPhone XR") but discards
# the raw identifier. We preserve it in user_agent.device.model.identifier;
# device_normalize.py uses it as a hard clustering key.
def _enrich_fban(ua_string: str, parsed: dict) -> None:
    if '[FBAN/' not in ua_string:
        return
    tokens = {m.group(1): m.group(2) for m in _FBAN_TOKEN_RE.finditer(ua_string)}
    if tokens.get('DV'):
        parsed['user_agent.device.model.identifier'] = tokens['DV']  # e.g. "iPhone11,8"
# ------------------------------------------------------------------------------


def _parse_raw(ua_string: str) -> dict:
    try:
        dd = DeviceDetector(ua_string).parse()

        os_name = _nonempty(dd.os_name() or '')
        parsed = {
            'user_agent.name':                _nonempty(dd.client_name() or ''),
            'user_agent.version':             _nonempty(dd.client_version() or ''),
            'user_agent.os.name':             os_name,
            'user_agent.os.version':          _nonempty(dd.os_version() or ''),
            'user_agent.os.type':             _os_type(os_name),
            'user_agent.device.name':         _nonempty(dd.device_model() or ''),
            'user_agent.device.manufacturer': _nonempty(dd.device_brand() or ''),
            'user_agent.device.type':         _nonempty(dd.device_type() or ''),
        }

        _enrich_fban(ua_string, parsed)

        return {k: v for k, v in parsed.items() if v}
    except Exception as e:
        print(f"[ua_normalize] ERROR parsing {ua_string[:80]!r}: {type(e).__name__}: {e}")
        return {}


def normalize_ua_fields(fields: dict) -> dict:
    ua_string = fields.get('user_agent.original', '')
    if not ua_string or not ua_string.strip():
        return fields
    derived = _parse_raw(str(ua_string))
    for k, v in derived.items():
        existing = fields.get(k, '')
        if k in _ALWAYS_ADDITIVE:
            if not existing:
                fields[k] = v
        elif k in _PREFER_MORE_SPECIFIC:
            fields[k] = _more_specific(existing, v)
        elif k in _PREFER_MORE_VERSION:
            fields[k] = _more_version(existing, v)
        else:
            if not existing:
                fields[k] = v
    return fields
