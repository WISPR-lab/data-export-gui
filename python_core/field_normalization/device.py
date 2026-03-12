import re
from utils.device_lookup import APPLE_MODELS, MANUFACTURER_PATTERNS


def _infer_manufacturer(model_name: str) -> str | None:
    # Infer manufacturer from device model name using regex patterns
    if not model_name:
        return None
    model_name = model_name.strip()
    for manufacturer, patterns in MANUFACTURER_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, model_name, re.IGNORECASE):
                return manufacturer
    return None


def normalize_device_fields(attrs: dict) -> dict:
    # Normalize device_* fields in-place
    
    identifier = attrs.get('device_model_identifier', '').strip()
    if identifier:  # and not attrs.get('device_model_name'):
        name = APPLE_MODELS.get(identifier)
        if name:
            attrs['device_model_name'] = name
    
    model_name = attrs.get('device_model_name', '').strip()
    if model_name and not attrs.get('device_manufacturer'):
        mfr = _infer_manufacturer(model_name)
        if mfr:
            attrs['device_manufacturer'] = mfr
    
    return attrs
