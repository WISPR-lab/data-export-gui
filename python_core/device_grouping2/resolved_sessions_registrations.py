# added for WISPR-lab/data-export-gui
import json
from datetime import datetime, timezone
from utils.redaction_utils import compare_redacted_vals

def resolve(raw_rows: list[dict], event_rows: list[dict] = None) -> list[dict]:
    """
    Builds the session and registration list for the Devices View.
    
    Pairs active sessions with trusted cookies sharing a client_session_id,
    and registered Apple devices with passkeys sharing a device_serial_number.
    """
    devices = _parsed_devices(raw_rows)
    events = _parsed_events(event_rows)

    # Group events by client_session_id
    session_events = {}
    for ev in events:
        sid = ev["attributes"].get("client_session_id")
        if not sid:
            continue
        if sid not in session_events:
            session_events[sid] = []
        session_events[sid].append(ev)

    # Synthesize sessions from events history if not present in raw devices
    raw_sids = {
        d["attributes"].get("client_session_id")
        for d in devices
        if d["entity_type"] == "session" and d["attributes"].get("client_session_id")
    }

    for sid, evs in session_events.items():
        if sid not in raw_sids:
            first_ev = min(evs, key=lambda e: e["timestamp"])
            attrs = {"client_session_id": sid, "inactive": True}
            for k in ("device_model_name", "norm__model_name", "model",
                      "user_agent_client_name", "norm__client_name", "client_name",
                      "user_agent_os_full", "norm__os_name", "os_name",
                      "os_version", "norm__os_version",
                      "norm__os_type", "os_type", "user_agent_original", "user_agent"):
                for ev in evs:
                    if k in ev["attributes"]:
                        attrs[k] = ev["attributes"][k]
                        break

            devices.append({
                "id": f"synthetic_session_{sid}",
                "upload_id": first_ev["upload_id"],
                "entity_type": "session",
                "origin": first_ev["origin"],
                "attributes": attrs
            })

    # Bolster session timestamps with event boundaries (widest bound).
    # ponytail: assumes timestamps are UTC ISO strings as stored; no epoch conversion needed.
    for d in devices:
        if d["entity_type"] != "session":
            continue
        sid = d["attributes"].get("client_session_id")
        if not sid or sid not in session_events:
            continue

        evs = session_events[sid]
        min_ev_ts = min(e["timestamp"] for e in evs)
        max_ev_ts = max(e["timestamp"] for e in evs)

        attrs = d["attributes"]
        curr_first = attrs.get("entity_first_seen_timestamp")
        curr_last = attrs.get("entity_last_seen_timestamp")

        # Widen bounds: event timestamps win if they extend the range
        final_first = min(curr_first, min_ev_ts) if curr_first else min_ev_ts
        final_last = max(curr_last, max_ev_ts) if curr_last else max_ev_ts

        attrs["entity_first_seen_timestamp"] = final_first
        attrs["entity_last_seen_timestamp"] = final_last

    passkeys = [d for d in devices if d["entity_type"] == "passkey_registration"]
    cookies = [d for d in devices if d["entity_type"] == "trusted_cookie"]

    # Deduplicate registrations of the SAME type sharing same hardware ID
    registrations = {}
    other_devices = []
    
    for d in devices:
        if d["entity_type"] in ("trusted_cookie", "passkey_registration"):
            continue
            
        entity_type = d["entity_type"]
        if entity_type in ("app_registration", "hardware_registration"):
            dev_key = None
            for k, v in d["attributes"].items():
                if v and (k.startswith("device_id") or k in ("device_serial_number", "device_imei")):
                    dev_key = str(v)
                    break
                    
            if dev_key:
                group_key = (entity_type, dev_key)
                if group_key in registrations:
                    registrations[group_key]["attributes"].update(d["attributes"])
                else:
                    registrations[group_key] = d
            else:
                other_devices.append(d)
        else:
            other_devices.append(d)

    filtered_devices = list(registrations.values()) + other_devices

    rows = []
    for dev in filtered_devices:
        attrs = dev["attributes"]
        serial = attrs.get("device_serial_number")
        session_id = attrs.get("client_session_id")

        has_passkey = 0
        if serial:
            for pk in passkeys:
                pk_serial = pk["attributes"].get("device_serial_number")
                if pk_serial and compare_redacted_vals(serial, pk_serial):
                    has_passkey = 1
                    break

        cookie_id = None
        if session_id:
            for tc in cookies:
                tc_sid = tc["attributes"].get("client_session_id")
                if tc_sid and compare_redacted_vals(session_id, tc_sid):
                    cookie_id = tc["id"]
                    break

        rows.append({
            "id": dev["id"],
            "upload_id": dev["upload_id"],
            "entity_type": dev["entity_type"],
            "origin": dev["origin"],
            "model_name": attrs.get("device_model_name") or attrs.get("norm__model_name") or attrs.get("model"),
            "client_name": attrs.get("user_agent_client_name") or attrs.get("norm__client_name") or attrs.get("client_name"),
            "os_name": attrs.get("user_agent_os_full") or attrs.get("norm__os_name") or attrs.get("os_name"),
            "os_version": attrs.get("os_version") or attrs.get("norm__os_version"),
            "os_type": attrs.get("norm__os_type") or attrs.get("os_type"),
            "attributes": json.dumps(attrs),
            "is_reduced_ua": 1 if "mobile/15e148" in str(attrs.get("user_agent_original") or "").lower() else 0,
            "has_trusted_cookie": 1 if cookie_id else 0,
            "trusted_cookie_id": cookie_id,
            "has_passkey": has_passkey,
            "registration_device": attrs.get("registration_device")
        })

    return rows


def _parsed_devices(raw_rows: list[dict]) -> list[dict]:
    parsed = []
    for r in raw_rows:
        attrs = {}
        if r["attributes"]:
            try:
                attrs = json.loads(r["attributes"]) if isinstance(r["attributes"], str) else r["attributes"]
            except Exception:
                pass
        parsed.append({
            "id": r["id"],
            "upload_id": r["upload_id"],
            "entity_type": r["entity_type"],
            "origin": r["origin"],
            "attributes": attrs
        })
    return parsed


def _parsed_events(event_rows: list[dict]) -> list[dict]:
    parsed = []
    if not event_rows:
        return parsed
    for r in event_rows:
        attrs = {}
        if r["attributes"]:
            try:
                attrs = json.loads(r["attributes"]) if isinstance(r["attributes"], str) else r["attributes"]
            except Exception:
                pass
        parsed.append({
            "id": r["id"],
            "upload_id": r["upload_id"],
            "origin": r["origin"],
            "timestamp": r["timestamp"],
            "attributes": attrs
        })
    return parsed
