import re
import python_core.utils.time_utils as time_utils
import json

RESERVED_COLUMNS = {
    'id', 'upload_id', 'file_id', 'timestamp', 'event_kind', 
    'event_action', 'message', 'tags', 'labels', 'is_duplicate_of'
}

def build_where_clause(query_string, filter_obj):
    conditions = []
    params = []

    _apply_index_filters(filter_obj, conditions, params)
    _apply_chip_filters(filter_obj, conditions, params)
    _apply_text_query(query_string, conditions, params)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    return where_clause, params

# --- Helpers ---

def _get_json_path(key):
    return f"$.{key}"

def _apply_index_filters(filter_obj, conditions, params):
    indices = filter_obj.get('indices', [])
    if indices and '_all' not in indices:
        placeholders = ','.join(['?'] * len(indices))
        conditions.append(f"e.upload_id IN ({placeholders})")
        params.extend(indices)

def _apply_chip_filters(filter_obj, conditions, params):
    for chip in filter_obj.get('chips', []):
        c_type = chip.get('type')
        c_val = chip.get('value')
        c_op = chip.get('operator', 'must')
        
        # skip malformed chips
        if c_val is None and c_type != 'datetime': 
            continue

        if c_type == 'label':
            # c_val is guaranteed not None here
            _handle_label_chip(c_val, c_op, conditions, params)
            
        elif c_type == 'term':
            _handle_term_chip(chip, c_val, c_op, conditions, params)
            
        elif c_type.startswith('datetime'):
            # Datetime might handle empty strings, but ensure it's a string
            _handle_datetime_chip(str(c_val) if c_val else "", conditions, params)

def _handle_label_chip(value, operator, conditions, params):
    # 'must_not' implies NOT LIKE
    clause = f"e.labels {('NOT' if operator == 'must_not' else '')} LIKE ?"
    conditions.append(clause)
    params.append(f'%"{value}"%')

def _handle_term_chip(chip, value, operator, conditions, params):
    field = chip.get('field')
    if not field: return # Safety check
    
    sql_op = "!=" if operator == 'must_not' else "="
    
    if field == 'event_kind':
        conditions.append(f"e.event_kind {sql_op} ?")
    else:
        path = _get_json_path(field)
        conditions.append(f"json_extract(e.attributes, '{path}') {sql_op} ?")
    
    params.append(value)

def _handle_datetime_chip(value_str, conditions, params):
    # Safe against empty input
    if not value_str: return

    parts = value_str.split(',')
    start_raw = parts[0].strip() if len(parts) > 0 else '*'
    end_raw = parts[1].strip() if len(parts) > 1 else '*'

    if start_raw and start_raw != '*':
        start_dt = time_utils.parse_date(start_raw)
        if start_dt:
            conditions.append("e.timestamp >= ?")
            params.append(time_utils.unix_ms(start_dt))

    if end_raw and end_raw != '*':
        end_dt = time_utils.parse_date(end_raw)
        if end_dt:
            conditions.append("e.timestamp <= ?")
            params.append(time_utils.unix_ms(end_dt))

def _apply_text_query(query_string, conditions, params):
    if not query_string or query_string.strip() == "*":
        return

    tokens = query_string.split()
    for token in tokens:
        if ":" in token:
            _handle_keyed_search(token, conditions, params)
        else:
            _handle_global_search(token, conditions, params)

def _handle_keyed_search(token, conditions, params):
    try:
        key, val = token.split(":", 1)
        val = val.strip('"\'')
    except ValueError:
        # Handle cases where token ends with ':' or has no value
        return 
    
    if key in ['message', 'event_kind', 'event_action']:
        conditions.append(f"e.{key} LIKE ?")
    else:
        path = _get_json_path(key)
        conditions.append(f"json_extract(e.attributes, '{path}') LIKE ?")
    
    params.append(f"%{val}%")

def _handle_global_search(token, conditions, params):
    conditions.append("(e.message LIKE ? OR e.attributes LIKE ?)")
    params.extend([f"%{token}%", f"%{token}%"])