"""

LINK EVENTS THAT WITH CLIENT/OS UPGRADES OVER TIME

Modification of the rule-based algo from FP-Stalker (Vastel et al., 2018).
Link: https://inria.hal.science/hal-01652021/document
Login events with user agents are subject to browser/OS versions changing over time.
This attempts to add an edge between them.
Finally, if the platform has a separate file of logged-in devices or active sessions,
we link those.


Pass 1 -- Client (browser/app) Upgrades
Add edge between two EVENT records, A and B, if:
(a) A is temporally before B based on timestamp
    AND they don't differ by more than MAX_DAYS_CLIENT_DIFF (60 by default)
(b) they share ALL of the following:
    - device manufacturer (e.g., Samsung, Apple)
    - device model
    - OS name (e.g., iOS, Android)
    - OS version (e.g., iOS 15.7, Android 12)
    - browser name (e.g., Chrome, Safari)
(c) AND the client/app/browser version shows a valid upgrade
    - The client version of B is >= A


Pass 2 -- OS upgrades
Add edge between two subgraphs, F and G, generated from Pass 1 if:
(a) the maximum timestamp in F is less than before the minimum timestamp in G
    AND they don't differ by more than MAX_DAYS_OS_DIFF (60 by default)
(b) they share ALL of the following:
    - device manufacturer (e.g., Samsung, Apple)
    - device model
    - OS name (e.g., iOS, Android) --> *but NOT version*
    - browser name (e.g., Chrome, Safari)
(c) AND the client/app/browser version shows a valid upgrade
    - The minimum client version in G >= the maximum in F.
(d) AND the OS version shows a valid upgrade
    - The OS version of G > that of F.

"""

import pandas as pd
import re
import json
from packaging import version

MAX_DAYS_CLIENT_DIFF = 30  # this is to sever spurious links across long time gaps
MAX_DAYS_OS_DIFF = 30

BASE_ATTRIBUTES = [
    "attr__norm__manufacturer",
    "attr__norm__model_name",
    "attr__norm__os_name",
    "attr__norm__client_name",
]
OS_VERSION = ["attr__norm__os_version"]
CLIENT_VERSION = ["attr__norm__client_version"]


def _has_required_columns(df: pd.DataFrame, subgraph_metadata=False) -> bool:
    cols = BASE_ATTRIBUTES + OS_VERSION + ["timestamp"]
    if subgraph_metadata:
        cols = cols + ["id", "subgraph_id"]
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


def _pass1_client(
    events_df: pd.DataFrame, max_days=MAX_DAYS_CLIENT_DIFF
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not _has_required_columns(events_df, subgraph_metadata=False):
        return pd.DataFrame(columns=["id_a", "id_b", "type", "provenance"]), events_df

    keys = BASE_ATTRIBUTES + OS_VERSION
    df = events_df.copy()
    if "attr__norm__client_version" not in df.columns:
        df["attr__norm__client_version"] = None

    df = df.dropna(subset=keys + ["timestamp"])
    df = df.sort_values(by=keys + ["timestamp"])

    if df.empty:
        return pd.DataFrame(columns=["id_a", "id_b", "type", "provenance"]), df

    exceeds_max_time = (df["timestamp"].diff().dt.days > max_days).tolist()
    no_id_match = (
        df[keys].fillna("").ne(df[keys].fillna("").shift()).any(axis=1).tolist()
    )

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


def _pass2_os(
    subgraph_df: pd.DataFrame, max_days=MAX_DAYS_OS_DIFF
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not _has_required_columns(subgraph_df, subgraph_metadata=True):
        return pd.DataFrame(
            columns=["id_a", "id_b", "type", "provenance"]
        ), pd.DataFrame()

    subgraph_summaries = (
        subgraph_df.groupby("subgraph_id")
        .agg(
            manufacturer=("attr__norm__manufacturer", "first"),
            model=("attr__norm__model_name", "first"),
            os_name=("attr__norm__os_name", "first"),
            client_name=("attr__norm__client_name", "first"),
            os_version=("attr__norm__os_version", "first"),
            min_ts=("timestamp", "min"),
            max_ts=("timestamp", "max"),
            client_v_start=("attr__norm__client_version", "first"),
            client_v_end=("attr__norm__client_version", "last"),
            first_node_id=("id", "first"),
            last_node_id=("id", "last"),
        )
        .reset_index()
    )

    pairs = subgraph_summaries.merge(
        subgraph_summaries,
        on=["manufacturer", "model", "os_name", "client_name"],
        suffixes=("_F", "_G"),
    )

    if pairs.empty:
        return pd.DataFrame(columns=["id_a", "id_b", "type", "provenance"]), pairs

    valid_time_sequence = pairs["max_ts_F"] < pairs["min_ts_G"]
    under_max_days = (pairs["min_ts_G"] - pairs["max_ts_F"]).dt.days <= max_days
    pairs = pairs[valid_time_sequence & under_max_days]

    # client upgrade from F to G
    valid_client_upgrade = pairs.apply(
        lambda x: compare_versions(x["client_v_start_G"], x["client_v_end_F"]) != "LT",
        axis=1,
    )
    pairs = pairs[valid_client_upgrade]

    # OS upgrade from F to G
    valid_os_upgrade = pairs.apply(
        lambda x: compare_versions(x["os_version_G"], x["os_version_F"]) == "GT", axis=1
    )
    pairs = pairs[valid_os_upgrade]

    if pairs.empty:
        return pd.DataFrame(columns=["id_a", "id_b", "type", "provenance"]), pairs

    edges = (
        pairs[["last_node_id_F", "first_node_id_G", "os_version_F", "os_version_G"]]
        .rename(columns={"last_node_id_F": "id_a", "first_node_id_G": "id_b"})
        .drop_duplicates()
    )
    edges["type"] = "OSUpgrade"
    edges["provenance"] = edges.apply(
        lambda r: json.dumps(
            {
                "column": "attr__norm__os_version",
                "value": f"{r['os_version_F']} -> {r['os_version_G']}",
            }
        ),
        axis=1,
    )
    return edges[["id_a", "id_b", "type", "provenance"]], pairs


def get_edges(df: pd.DataFrame, run_pass2: bool = None) -> pd.DataFrame:
    events_df = df[df["table"] == "events"]
    if events_df.empty:
        return pd.DataFrame(columns=["id_a", "id_b", "type", "provenance"])

    if run_pass2 is None:
        from python_core.utils.pyodide_utils import get_config_value
        run_pass2 = get_config_value("ENABLE_DEVICE_GROUPING_PASS2", False)

    pass1_edges, subgraph_df = _pass1_client(events_df)
    if run_pass2:
        pass2_edges, _ = _pass2_os(subgraph_df)
        combined = pd.concat([pass1_edges, pass2_edges], ignore_index=True)
    else:
        combined = pass1_edges
    return combined.drop_duplicates()
