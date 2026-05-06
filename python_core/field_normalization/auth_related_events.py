import json
import re

AUTH_EVENT_ACTIONS = {
    "user_login",
    "user_logout",
    "session_start",
    "session_end",
    "password"
}
AUTH_EVENT_CATEGORIES = {
    "authentication", "session"
}
AUTH_DEVICE_ATTR_KEYS = {
    "device_model_identifier", 
    "device_model_name",
    "device_manufacturer",
    "user_agent_device_model",
    "user_agent_device_manufacturer",
    "user_agent_device_model_identifier",
    "user_agent_os_name",
    "user_agent_os_type",
    "user_agent_device_type"
}


def treat_event_as_auth_device(event_row: dict) -> bool:
    """TODO docs"""
    action = event_row.get("action", "").lower()
    categories = event_row.get("category", [])
    if isinstance(categories, str) and categories.startswith('['):
        categories = json.loads(categories.strip())
    categories = [str(c).strip().lower() for c in categories]
    
    is_auth_event = \
        any(re.search(re.escape(a), action) for a in AUTH_EVENT_ACTIONS) \
        or any(c in AUTH_EVENT_CATEGORIES for c in categories)
    
    # if not is_auth_event:
    #     return False
    
    # now check if has enough attributes
    attr_keys = set(event_row.get("attributes", {}).keys())
    if attr_keys.intersection(AUTH_DEVICE_ATTR_KEYS):
        return True
    
    return False