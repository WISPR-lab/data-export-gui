import re

_MASK_RE = re.compile(r'^[\*Xx•\-_\s]{2,}(.{4,})$')
_FULLY_REDACTED_RE = re.compile(r'^\[?redacted\]?$', re.IGNORECASE)


def _is_redacted(value: str) -> bool:
    if _FULLY_REDACTED_RE.match(value.strip()):
        return True
    return bool(_MASK_RE.match(value.strip()))


def _extract_suffix(value: str, min_len: int = 4) -> str | None:
    m = _MASK_RE.match(value.strip())
    if m and len(m.group(1)) >= min_len:
        return m.group(1).strip()
    return None


def values_match(a: str, b: str, min_suffix_len: int = 4) -> bool:
    """
    Returns True if a and b refer to the same value, accounting for redaction.
    If either value is fully redacted (e.g. [redacted]), never matches.
    If either value is partially redacted, extracts the visible suffix and compares.
    """
    a, b = (a or '').strip(), (b or '').strip()
    if not a or not b:
        return False
    if _FULLY_REDACTED_RE.match(a) or _FULLY_REDACTED_RE.match(b):
        return False

    a_redacted = _is_redacted(a)
    b_redacted = _is_redacted(b)

    if not a_redacted and not b_redacted:
        return a.lower() == b.lower()

    a_cmp = _extract_suffix(a, min_suffix_len) if a_redacted else a
    b_cmp = _extract_suffix(b, min_suffix_len) if b_redacted else b

    if a_cmp is None or b_cmp is None:
        return False

    return a_cmp.lower().endswith(b_cmp.lower()) or b_cmp.lower().endswith(a_cmp.lower())
