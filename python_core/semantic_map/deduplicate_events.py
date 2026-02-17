import json

DEFAULT_EVENT_ACTIONS_TO_EXCLUDE = []  # e.g. messages, potentially, which might be sent in quick succession



def deduplicate_events(
        event_rows: list[dict], # event_rows, from semantic_map_worker.py
        tolerance_ms=100,
        merge_conflict_policy="keep_original", # or "log_conflict"
        exclude=DEFAULT_EVENT_ACTIONS_TO_EXCLUDE) -> list[dict]:        
    seen_originals = {}
    final_rows = []

    event_rows.sort(key=lambda x: x.get('timestamp') or 0)

    for e in event_rows:

        action = e.get("event_action")
        timestamp = e.get("timestamp", 0)

        if action in exclude or timestamp == 0:
            final_rows.append(e)
            continue

        kind = e.get('event_kind', '_unknown')
        key = (kind, action)
        is_dup = False

        if key in seen_originals:
            orig_event = seen_originals[key][-1] # optimization, need to test if works on all edge cases #TODO
            orig_ts = orig_event.get('timestamp', 0)

            if orig_ts != 0 and abs(orig_ts - timestamp) <= tolerance_ms:
                is_dup = True
                
                # merge new event INTO original event
                for r_id in e.get('raw_data_ids', []):
                    orig_event['raw_data_ids'].append(r_id)
                for f_id in e.get('file_ids', []):
                    orig_event['file_ids'].append(f_id)

                orig_event['extra_timestamps'].append(timestamp)
                orig_event['deduplicated'] = True

                # merge attributes
                new_attrs = e.get('attributes', {})
                orig_attrs = orig_event.get('attributes', {})
                for k, v in new_attrs.items():
                    if k not in orig_attrs:
                        orig_attrs[k] = v
                    elif orig_attrs[k] != v:
                        if merge_conflict_policy == "keep_original":
                            continue
                        elif merge_conflict_policy == "log_conflict":
                            # conflict - keep original but log the conflict in a special field
                            conflict_key = f"_conflict_{k}"
                            if conflict_key not in orig_attrs:
                                orig_attrs[conflict_key] = []
                            orig_attrs[conflict_key].append({"original": orig_attrs[k], "new": v, "timestamp": timestamp})

                orig_event['attributes'] = orig_attrs

        if not is_dup:
            if key not in seen_originals:
                seen_originals[key] = []
            seen_originals[key].append(e)
            final_rows.append(e)




# ----------------------------------------------------


def old_deduplicate_events(
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