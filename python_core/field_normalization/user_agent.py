import re
from ua_extract import DeviceDetector
from utils.device_lookup import OS_TYPE_MAP


class UserAgentParser:
    def __init__(self):
        self._cache = {}
        self.FBAN_RE = re.compile(r'FB([A-Z]+)/([^;\]]+)')


    def parse(self, attrs: dict) -> dict:
        ua_string = attrs.get('user_agent_original', '') or attrs.get('user_agent_os_full', '')
        if ua_string:
            return self._parse(ua_string)
        return {}

    def _parse(self, ua_string: str, skip_bot_detection=True) -> dict:
        
        ua_string = ua_string.strip()
        if not ua_string:
            return {}

        if ua_string in self._cache:
            return self._cache[ua_string]
        
        attrs = {}
        try:
            dd = DeviceDetector(ua_string, skip_bot_detection=skip_bot_detection).parse()
        except Exception as e:
            print(f"[ua_normalize] ERROR parsing {ua_string[:80]!r}: {type(e).__name__}: {e}")
            self._cache[ua_string] = {}
            return {}
        
        if dd.client_name() and not attrs.get('user_agent_name'):
            attrs['user_agent_name'] = dd.client_name()
        if dd.client_version():
            attrs['user_agent_version'] = dd.client_version()
        if dd.client_type():
            attrs['user_agent_type'] = dd.client_type()
        if dd.client_application_id():
            attrs['user_agent_client_application_id'] = dd.client_application_id()
        if dd.secondary_client_name():
            attrs['user_agent_secondary.name'] = dd.secondary_client_name()
        if dd.secondary_client_version():
            attrs['user_agent_secondary_version'] = dd.secondary_client_version()
        if dd.secondary_client_type():
            attrs['user_agent_secondary_type'] = dd.secondary_client_type()
        if dd.is_mobile():
            attrs['user_agent_is_mobile'] = True
        if dd.is_desktop():
            attrs['user_agent_is_desktop'] = True
        if dd.is_television():
            attrs['user_agent_is_television'] = True
        if dd.uses_mobile_browser():
            attrs['user_agent_uses_mobile_browser'] = True
        if dd.os_name():
            attrs['user_agent_os.name'] = dd.os_name()
            attrs['user_agent_os_type'] = OS_TYPE_MAP.get(dd.os_name().lower(), '')
        if dd.os_version():
            attrs['user_agent_os_version'] = dd.os_version()
        if dd.device_model():
            attrs['user_agent_device_model'] = dd.device_model()
        if dd.device_brand():
            attrs['user_agent_device_manufacturer'] = dd.device_brand()
        if dd.device_type():
            attrs['user_agent_device_type'] = dd.device_type()

        attrs = self.parse_fban(ua_string, attrs)
        
        
        self._cache[ua_string] = attrs
        return attrs
    

    def parse_fban(self, ua_string: str, attrs: dict) -> dict:
        """
        Facebook/Instagram embed FBDV (Apple hardware model ID) in UA strings, e.g.:
        [FBAN/FBIOS;FBDV/iPhone11,8;...]
        DeviceDetector resolves FBDV into display name ("iPhone XR") but discards
        the raw identifier. We preserve it in user_agent_device_model.identifier
        for use as a hard clustering key in device grouping.
        """
        if '[FBAN/' not in ua_string:
            return attrs
        tokens = {m.group(1): m.group(2) for m in self.FBAN_RE.finditer(ua_string)}
        if tokens.get('DV'):
            attrs['user_agent_device_model_identifier'] = tokens['DV']

        return attrs

