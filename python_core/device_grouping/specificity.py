#  Calculate specificity level for atomic devices
#  Level 1: Generic (brand only or missing identifiers)
#  Level 2: Specific (has model name + version/variant)
#  Level 3: Hard ID (has deterministic identifiers like IMEI, serial, device_id, MEID)

from utils.device_lookup import VARIANT_SUFFIXES
from device_grouping.hard_merge import HARD_KEYS, IS_HARD_KEY

GENERIC = {'other', 'unknown', 'phone', 'smartphone', 'tablet', 'android', 'iphone', 'ipad', ''}



def _has_hard_id(attrs: dict) -> bool:
    for key in attrs:
        if IS_HARD_KEY(key) and attrs[key]:
            return True
    return False


def _has_version_or_variant(name: str) -> bool:
    if not name:
        return False
    words = {w.lower().rstrip('.,') for w in name.split()}
    return bool(words & VARIANT_SUFFIXES) or any(c.isdigit() for c in name)


def _is_generic_name(name: str) -> bool:
    return not name or name.strip().lower() in GENERIC


def _get_best_model(attrs: dict) -> str:
    candidates = [
        attrs.get('device_model_name', ''),
        attrs.get('user_agent_device_model', ''),
    ]
    candidates = [v.strip() for v in candidates if v and v.strip()]
    if not candidates:
        return ''
    return max(candidates, key=lambda x: not _is_generic_name(x))


def specificity(attrs: dict) -> int:
    if not attrs:
        return 1
    
    if _has_hard_id(attrs):
        return 3
    
    model = _get_best_model(attrs)
    if model and not _is_generic_name(model) and _has_version_or_variant(model):
        return 2
    
    return 1
