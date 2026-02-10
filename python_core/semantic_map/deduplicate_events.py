DEFAULT_EVENT_ACTIONS_TO_EXCLUDE = []  # e.g. messages, potentially, which might be sent in quick succession

def deduplicate_events(
        event_rows: list[dict], # event_rows, from semantic_map_worker.py
        tolerance_ms=100,
        exclude=DEFAULT_EVENT_ACTIONS_TO_EXCLUDE) -> list[dict]:
    
    seen_originals = {}

    for e in event_rows:
        if e.get("event_action") in exclude:
            e['is_duplicate_of'] = -1
            continue

        kind = e.get('event_kind')
        action = e.get('event_action')
        ts = e.get('timestamp', 0)

        if ts == 0:  # skip deduplication
            e['is_duplicate_of'] = -1
            continue

        key = (kind, action)
        is_dup = False

        if key in seen_originals:
            for orig_event in seen_originals[key]:
                orig_ts = orig_event.get('timestamp', 0)
                if orig_ts != 0 and abs(orig_ts - ts) <= tolerance_ms:
                    e['is_duplicate_of'] = orig_event['id']
                    is_dup = True
                    break
        if not is_dup:
            e['is_duplicate_of'] = -1
            if key not in seen_originals:
                seen_originals[key] = []
            seen_originals[key].append(e)
    
    return event_rows