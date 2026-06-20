import re
from ua_extract import DeviceDetector
from python_core.field_normalization.device_lookup import OS_TYPE_MAP


class UserAgentParser:
    def __init__(self):
        self._cache = {}
        self.FBAN_RE = re.compile(r"FB([A-Z]+)/([^;\]]+)")

    def parse(self, attrs: dict, file_info=None) -> dict:
        ua_string = attrs.get("user_agent_original", "") or attrs.get(
            "user_agent_os_full", ""
        )
        if file_info:
            mfst_id = file_info.get("manifest_file_id", "").lower()
            mfst_fname = file_info.get("manifest_filename", "").lower()
            if mfst_id == "ggl_access_log_activity" or (
                mfst_id.startswith("google")
                or mfst_id.startswith("ggl")
                and "activities" in mfst_fname
            ):
                ua_string = self._synthesize_google_ua(ua_string)

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
            dd = DeviceDetector(
                ua_string, skip_bot_detection=skip_bot_detection
            ).parse()
        except Exception as e:
            print(
                f"[ua_normalize] ERROR parsing {ua_string[:80]!r}: {type(e).__name__}: {e}"
            )
            self._cache[ua_string] = {}
            return {}

        if dd.client_name() and not attrs.get("user_agent_client_name"):
            attrs["user_agent_client_name"] = dd.client_name()
        if dd.client_version():
            attrs["user_agent_client_version"] = dd.client_version()
        if dd.client_type():
            attrs["user_agent_client_type"] = dd.client_type()
        if dd.client_application_id():
            attrs["user_agent_client_application_id"] = dd.client_application_id()
        if dd.secondary_client_name():
            attrs["user_agent_secondary_client_name"] = dd.secondary_client_name()
        if dd.secondary_client_version():
            attrs["user_agent_secondary_client_version"] = dd.secondary_client_version()
        if dd.secondary_client_type():
            attrs["user_agent_secondary_client_type"] = dd.secondary_client_type()
        if dd.is_mobile():
            attrs["user_agent_is_mobile"] = True
        if dd.is_desktop():
            attrs["user_agent_is_desktop"] = True
        if dd.is_television():
            attrs["user_agent_is_television"] = True
        if dd.uses_mobile_browser():
            attrs["user_agent_uses_mobile_browser"] = True
        if dd.os_name():
            attrs["user_agent_os_name"] = dd.os_name()
            attrs["user_agent_os_type"] = OS_TYPE_MAP.get(dd.os_name().lower(), "")
        if dd.os_version():
            attrs["user_agent_os_version"] = dd.os_version()
        if dd.device_model():
            attrs["user_agent_device_model_name"] = dd.device_model()
        if dd.device_brand():
            attrs["user_agent_device_manufacturer"] = dd.device_brand()
        if dd.device_type():
            attrs["user_agent_device_type"] = dd.device_type()

        attrs = self._parse_fban(ua_string, attrs)
        for k in ["user_agent_client_name", "user_agent_secondary_client_name"]:
            if attrs.get(k) == "GGLUnknown":
                attrs.pop(k)

        self._cache[ua_string] = attrs
        return attrs

    def _parse_fban(self, ua_string: str, attrs: dict) -> dict:
        """
        Facebook/Instagram embed FBDV (Apple hardware model ID) in UA strings, e.g.:
        [FBAN/FBIOS;FBDV/iPhone11,8;...]
        DeviceDetector resolves FBDV into display name ("iPhone XR") but discards
        the raw identifier. We preserve it in user_agent_device_model_identifier
        for use as a hard clustering key in device grouping.
        """
        if "[FBAN/" not in ua_string:
            return attrs
        tokens = {m.group(1): m.group(2) for m in self.FBAN_RE.finditer(ua_string)}
        if tokens.get("DV"):
            attrs["user_agent_device_model_identifier"] = tokens["DV"]

        return attrs

    def _synthesize_google_ua(self, ua_string: str) -> dict:
        """
        Google activity headers have a different format and often include a JSON blob with more structured info.
        This attempts to extract that info.
        Example UA:
        "App : GMM_APP. App Version : 24.47.3. Os : IOS_OS. Os Version : 17.7.1. Device Type : MOBILE."
        """
        pattern = r"\s*([^:]+?)\s*:\s*(.*?)\.(?:\s+|$)"
        matches = dict(re.findall(pattern, ua_string))
        app = matches.get("App", "GGLUnknown")
        app_ver = matches.get("App Version", "")
        os_raw = matches.get("Os", "")
        os_ver = matches.get("Os Version", "")

        os_map = {
            "IOS_OS": f"iPhone; iOS {os_ver}",
            "ANDROID_OS": f"Linux; Android {os_ver}",
            "WINDOWS_OS": f"Windows NT {os_ver}",
            "MAC_OS": f"Macintosh; Intel Mac OS X {os_ver.replace('.', '_')}",
            "CHROME_OS": f"X11; CrOS x86_64 {os_ver}",
        }
        os_fragment = os_map.get(os_raw, f"{os_raw} {os_ver}")

        app_map = {
            # [android version, ios version]
            "GMAIL": ["com.google.android.gm", "com.google.gmail"],
            "GSA": [
                "com.google.android.googlequicksearchbox",
                "com.google.googlemobile",
            ],
            "GMM": ["com.google.android.apps.maps", "com.google.maps"],
            "PLAY": ["com.android.vending", ""],
            "DOCS": ["com.google.android.apps.docs.editors.docs", "com.google.docs"],
            "SLIDES": [
                "com.google.android.apps.docs.editors.slides",
                "com.google.slides",
            ],
            "SAFARI_WEBVIEW": ["", "Mobile Safari"],
            "DRIVE": ["com.google.android.apps.docs", "com.google.drive"],
            "ASSISTANT": ["com.google.android.apps.bard", "com.google.gemini"],
            "SHEETS_APP": [
                "com.google.android.apps.docs.editors.sheets",
                "com.google.sheets",
            ],
            "PHOTOS": ["com.google.android.apps.photos", "com.google.photos"],
            "CALENDAR": ["com.google.android.calendar", "com.google.calendar"],
            "YOUTUBE": ["com.google.android.youtube", "com.google.ios.youtube"],
            "CHROME": ["com.android.chrome", "com.google.chrome.ios"],
        }

        for key, bundle_id in app_map.items():
            if key.lower() in app.lower():
                if "android" in os_raw.lower():
                    app = bundle_id[0]
                elif "ios" in os_raw.lower():
                    app = bundle_id[1]
                break
        UA = f"{app}/{app_ver} ({os_fragment})"
        print(f"[UA Parser] Synthesized Google UA: {UA}")
        return UA
