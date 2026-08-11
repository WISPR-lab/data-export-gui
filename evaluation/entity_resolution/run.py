"""
FP Stalker entity-resolution evaluation.

Usage:
    uv run python -m evaluation.entity_resolution.run
    uv run python -m evaluation.entity_resolution.run --trials 1000
    uv run python -m evaluation.entity_resolution.run --no-download
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

# python_core/ isn't a proper package for pyodide reasons
_python_core = Path(__file__).resolve().parent.parent.parent / "python_core"
if str(_python_core) not in sys.path:
    sys.path.insert(0, str(_python_core))

import duckdb
import pandas as pd
from tqdm import tqdm

import evaluation.entity_resolution.config as cf
from evaluation.entity_resolution import fetch_data, sweep
import python_core.field_normalization.user_agent as ua
from python_core.field_normalization.device import normalize_device_fields

_ua_parser = ua.UserAgentParser()


def _load() -> pd.DataFrame:
    print(f"Loading FP Stalker from {cf.FP_STALKER_DB} ...")
    with duckdb.connect(str(cf.FP_STALKER_DB), read_only=True) as conn:
        raw = conn.execute(f"SELECT * FROM {cf.DB_TABLE}").df()

    records = []
    for _, row in tqdm(raw.iterrows(), total=len(raw), desc="Normalizing UA strings"):
        d = _ua_parser.parse({"user_agent_original": row.get("userAgentHttp", "")})
        d = normalize_device_fields(d)
        norm = {k: v for k, v in d.items() if k.startswith("norm__")}
        norm["timestamp"] = row.get("creationDate", "")
        records.append(norm)

    norm_df = pd.DataFrame(records, index=raw.index)
    norm_cols = [c for c in norm_df.columns if c.startswith("norm__")]
    keep = [c for c in ["id", "counter", "osDetailed", "browserDetailed"] if c in raw.columns]
    df = pd.concat([norm_df[["timestamp"] + norm_cols], raw[keep + ["userAgentHttp"]]], axis=1)
    df.rename(columns={c: f"attr__{c}" for c in norm_cols}, inplace=True)
    df.rename(columns={"id": "tracking_id", "counter": "id"}, inplace=True)
    return df


def main():
    parser = argparse.ArgumentParser(description="FP Stalker BCubed eval (independent sampling)")
    parser.add_argument("--trials", "-n", type=int, default=cf.DEFAULT_N_TRIALS,
                        help=f"Trials per (k, max_days) cell (default: {cf.DEFAULT_N_TRIALS})")
    parser.add_argument("--seed", type=int, default=cf.DEFAULT_SEED)
    parser.add_argument("--k", type=int, nargs="+", default=cf.K_OPTIONS,
                        help="K values to sweep (default: %(default)s)")
    parser.add_argument("--days", type=int, nargs="+", default=cf.MAX_DAYS_CLIENT_OPTIONS,
                        help="max_days_client values to sweep (default: %(default)s)")
    parser.add_argument("--no-download", action="store_true",
                        help="Skip the download prompt; fail if DB is not already present")

    args = parser.parse_args()

    print("=== FP Stalker Evaluation ===")
    print(f"Trials per cell: {args.trials} | Seed: {args.seed}")
    print(f"K: {args.k} | max_days: {args.days}")

    if args.no_download:
        if not cf.FP_STALKER_DB.exists():
            print(f"ERROR: --no-download set but {cf.FP_STALKER_DB} does not exist. Run without --no-download first.")
            sys.exit(1)
    else:
        fetch_data.fetch()

    df = _load()
    print(f"  {len(df)} rows, {df['tracking_id'].nunique()} unique tracking IDs")

    start = datetime.datetime.now()
    results = sweep.run_sweep(df, k_options=args.k, max_days_options=args.days,
                              n_trials=args.trials, seed=args.seed)
    elapsed = datetime.datetime.now() - start

    ts = start.isoformat().replace(":", "-").replace(".", "-")
    run_dir = cf.RUNS_DIR / f"fp_stalker_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "run": {
            "description": "FP Stalker BCubed eval — independent sampling",
            "start_time": start.isoformat(),
            "duration": str(elapsed),
            "n_trials": args.trials,
            "seed": args.seed,
            "k_options": args.k,
            "max_days_client_options": args.days,
        },
        "dataset": {
            "num_records": len(df),
            "num_tracking_ids": int(df["tracking_id"].nunique()),
        },
        "results": results,
    }

    with open(run_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=4)
    print(f"\nSummary written to {run_dir / 'summary.json'}")

    results_df = pd.DataFrame(results)
    results_df.to_csv(run_dir / "results.csv", index=False)
    print(f"Results CSV written to {run_dir / 'results.csv'}")

    print("\n" + results_df.sort_values(["k", "max_days_client"]).to_string(index=False))
    print(f"\nDone in {elapsed}. Output: {run_dir}")


if __name__ == "__main__":
    main()
