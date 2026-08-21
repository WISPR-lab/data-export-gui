"""

LINK EVENTS WITH CLIENT/OS UPGRADES OVER TIME

Modification of the rule-based algo from FP-Stalker (Vastel et al., 2018).
Link: https://inria.hal.science/hal-01652021/document
Login events with user agents are subject to browser/OS versions changing over time.
This attempts to add an edge between them. (Linking of logged-in-device/active-session
files -- e.g. matching serial numbers or session IDs -- happens separately in
deterministic_ids.py and resolved_sessions_registrations.py, not in this file.)


Client (browser/app) Upgrades -- _valid_client_upgrade(), always on

Key = (manufacturer if present else <unknown>, model, OS name, OS version, browser/app name)
Records are grouped by key, then sorted by timestamp within each group, then walked in order.

An edge is added between consecutive records A, B in that walk iff:
(a) 0 <= B.timestamp - A.timestamp <= MAX_DAYS_CLIENT_DIFF (30 by default)
(b) B.client_version >= A.client_version
Records missing client_version or any of the key fields (other than
manufacturer, because desktop UAs don't report it), are dropped before 
grouping and can't be linked at all -- there's no
version evidence to check them against. 

Candidate edges are are dropped if the two records have a hardware ID or platform-fingerprint column (imei/serial/device_id and
friends) that is present on both sides and differs

"""

import pandas as pd
import re
import json
from packaging import version

MAX_DAYS_CLIENT_DIFF = 30  # this is to sever spurious links across long time gaps

BASE_ATTRIBUTES = [
    "attr__norm__manufacturer",
    "attr__norm__model_name",
    "attr__norm__os_name",
    "attr__norm__client_name",
]
OS_VERSION = ["attr__norm__os_version"]
CLIENT_VERSION = ["attr__norm__client_version"]


def _has_required_columns(df: pd.DataFrame) -> bool:
    cols = BASE_ATTRIBUTES + OS_VERSION + ["timestamp"]
    return all(col in df.columns for col in cols)


def _coerce_version_string(v_str: str) -> str:
    if not v_str:
        return "0.0.0"
    clean = "".join(c for c in str(v_str) if c.isdigit() or c == ".")
    clean = re.sub(r"\.+", ".", clean).strip(".")
    return clean if clean else "0.0.0"


def compare_versions(v1: str, v2: str) -> str:
    if not v1 or not v2:
        return None
    if v1 == v2:
        return "EQ"
    try:
        p1 = version.parse(v1)
        p2 = version.parse(v2)
    except Exception:
        p1 = version.parse(_coerce_version_string(v1))
        p2 = version.parse(_coerce_version_string(v2))

    if p1 < p2:
        return "LT"
    elif p1 > p2:
        return "GT"
    else:
        return "EQ"


def _valid_client_upgrade(
    events_df: pd.DataFrame, max_days=MAX_DAYS_CLIENT_DIFF
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not _has_required_columns(events_df):
        return pd.DataFrame(columns=["id_a", "id_b", "type", "provenance"]), events_df

    keys = BASE_ATTRIBUTES + OS_VERSION
    df = events_df.copy()
    if "attr__norm__client_version" not in df.columns:
        df["attr__norm__client_version"] = None

    # Exclude manufacturer from required keys because desktop platforms (Windows/Linux)
    # do not have manufacturer information in their User Agents and would otherwise be dropped.
    required_keys = [c for c in BASE_ATTRIBUTES if c != "attr__norm__manufacturer"] + OS_VERSION
    df = df.dropna(subset=required_keys + CLIENT_VERSION + ["timestamp"])
    df = df.sort_values(by=keys + ["timestamp"])

    if df.empty:
        return pd.DataFrame(columns=["id_a", "id_b", "type", "provenance"]), df

    exceeds_max_time = (df["timestamp"].diff().dt.days > max_days).tolist()
    group_id = df.groupby(keys, dropna=False, sort=False).ngroup()
    no_id_match = group_id.ne(group_id.shift()).tolist()

    client_versions = df["attr__norm__client_version"].tolist()
    client_version_downgraded = [False] * len(client_versions)
    for i in range(1, len(client_versions)):
        if no_id_match[i]:
            continue
        if compare_versions(client_versions[i - 1], client_versions[i]) == "GT":
            client_version_downgraded[i] = True

    subgraph_boundaries = [
        a or b or c
        for a, b, c in zip(exceeds_max_time, no_id_match, client_version_downgraded)
    ]

    df["subgraph_id"] = pd.Series(subgraph_boundaries, index=df.index).cumsum().values

    edges_list = []
    for _, group_df in df.groupby("subgraph_id"):
        if len(group_df) > 1:
            ids = group_df["id"].tolist()
            versions = group_df["attr__norm__client_version"].tolist()
            for i in range(len(ids) - 1):
                edges_list.append(
                    {
                        "id_a": ids[i],
                        "id_b": ids[i + 1],
                        "provenance": json.dumps(
                            {
                                "column": "attr__norm__client_version",
                                "value": f"{versions[i]} -> {versions[i + 1]}",
                            }
                        ),
                    }
                )

    if edges_list:
        edges = pd.DataFrame(edges_list)
    else:
        edges = pd.DataFrame(columns=["id_a", "id_b", "provenance"])
    edges["type"] = "ClientUpgrade"
    return edges, df


def _stable_conflict_columns(df: pd.DataFrame) -> list[str]:
    hardware_cols = [
        c
        for c in df.columns
        if c in ("attr__device_id", "attr__device_serial_number", "attr__device_imei")
        # session ID deliberatly excluded here since it multiple can belong to a single device
    ]
    platform_fp_cols = [c for c in df.columns if c.startswith("attr__device_id")]
    return sorted(set(hardware_cols) | set(platform_fp_cols))


def _drop_stable_id_conflicts(edges: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    if edges.empty:
        return edges
    conflict_cols = _stable_conflict_columns(df)
    if not conflict_cols:
        return edges

    lookup = df.drop_duplicates(subset="id").set_index("id")[conflict_cols]
    a_vals = lookup.reindex(edges["id_a"]).reset_index(drop=True)
    b_vals = lookup.reindex(edges["id_b"]).reset_index(drop=True)
    both_present = a_vals.notna() & b_vals.notna()
    conflicts = (a_vals.ne(b_vals) & both_present).any(axis=1)
    return edges[~conflicts.values].reset_index(drop=True)


def get_edges(
    df: pd.DataFrame,
    max_days_client: int = MAX_DAYS_CLIENT_DIFF,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["id_a", "id_b", "type", "provenance"])

    client_upgrade_edges, _ = _valid_client_upgrade(df, max_days=max_days_client)
    combined = _drop_stable_id_conflicts(client_upgrade_edges, df)
    return combined.drop_duplicates()
