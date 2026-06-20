import re
import field_normalization.device_lookup as dl


def _infer_manufacturer_from_model(model_name: str) -> str | None:
    if not model_name:
        return None
    model_name = model_name.strip()
    for manufacturer, patterns in dl.COMPILED_MANUFACTURER_MODEL_MAP.items():
        for pattern in patterns:
            if pattern.match(model_name):
                return manufacturer
    return None


def _has_version_or_variant(name: str) -> bool:
    if not name:
        return False
    words = {w.lower().rstrip(".,") for w in name.split()}
    return bool(words & dl.VARIANT_SUFFIXES) or any(c.isdigit() for c in name)


def _generic_model_name(name: str) -> bool:
    return not name or name.strip().lower() in dl.GENERIC_MODEL_NAMES


def _get_val(attrs: dict, key: str, preference="first") -> str | None:
    # By default, return the first non-empty value for the given key or its "user_agent_" variant.
    #
    # - preference == "non-generic" --> default to the non-generic value in list, where "generic" is defined heuristically
    #   as the value in the "GENERIC MODELS NAMES" list (like 'phone' or 'smartphone') and/or lacks
    #   version/variant info (i.e., iphone 7 vs iphone).
    # - preference == "longest" --> returns longest string
    if preference not in {"first", "non_generic", "longest"}:
        raise ValueError(f"Invalid preference {preference!r}")

    candidates = []
    for k in [key, "user_agent_" + key]:
        val = attrs.get(k)
        if val and str(val).strip():
            v = str(val).strip()
            if preference == "first":
                return v
            else:
                candidates.append(v)

    if preference == "non_generic" and candidates:
        return max(
            candidates,
            key=lambda x: (not _generic_model_name(x), _has_version_or_variant(x)),
        )
    elif preference == "longest" and candidates:
        return max(candidates, key=len)
    return None


def _decompose_os_version(raw_version: str) -> tuple:
    # separate out the version number from any leading text
    # (which may help infer OS type, e.g., "ios 15.7" or "android 12")
    if not raw_version:
        return None, None

    raw_clean = raw_version.strip()
    # Extract leading text before first digit (keep original separators)
    text_part = re.split(r"\d", raw_clean, maxsplit=1)[0].strip().strip("-_")
    inferred_name = text_part if text_part else None

    # Now replace underscores for version matching
    clean = raw_clean.replace("_", ".")
    num_match = re.search(r"\d+(?:\.\d+)*", clean)
    version_part = num_match.group(0) if num_match else None

    return version_part, inferred_name


def _composite_client_name(attrs: dict) -> str | None:
    client1 = attrs.get("user_agent_client_name")
    if client1 and str(client1).strip():
        client2 = attrs.get("user_agent_secondary_client_name")
        if client2 and str(client2).strip():
            client1 = str(client1).strip()
            client2 = str(client2).strip()
            if client1.lower() != client2.lower():
                return f"{client1} :: {client2}"
        return client1
    return None


# -------------------------


def normalize_device_fields(attrs: dict) -> dict:

    # resolve apple model identifiers (i.e., iPhone10,6) to model names (i.e., iPhone X)
    model_identifier = _get_val(attrs, "device_model_identifier")
    if model_identifier:
        name = dl.APPLE_MODELS.get(model_identifier)
        if name:
            attrs["device_model_name"] = name

    model_name = _get_val(attrs, "device_model_name", preference="non_generic")

    # infer manufacturer from model name if possible
    manufacturer = _get_val(attrs, "device_manufacturer")
    if not manufacturer:
        manufacturer = _infer_manufacturer_from_model(model_name)
    if manufacturer:
        if manufacturer.lower() not in dl.ALL_MFRS_LOWER:
            for _mfr, pattern in dl.COMPILED_MANUFACTURER_ALIASES_MAP.items():
                if pattern.search(manufacturer):
                    manufacturer = _mfr
                    break

    # now deal with OS
    os_version, inferred_os_name = _decompose_os_version(
        _get_val(attrs, "os_version", preference="longest")
    )
    os_type = _get_val(attrs, "os_type")
    os_name = _get_val(attrs, "os_name") or inferred_os_name or os_type
    if os_name:
        _os_type = dl.OS_TYPE_MAP.get(os_name.lower())
        if _os_type:
            os_type = _os_type

    client_name = _composite_client_name(attrs)

    # now every single event has some normalized fields we can easily query on for device grouping
    # downstream, even if we have to fall back to less specific fields for some events.
    if model_identifier:
        attrs["norm__model_identifier"] = str(model_identifier).strip().lower()
    if model_name:
        attrs["norm__model_name"] = str(model_name).strip().lower()
    if manufacturer:
        attrs["norm__manufacturer"] = str(manufacturer).strip().lower()
    if os_name:
        attrs["norm__os_name"] = str(os_name).strip().lower()
    if os_version:
        attrs["norm__os_version"] = str(os_version).strip().lower()
    if os_type:
        attrs["norm__os_type"] = str(os_type).strip().lower()
    if client_name:
        attrs["norm__client_name"] = (
            str(client_name).strip().lower()
        )  # TODO make sure not "unknown"
    client_version = _get_val(attrs, "client_version")
    if client_version:
        attrs["norm__client_version"] = str(client_version).strip().lower()

    return attrs
