# Resolves user_agent.device.* fields (written by ua_normalize) into device.*,
# and enriches device.model.name from device.model.identifier via Apple lookup.
# This is the only file that writes device.* from derived data.

_APPLE_MODELS = {
    'iPhone1,1': 'iPhone', 'iPhone1,2': 'iPhone 3G', 'iPhone2,1': 'iPhone 3GS',
    'iPhone3,1': 'iPhone 4', 'iPhone3,2': 'iPhone 4', 'iPhone3,3': 'iPhone 4',
    'iPhone4,1': 'iPhone 4S',
    'iPhone5,1': 'iPhone 5', 'iPhone5,2': 'iPhone 5',
    'iPhone5,3': 'iPhone 5c', 'iPhone5,4': 'iPhone 5c',
    'iPhone6,1': 'iPhone 5s', 'iPhone6,2': 'iPhone 5s',
    'iPhone7,1': 'iPhone 6 Plus', 'iPhone7,2': 'iPhone 6',
    'iPhone8,1': 'iPhone 6s', 'iPhone8,2': 'iPhone 6s Plus', 'iPhone8,4': 'iPhone SE',
    'iPhone9,1': 'iPhone 7', 'iPhone9,2': 'iPhone 7 Plus',
    'iPhone9,3': 'iPhone 7', 'iPhone9,4': 'iPhone 7 Plus',
    'iPhone10,1': 'iPhone 8', 'iPhone10,2': 'iPhone 8 Plus',
    'iPhone10,3': 'iPhone X', 'iPhone10,4': 'iPhone 8',
    'iPhone10,5': 'iPhone 8 Plus', 'iPhone10,6': 'iPhone X',
    'iPhone11,2': 'iPhone XS', 'iPhone11,4': 'iPhone XS Max',
    'iPhone11,6': 'iPhone XS Max', 'iPhone11,8': 'iPhone XR',
    'iPhone12,1': 'iPhone 11', 'iPhone12,3': 'iPhone 11 Pro',
    'iPhone12,5': 'iPhone 11 Pro Max', 'iPhone12,8': 'iPhone SE (2nd gen)',
    'iPhone13,1': 'iPhone 12 mini', 'iPhone13,2': 'iPhone 12',
    'iPhone13,3': 'iPhone 12 Pro', 'iPhone13,4': 'iPhone 12 Pro Max',
    'iPhone14,2': 'iPhone 13 Pro', 'iPhone14,3': 'iPhone 13 Pro Max',
    'iPhone14,4': 'iPhone 13 mini', 'iPhone14,5': 'iPhone 13',
    'iPhone14,6': 'iPhone SE (3rd gen)',
    'iPhone14,7': 'iPhone 14', 'iPhone14,8': 'iPhone 14 Plus',
    'iPhone15,2': 'iPhone 14 Pro', 'iPhone15,3': 'iPhone 14 Pro Max',
    'iPhone15,4': 'iPhone 15', 'iPhone15,5': 'iPhone 15 Plus',
    'iPhone16,1': 'iPhone 15 Pro', 'iPhone16,2': 'iPhone 15 Pro Max',
    'iPhone16,3': 'iPhone 16e',
    'iPhone17,1': 'iPhone 16 Pro', 'iPhone17,2': 'iPhone 16 Pro Max',
    'iPhone17,3': 'iPhone 16', 'iPhone17,4': 'iPhone 16 Plus',
    # iPad
    'iPad1,1': 'iPad', 'iPad2,1': 'iPad 2', 'iPad2,2': 'iPad 2',
    'iPad2,3': 'iPad 2', 'iPad2,4': 'iPad 2',
    'iPad2,5': 'iPad mini', 'iPad2,6': 'iPad mini', 'iPad2,7': 'iPad mini',
    'iPad3,1': 'iPad (3rd gen)', 'iPad3,2': 'iPad (3rd gen)', 'iPad3,3': 'iPad (3rd gen)',
    'iPad3,4': 'iPad (4th gen)', 'iPad3,5': 'iPad (4th gen)', 'iPad3,6': 'iPad (4th gen)',
    'iPad4,1': 'iPad Air', 'iPad4,2': 'iPad Air', 'iPad4,3': 'iPad Air',
    'iPad4,4': 'iPad mini 2', 'iPad4,5': 'iPad mini 2', 'iPad4,6': 'iPad mini 2',
    'iPad4,7': 'iPad mini 3', 'iPad4,8': 'iPad mini 3', 'iPad4,9': 'iPad mini 3',
    'iPad5,1': 'iPad mini 4', 'iPad5,2': 'iPad mini 4',
    'iPad5,3': 'iPad Air 2', 'iPad5,4': 'iPad Air 2',
    'iPad6,3': 'iPad Pro 9.7"', 'iPad6,4': 'iPad Pro 9.7"',
    'iPad6,7': 'iPad Pro 12.9"', 'iPad6,8': 'iPad Pro 12.9"',
    'iPad6,11': 'iPad (5th gen)', 'iPad6,12': 'iPad (5th gen)',
    'iPad7,1': 'iPad Pro 12.9" (2nd gen)', 'iPad7,2': 'iPad Pro 12.9" (2nd gen)',
    'iPad7,3': 'iPad Pro 10.5"', 'iPad7,4': 'iPad Pro 10.5"',
    'iPad7,5': 'iPad (6th gen)', 'iPad7,6': 'iPad (6th gen)',
    'iPad7,11': 'iPad (7th gen)', 'iPad7,12': 'iPad (7th gen)',
    'iPad8,1': 'iPad Pro 11"', 'iPad8,2': 'iPad Pro 11"',
    'iPad8,3': 'iPad Pro 11"', 'iPad8,4': 'iPad Pro 11"',
    'iPad8,5': 'iPad Pro 12.9" (3rd gen)', 'iPad8,6': 'iPad Pro 12.9" (3rd gen)',
    'iPad8,7': 'iPad Pro 12.9" (3rd gen)', 'iPad8,8': 'iPad Pro 12.9" (3rd gen)',
    'iPad8,9': 'iPad Pro 11" (2nd gen)', 'iPad8,10': 'iPad Pro 11" (2nd gen)',
    'iPad8,11': 'iPad Pro 12.9" (4th gen)', 'iPad8,12': 'iPad Pro 12.9" (4th gen)',
    'iPad11,1': 'iPad mini (5th gen)', 'iPad11,2': 'iPad mini (5th gen)',
    'iPad11,3': 'iPad Air (3rd gen)', 'iPad11,4': 'iPad Air (3rd gen)',
    'iPad11,6': 'iPad (8th gen)', 'iPad11,7': 'iPad (8th gen)',
    'iPad12,1': 'iPad (9th gen)', 'iPad12,2': 'iPad (9th gen)',
    'iPad13,1': 'iPad Air (4th gen)', 'iPad13,2': 'iPad Air (4th gen)',
    'iPad13,4': 'iPad Pro 11" (3rd gen)', 'iPad13,5': 'iPad Pro 11" (3rd gen)',
    'iPad13,6': 'iPad Pro 11" (3rd gen)', 'iPad13,7': 'iPad Pro 11" (3rd gen)',
    'iPad13,8': 'iPad Pro 12.9" (5th gen)', 'iPad13,9': 'iPad Pro 12.9" (5th gen)',
    'iPad13,10': 'iPad Pro 12.9" (5th gen)', 'iPad13,11': 'iPad Pro 12.9" (5th gen)',
    'iPad13,16': 'iPad Air (5th gen)', 'iPad13,17': 'iPad Air (5th gen)',
    'iPad13,18': 'iPad (10th gen)', 'iPad13,19': 'iPad (10th gen)',
    'iPad14,1': 'iPad mini (6th gen)', 'iPad14,2': 'iPad mini (6th gen)',
    'iPad14,3': 'iPad Pro 11" (4th gen)', 'iPad14,4': 'iPad Pro 11" (4th gen)',
    'iPad14,5': 'iPad Pro 12.9" (6th gen)', 'iPad14,6': 'iPad Pro 12.9" (6th gen)',
    'iPad14,8': 'iPad Air 11" M2', 'iPad14,9': 'iPad Air 11" M2',
    'iPad14,10': 'iPad Air 13" M2', 'iPad14,11': 'iPad Air 13" M2',
    'iPad16,1': 'iPad mini (7th gen)', 'iPad16,2': 'iPad mini (7th gen)',
    'iPad16,3': 'iPad Pro 11" M4', 'iPad16,4': 'iPad Pro 11" M4',
    'iPad16,5': 'iPad Pro 13" M4', 'iPad16,6': 'iPad Pro 13" M4',
    # iPod
    'iPod1,1': 'iPod touch', 'iPod2,1': 'iPod touch (2nd gen)',
    'iPod3,1': 'iPod touch (3rd gen)', 'iPod4,1': 'iPod touch (4th gen)',
    'iPod5,1': 'iPod touch (5th gen)', 'iPod7,1': 'iPod touch (6th gen)',
    'iPod9,1': 'iPod touch (7th gen)',
}


def _apple_model_name(identifier: str) -> str:
    return _APPLE_MODELS.get(identifier, '')


def _more_specific(existing: str, derived: str) -> str:
    e, d = (existing or '').strip(), (derived or '').strip()
    return d if d and len(d) > len(e) else (e or d)


def normalize_device_fields(fields: dict) -> dict:
    for ua_key, dev_key in (
        ('user_agent.device.manufacturer', 'device.manufacturer'),
        ('user_agent.device.type',         'device.type'),
        ('user_agent.device.model.identifier', 'device.model.identifier'),
    ):
        v = fields.get(ua_key, '')
        if v and not fields.get(dev_key, ''):
            fields[dev_key] = v

    ua_name = fields.get('user_agent.device.name', '')
    if ua_name:
        fields['device.model.name'] = _more_specific(fields.get('device.model.name', ''), ua_name)

    identifier = fields.get('device.model.identifier', '')
    if identifier and not fields.get('device.model.name', ''):
        name = _apple_model_name(identifier)
        if name:
            fields['device.model.name'] = name

    return fields
