"""
Device Profiles - matching manufacturer and model names
"""

import uuid
from typing import List, Tuple
from .instances import DeviceInstance


def calculate_profile_updates(
    instances: List[DeviceInstance],
    existing_instances: List[dict],
    existing_mappings: List[dict],
    ts: float,
) -> Tuple[List[dict], List[dict]]:
    # Compares the active batch of device instances against current database profiles to determine which new profiles
    # must be generated, returning structured rows for both device_profiles_v2 and device_profile_instances tables.

    inst_to_profile = {
        r.get("device_instance_id"): r.get("device_profile_id")
        for r in existing_mappings
        if r.get("device_instance_id")
    }
    existing_profiles = {}
    for inst in existing_instances:
        inst_id = inst.get("id")
        if inst_id and inst_id in inst_to_profile:
            man = inst.get("manufacturer")
            mod = inst.get("model")
            os_type = inst.get("os_type")
            key = (
                man.lower() if man else "",
                mod.lower() if mod else "",
                os_type.lower() if os_type else "",
            )
            existing_profiles[key] = inst_to_profile[inst_id]

    device_profiles_v2_rows = []
    device_profile_instances_rows = []

    for inst in instances:
        man = inst.manufacturer
        mod = inst.model
        os_type = inst.os_type
        key = (
            man.lower() if man else "",
            mod.lower() if mod else "",
            os_type.lower() if os_type else "",
        )

        if key in existing_profiles:
            profile_id = existing_profiles[key]
        else:
            profile_id = str(uuid.uuid4())
            device_profiles_v2_rows.append(
                {
                    "id": profile_id,
                    "manufacturer": man,
                    "model": mod,
                    "os_type": os_type,
                    "created_at": ts,
                    "updated_at": ts,
                }
            )
            existing_profiles[key] = profile_id

        device_profile_instances_rows.append(
            {"device_profile_id": profile_id, "device_instance_id": inst.root_id}
        )

    return device_profiles_v2_rows, device_profile_instances_rows
