"""
Run N independent trials for a given (k, max_days_client) pair.

Each trial independently samples k tracking IDs from the full pool (with replacement
across trials, without replacement within a trial), assigns them a synthetic user ID,
runs the device grouping heuristic, and computes BCubed precision/recall.
"""
import numpy as np
import pandas as pd

from python_core.device_grouping2 import client_os_upgrades
from python_core.device_grouping2.instances import DeviceInstanceGraph


def _bcubed(df: pd.DataFrame, pred_col: str) -> tuple[float, float]:
    same_per_inst = df.groupby([pred_col, "tracking_id"]).transform("size")
    precision = float((same_per_inst / df.groupby(pred_col).transform("size")).mean())
    recall = float((same_per_inst / df.groupby("tracking_id").transform("size")).mean())
    return precision, recall


def _run_trial(trial_df: pd.DataFrame, max_days_client: int) -> tuple[float, float]:
    """
    trial_df: rows for exactly k tracking IDs, all under synth_user_id = 0.
    Returns (bcubed_precision, bcubed_recall).
    """
    trial_df = trial_df.copy()
    edges = client_os_upgrades.get_edges(trial_df, max_days_client=max_days_client)
    graph = DeviceInstanceGraph(trial_df, pd.DataFrame(edges))

    pred = pd.Series(index=trial_df.index, dtype=object)
    for i, inst in enumerate(graph.get_instances()):
        pred.loc[inst.df.index] = f"inst_{i}"
    trial_df["_pred"] = pred
    return _bcubed(trial_df, "_pred")


def run_sweep(
    df: pd.DataFrame,
    k_options: list,
    max_days_options: list,
    n_trials: int,
    seed: int,
) -> list[dict]:
    """
    Returns a list of result dicts, one per (k, max_days, trial) combination.
    Caller can aggregate however they like.
    """
    rng = np.random.default_rng(seed)
    all_ids = df["tracking_id"].dropna().unique()
    print(f"\nPool: {len(all_ids)} unique tracking IDs")
    print(f"Sweep: K={k_options}, max_days={max_days_options}, {n_trials} trials each\n")

    results = []
    total_cells = len(k_options) * len(max_days_options)
    cell = 0

    for k in k_options:
        if k > len(all_ids):
            print(f"  Skipping k={k}: pool only has {len(all_ids)} IDs.")
            continue
        for max_days in max_days_options:
            cell += 1
            print(f"[{cell}/{total_cells}] k={k}, max_days={max_days} — running {n_trials} trials ...")

            precisions, recalls = [], []
            for t in range(n_trials):
                sampled_ids = rng.choice(all_ids, size=k, replace=False)
                trial_df = df[df["tracking_id"].isin(sampled_ids)].copy()
                p, r = _run_trial(trial_df, max_days_client=max_days)
                precisions.append(p)
                recalls.append(r)

            mean_p = float(np.mean(precisions))
            mean_r = float(np.mean(recalls))
            f1 = 2 * mean_p * mean_r / (mean_p + mean_r) if (mean_p + mean_r) > 0 else 0.0
            f05 = 1.25 * mean_p * mean_r / (0.25 * mean_p + mean_r) if (0.25 * mean_p + mean_r) > 0 else 0.0
            print(f"  → precision={mean_p:.4f}  recall={mean_r:.4f}  F1={f1:.4f}  F0.5={f05:.4f}")

            results.append({
                "k": k,
                "max_days_client": max_days,
                "n_trials": n_trials,
                "mean_bcubed_precision": mean_p,
                "mean_bcubed_recall": mean_r,
                "bcubed_f1": f1,
                "bcubed_f05": f05,
                "std_precision": float(np.std(precisions)),
                "std_recall": float(np.std(recalls)),
            })

    return results
