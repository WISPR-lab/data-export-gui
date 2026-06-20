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
            merged = melted_hw.merge(melted_hw, on=["value"], suffixes=("_a", "_b"))
            matched_pairs = merged[merged["id_a"] < merged["id_b"]].copy()
            if not matched_pairs.empty:
                hardware_edges = matched_pairs[["id_a", "id_b"]].copy()
                hardware_edges["type"] = "Hardware"
                hardware_edges["provenance"] = matched_pairs.apply(
                    lambda r: json.dumps(
                        {"column": r["variable_a"], "value": r["value"]}
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
            merged_fp = melted_fp.merge(melted_fp, on=["value"], suffixes=("_a", "_b"))
            matched_fp_pairs = merged_fp[merged_fp["id_a"] < merged_fp["id_b"]].copy()
            if not matched_fp_pairs.empty:
                platform_fp_edges = matched_fp_pairs[["id_a", "id_b"]].copy()
                platform_fp_edges["type"] = "PlatformFingerprint"
                platform_fp_edges["provenance"] = matched_fp_pairs.apply(
                    lambda r: json.dumps(
                        {"column": r["variable_a"], "value": r["value"]}
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
            pairs = s_df.merge(s_df, how="cross", suffixes=("_a", "_b"))
            pairs = pairs[pairs["id_a"] < pairs["id_b"]]
            if not pairs.empty:
                matches = pairs.apply(
                    lambda r: compare_redacted_vals(
                        r[f"{session_id_col}_a"], r[f"{session_id_col}_b"]
                    ),
                    axis=1,
                )
                matched_session_pairs = pairs[matches].copy()
                if not matched_session_pairs.empty:
                    session_edges = matched_session_pairs[["id_a", "id_b"]].copy()
                    session_edges["type"] = "Session"
                    session_edges["provenance"] = matched_session_pairs.apply(
                        lambda r: json.dumps(
                            {
                                "column": session_id_col,
                                "value_a": r[f"{session_id_col}_a"],
                                "value_b": r[f"{session_id_col}_b"],
                            }
                        ),
                        axis=1,
                    )

    edges = pd.concat(
        [hardware_edges, platform_fp_edges, session_edges], ignore_index=True
    )
    return edges.drop_duplicates()
