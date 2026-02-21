import re
import logging

# regex
# '([^']*)'   -> Captures quoted keys: 'Device ID'
# \[(\d+)\]   -> Captures list indices: [0]
# ([^.\[\]]+) -> Captures simple keys with or w/o dot: session and session.ip
PATH_REGEX = re.compile(r"'([^']*)'|\[(\d+)\]|([^.\[\]]+)")

def get_value_at_path(data, path, default=""):
    """
    Traverses a dictionary/list structure using a dot-notation path.
    
    Supports:
    - Dot notation: "session.ip"
    - List indexing: "tokens[0].id"
    - Quoted keys (single quotes): "'Device ID'.timestamp"
    - Mixed usage: "items[0].'User Info'.id"
    """
    if data is None or not path:
        return default

    try:
        current = data
        
        # Iterates over all matches in the path string
        for match in PATH_REGEX.finditer(path):
            quoted_key, list_idx, simple_key = match.groups()

            if quoted_key:
                # dict key in quotes ('Device ID')
                if isinstance(current, dict):
                    current = current.get(quoted_key)
                else:
                    return default
            
            elif list_idx:
                # Clist index ([0])
                idx = int(list_idx)
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return default
            
            elif simple_key:
                # simple dict key
                if isinstance(current, dict):
                    current = current.get(simple_key)
                else:
                    return default

            if current is None:
                return default

        return current

    except Exception as e:
        logging.getLogger(__name__).debug(f"Error traversing path {path}: {e}")
        return default