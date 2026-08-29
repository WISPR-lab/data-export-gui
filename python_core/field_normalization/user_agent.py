import re
from ua_extract import DeviceDetector
import field_normalization.device_lookup as dl
from python_core.logger import get_logger

logger = get_logger("user_agent")


class UserAgentParser:
    # fallback for Google webview UAs (e.g. "OcIdWebView") that embed version in a JSON blob
    GOOGLE_APP_VERSION_RE = re.compile(r'"appVersion":"([\d.]+)"')

    def __init__(self):
        self._cache = {}
        self.FBAN_RE = re.compile(r"FB([A-Z]+)/([^;\]]+)")

    def parse(self, attrs: dict, file_info=None) -> dict:
        ua_string = attrs.get("user_agent_original", "") or attrs.get(
            "user_agent_os_full", ""
        )
        is_google = False
        if file_info:
            mfst_id = file_info.get("manifest_file_id", "").lower()
            mfst_fname = file_info.get("manifest_filename", "").lower()
            is_google = mfst_id.startswith("google") or mfst_id.startswith("ggl")
            if mfst_id == "ggl_access_log_activity" or (
                is_google and "activities" in mfst_fname
            ):
                ua_string = self._synthesize_google_ua(ua_string)

        if ua_string:
            return self._parse(ua_string, is_google=is_google)
        return {}

    def _parse(self, ua_string: str, skip_bot_detection=True, is_google=False) -> dict:

        ua_string = ua_string.strip()
        if not ua_string:
            return {}

        cache_key = (ua_string, is_google)
        if cache_key in self._cache:
            return self._cache[cache_key]

        attrs = {}
        try:
            dd = DeviceDetector(
                ua_string, skip_bot_detection=skip_bot_detection
            ).parse()
        except Exception as e:
            logger.warning("DeviceDetector parse failure on UA '%s': %s", ua_string[:80], e)
            self._cache[cache_key] = {}
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
        elif "OcIdWebView" in ua_string:
            if m := self.GOOGLE_APP_VERSION_RE.search(ua_string):
                attrs["user_agent_secondary_client_version"] = m.group(1)
        if dd.secondary_client_type():
            attrs["user_agent_secondary_client_type"] = dd.secondary_client_type()

        if is_google:
            self._promote_google_api_client(ua_string, dd, attrs)
        if dd.is_mobile():
            attrs["user_agent_is_mobile"] = True
        if dd.is_desktop():
            attrs["user_agent_is_desktop"] = True
        if dd.is_television():
            attrs["user_agent_is_television"] = True
        if dd.uses_mobile_browser():
            attrs["user_agent_uses_mobile_browser"] = True
        if dd.os_name():
            os_name = dd.os_name()
            attrs["user_agent_os_name"] = os_name
            os_type = dl.resolve_pattern(os_name, dl.OS_TYPE_PATTERNS)
            if os_type:
                attrs["user_agent_os_type"] = os_type
        if dd.os_version():
            attrs["user_agent_os_version"] = dd.os_version()
        if dd.device_model():
            attrs["user_agent_device_model_name"] = dd.device_model()
        else:
            if dd.is_desktop():
                if dd.os_name():
                    os_type = attrs.get("user_agent_os_type")
                    if os_type == "windows":
                        attrs["user_agent_device_model_name"] = "Windows PC"
                    elif os_type == "linux":
                        attrs["user_agent_device_model_name"] = "Linux PC"
        if dd.device_brand():
            attrs["user_agent_device_manufacturer"] = dd.device_brand()
        if dd.device_type():
            attrs["user_agent_device_type"] = dd.device_type()

        attrs = self._parse_fban(ua_string, attrs)
        for k in ["user_agent_client_name", "user_agent_secondary_client_name"]:
            if attrs.get(k) == "GGLUnknown":
                attrs.pop(k)

        self._cache[cache_key] = attrs
        return attrs

    def _promote_google_api_client(self, ua_string: str, dd, attrs: dict) -> None:
        # native Google API-client UAs (e.g. "com.google.Gmail/6.0 iSL/3.4 iPhone/17.7.1 hw/...")
        # get mislabeled "Mobile Safari" by a generic catch-all -- the real client is the secondary
        if not (
            " iSL/" in ua_string
            and dd.client_name() == "Mobile Safari"
            and not dd.client_version()
            and dd.secondary_client_name()
        ):
            return
        attrs["user_agent_client_name"] = dd.secondary_client_name()
        attrs["user_agent_client_version"] = dd.secondary_client_version()
        attrs["user_agent_client_type"] = dd.secondary_client_type()
        attrs["user_agent_client_application_id"] = dd.client_application_id()
        attrs.pop("user_agent_secondary_client_name", None)
        attrs.pop("user_agent_secondary_client_version", None)
        attrs.pop("user_agent_secondary_client_type", None)

    def _parse_fban(self, ua_string: str, attrs: dict) -> dict:
        """
        Facebook/Instagram embed FBDV (Apple hardware model ID) in UA strings, e.g.:
        [FBAN/FBIOS;FBDV/iPhone11,8;...]
        DeviceDetector resolves FBDV into display name ("iPhone XR") but discards
        the raw identifier. We preserve it in user_agent_device_model_identifier
        for use as a static ID key in device grouping.
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
        logger.debug("Synthesized Google UA: %s", UA)
        return UA
