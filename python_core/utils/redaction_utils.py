import re

MIN_ASTERISKS = 3
PATTERN = rf'\*{{{MIN_ASTERISKS},}}'

def unmasked_segments(value: str) -> list[str]:
    if not value:
        return []
    return [p.strip() for p in re.split(PATTERN, value) if p.strip()]


def is_masked(value: str) -> bool:
    if not value or not isinstance(value, str):
        return False
    return bool(re.search(PATTERN, value))


def compare_redacted_vals(*vals) -> bool:
    if len(vals) == 1 and isinstance(vals[0], list):
        vals = vals[0]
    
    if not vals or len(vals) < 2:
        return False
    
    for v in vals:
        if v and not isinstance(v, str):
            raise ValueError(f"Expected string values, got {type(v).__name__}: {v!r}")
    
    all_parts_lower = []
    for v in vals:
        parts = unmasked_segments(v)
        parts = [p.lower() for p in parts if p]
        if not parts:
            return False
        all_parts_lower.extend(parts)
    
    for v in vals:
        parts = [p.lower() for p in unmasked_segments(v) if p]
        if not any(p in all_parts_lower or any(p in ap or ap in p for ap in all_parts_lower) 
                   for p in parts):
            return False
    
    return True


def get_unredacted_val(*vals) -> tuple[str]:
    if not compare_redacted_vals(vals):
        return '', 'error: values do not match'
    for v in vals:
        if v and isinstance(v, str) and not is_masked(v):
            return v, ''
    return '', 'error: all values are masked'