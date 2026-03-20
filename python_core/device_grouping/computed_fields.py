from utils.redaction_utils import get_unredacted_val
from utils.device_lookup import VARIANT_SUFFIXES
from device_grouping.shared_utils import IS_HARD_KEY

GENERIC = {'other', 'unknown', 'phone', 'smartphone', 'tablet', 'android', 'iphone', 'ipad', ''}
MFR_DO_NOT_MERGE_GENERIC = {'apple'}


# ------------- HELPER FUNCTIONS -------------


def has_version_or_variant(name: str) -> bool:
    if not name:
        return False
    words = {w.lower().rstrip('.,') for w in name.split()}
    return bool(words & VARIANT_SUFFIXES) or any(c.isdigit() for c in name)


def is_generic_name(name: str) -> bool:
    return not name or name.strip().lower() in GENERIC


def pick_most_specific(values: list) -> str:
    """Pick the most specific/descriptive value from a list of values.
    Only works with string values. Non-strings are filtered out.
    Returns first non-empty string or empty string if none found."""
    string_values = []
    for v in values:
        if isinstance(v, str):
            v = v.strip()
            if v:
                string_values.append(v)
    
    if not string_values:
        return ''
    return max(string_values, key=lambda x: (not is_generic_name(x), has_version_or_variant(x)))


def best_model_attr(attrs: dict) -> str:
    return pick_most_specific([
        attrs.get('device_model_name', ''),
        attrs.get('user_agent_device_model', '')
    ])


def get_mfr(attrs: dict, lower=True) -> str:
    # extract manufacturer from device or UA fields, return first non-empty field (lowercased)
    for key in ['device_manufacturer', 'user_agent_device_manufacturer']:
        val = attrs.get(key, '').strip()
        if lower:
            val = val.lower()
        if val:
            return val
    return ''



# ------------- OTHERS -------------
def specificity(attrs: dict) -> int:
    #  Calculate specificity level for atomic devices
    #  Level 1: Generic (brand only or missing identifiers)
    #  Level 2: Specific (has model name + version/variant)
    #  Level 3: Hard ID (has deterministic identifiers like IMEI, serial, device_id, MEID)
    if not attrs:
        return 1
    
    if any(IS_HARD_KEY(k) and attrs[k] for k in attrs):
        return 3
    
    model = pick_most_specific([
        attrs.get('device_model_name', ''),
        attrs.get('user_agent_device_model', '')
    ])
    if model and not is_generic_name(model) and has_version_or_variant(model):
        return 2
    
    return 1


def is_generic(atomic: dict) -> int:
    attrs = atomic.get('attributes', {})
    spec = atomic.get('specificity', specificity(attrs))
    return 1 if (spec < 2 and get_mfr(attrs) in MFR_DO_NOT_MERGE_GENERIC) else 0

def deduplicate_origins(origins_list: list[dict]) -> list[dict]:
    return [dict(t) for t in set(tuple(sorted(d.items())) for d in origins_list)]





# ------------- ATTRIBUTES -------------
def merge_attrs(attrs_list: list[dict], mode: str = 'soft') -> dict:
    
    if not attrs_list:
        return {}
    
    if len(attrs_list) == 1:
        return attrs_list[0].copy()
    
    # Collect all unique keys and their values
    all_keys = set()
    for attrs in attrs_list:
        all_keys.update(attrs.keys())
    
    attrs_new = {}
    for k in all_keys:
        values = [attrs.get(k) for attrs in attrs_list if k in attrs and attrs.get(k)]
        
        if not values:
            attrs_new[k] = ''
        elif mode == 'hard' and IS_HARD_KEY(k):
            attrs_new[k] = get_unredacted_val(values[0], values[1] if len(values) > 1 else None)[0] or values[0]
        else:
            if all(isinstance(v, str) for v in values):
                attrs_new[k] = pick_most_specific(values)
            else:
                attrs_new[k] = next((v for v in values if v), '')
    
    return attrs_new




# --------------  COMPUTE DEVICE PROFILE FIELDS --------

def compute_device_profile_fields(device_profile_row: dict,  # this is a single device profile row with atomic_devices_ids field
                                  atomic_devices_rows: list[dict]  # this is the full list of atomic devices rows, to be filtered down to the relevant ones based on atomic_devices_ids
                                  ) -> dict:
    atomics = [a for a in atomic_devices_rows \
               if a['id'] in device_profile_row.get('atomic_devices_ids', [])]
    
    attrs = merge_attrs([a.get('attributes', {}) for a in atomics],  mode='soft')
    spec = specificity(attrs)
    
    return {
        'attributes': attrs,
        'specificity': spec,
        'model': best_model_attr(attrs),
        'manufacturer': get_mfr(attrs, ),
        'is_generic': is_generic({'attributes': attrs, 'specificity': spec}),
        'origins': deduplicate_origins([o for a in atomics for o in a.get('origins', [])])
    }
