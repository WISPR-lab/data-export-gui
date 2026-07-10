# added for WISPR-lab/data-export-gui
import json
from utils.redaction_utils import compare_redacted_vals

def resolve(raw_rows: list[dict]) -> list[dict]:
    """
    Builds the session and registration list for the Devices View.
    
    Pairs active sessions with trusted cookies sharing a client_session_id,
    and registered Apple devices with passkeys sharing a device_serial_number.
    """
    devices = _parsed_devices(raw_rows)
    
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
                # Group strictly by (entity_type, dev_key) to prevent cross-type merging
                group_key = (entity_type, dev_key)
                if group_key in registrations:
                    existing = registrations[group_key]
                    existing["attributes"].update(d["attributes"])
                else:
                    registrations[group_key] = d
            else:
                other_devices.append(d)
        else:
            other_devices.append(d)

    # Combine deduplicated registrations and other devices
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
            "os_version": attrs.get("os_version") or attrs.get("norm__os_version") or attrs.get("os_version"),
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
