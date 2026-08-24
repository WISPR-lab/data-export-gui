"""
Deterministic (ish) Hardware/Session IDs

Add an edge between two records, A and B, if:
(a) They share a matching hardware identifier:
    - Serial number (`attr__device_serial_number`)
    - IMEI (`attr__device_imei`)
    - Device ID (`attr__device_id`)
(b) OR they share matching Platform Fingerprints (e.g., advertising fingerprints)
(c) OR they share matching Session IDs (`attr__client_session_id`), taking redacted values into account.
"""

import pandas as pd
import json
from utils.redaction_utils import compare_redacted_vals


def _session_edges(s_df: pd.DataFrame, col: str) -> pd.DataFrame:
    # exact-value groups: star to one anchor row each, no pairwise compare needed
    edges = []  # (id_a, id_b, value_a, value_b)
    anchor_id = {}
    for value, group in s_df.groupby(col):
        ids = group["id"].tolist()
        anchor_id[value] = ids[0]
        for other_id in ids[1:]:
            a, b = sorted((ids[0], other_id))
            edges.append((a, b, value, value))

    # residual unique values only - augmentation/exact dupes never reach this point
    values = list(anchor_id)
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            va, vb = values[i], values[j]
            if compare_redacted_vals(va, vb):
                a, b = sorted((anchor_id[va], anchor_id[vb]))
                edges.append((a, b, va, vb))

    if not edges:
        return pd.DataFrame(columns=["id_a", "id_b", "type", "provenance"])

    out = pd.DataFrame(edges, columns=["id_a", "id_b", "value_a", "value_b"])
    out["type"] = "Session"
    out["provenance"] = out.apply(
        lambda r: json.dumps({"column": col, "value_a": r["value_a"], "value_b": r["value_b"]}),
        axis=1,
    )
    return out[["id_a", "id_b", "type", "provenance"]].drop_duplicates()


def get_edges(df: pd.DataFrame) -> pd.DataFrame:
    hardware_id_cols = [
        col
        for col in df.columns
        if col in ("attr__device_id", "attr__device_serial_number", "attr__device_imei")
    ]

    # Check if we have hardware ID columns in df
    available_hw_cols = [col for col in hardware_id_cols if col in df.columns]

    hardware_edges = pd.DataFrame(columns=["id_a", "id_b", "type", "provenance"])
    if available_hw_cols:
        melted_hw = (
            df[["id"] + available_hw_cols]
            .melt(
                id_vars=["id"],
                value_vars=available_hw_cols,
            )
            .dropna()
        )

        if not melted_hw.empty:
            melted_hw = melted_hw[melted_hw["value"].astype(str).str.strip() != ""]
        if not melted_hw.empty:
            merged = melted_hw.merge(
                melted_hw, on=["variable", "value"], suffixes=("_a", "_b")
            )
            matched_pairs = merged[merged["id_a"] < merged["id_b"]].copy()
            if not matched_pairs.empty:
                hardware_edges = matched_pairs[["id_a", "id_b"]].copy()
                hardware_edges["type"] = "Hardware"
                hardware_edges["provenance"] = matched_pairs.apply(
                    lambda r: json.dumps(
                        {"column": r["variable"], "value": r["value"]}
                    ),
                    axis=1,
                )

    # platform fingerprints
    platform_fp_cols = [col for col in df.columns if col.startswith("attr__device_id")]
    platform_fp_edges = pd.DataFrame(columns=["id_a", "id_b", "type", "provenance"])
    if platform_fp_cols:
        melted_fp = (
            df[["id"] + platform_fp_cols]
            .melt(
                id_vars=["id"],
                value_vars=platform_fp_cols,
            )
            .dropna()
        )
        if not melted_fp.empty:
            melted_fp = melted_fp[melted_fp["value"].astype(str).str.strip() != ""]
        if not melted_fp.empty:
            merged_fp = melted_fp.merge(
                melted_fp, on=["variable", "value"], suffixes=("_a", "_b")
            )
            matched_fp_pairs = merged_fp[merged_fp["id_a"] < merged_fp["id_b"]].copy()
            if not matched_fp_pairs.empty:
                platform_fp_edges = matched_fp_pairs[["id_a", "id_b"]].copy()
                platform_fp_edges["type"] = "PlatformFingerprint"
                platform_fp_edges["provenance"] = matched_fp_pairs.apply(
                    lambda r: json.dumps(
                        {"column": r["variable"], "value": r["value"]}
                    ),
                    axis=1,
                )

    # session ids
    session_edges = pd.DataFrame(columns=["id_a", "id_b", "type", "provenance"])
    session_id_col = "attr__client_session_id"
    if session_id_col in df.columns:
        s_df = df[["id", session_id_col]].dropna()
        if not s_df.empty:
            s_df = s_df[s_df[session_id_col].astype(str).str.strip() != ""]
        if not s_df.empty:
            session_edges = _session_edges(s_df, session_id_col)

    edges = pd.concat(
        [hardware_edges, platform_fp_edges, session_edges], ignore_index=True
    )
    return edges.drop_duplicates()
