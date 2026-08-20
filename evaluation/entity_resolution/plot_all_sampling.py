"""
Plot 3-panel BCubed metric heatmaps across sampling regimes (Full Dataset, Window N=30d, Window N=60d).

Modes:
  1. Plot pre-computed results (default):
     uv run python -m evaluation.entity_resolution.plot_all_sampling \
         --full path/to/full/results.csv \
         --n30 path/to/n30/results.csv \
         --n60 path/to/n60/results.csv

  2. Recompute pipeline from raw database:
     uv run python -m evaluation.entity_resolution.plot_all_sampling --recompute
"""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from evaluation.entity_resolution.config import (
    DB_TABLE,
    DEFAULT_N_TRIALS,
    DEFAULT_SEED,
    FP_STALKER_DB,
    K_OPTIONS,
    MAX_DAYS_CLIENT_OPTIONS,
    RUNS_DIR,
)

_METRICS = {
    "mean_bcubed_precision": ("B\u00b3 Precision", "precision_all_sampling.pdf", 0.8),
    "mean_bcubed_recall":    ("B\u00b3 Recall",    "recall_all_sampling.pdf",    0.2),
    "bcubed_f1":             ("B\u00b3 F1",         "f1_all_sampling.pdf",        0.4),
    "bcubed_f05":            ("B\u00b3 F0.5",       "f05_all_sampling.pdf",       0.6),
}

REGIMES = [
    {"key": "full", "title": "Full Dataset", "window_days": None},
    {"key": "n30",  "title": "Window (N=30d)", "window_days": 30},
    {"key": "n60",  "title": "Window (N=60d)", "window_days": 60},
]


def load_or_run_regime(
    regime: dict,
    input_path: Path,
    recompute: bool = False,
    n_trials: int = DEFAULT_N_TRIALS,
    seed: int = DEFAULT_SEED,
) -> pd.DataFrame:
    if input_path.is_dir():
        raise ValueError(f"Direct folders not supported for '{regime['key']}'. Pass a specific .csv or .json file.")

    if input_path.suffix == ".json":
        results_path = input_path.parent / "results.csv"
        regime_dir = input_path.parent
    elif input_path.suffix == ".csv":
        results_path = input_path
        regime_dir = input_path.parent
    else:
        results_path = input_path
        regime_dir = input_path.parent

    if recompute or not results_path.exists():
        import duckdb
        from evaluation.entity_resolution.sweep import run_sweep

        regime_dir.mkdir(parents=True, exist_ok=True)
        print(f"[RECOMPUTE] Running sweep for '{regime['title']}'...")
        con = duckdb.connect(str(FP_STALKER_DB), read_only=True)
        df = con.execute(f"SELECT tracking_id, timestamp FROM {DB_TABLE}").df()
        con.close()

        results = run_sweep(
            df=df,
            k_options=K_OPTIONS,
            max_days_options=MAX_DAYS_CLIENT_OPTIONS,
            n_trials=n_trials,
            seed=seed,
            window_days=regime["window_days"],
        )
        res_df = pd.DataFrame(results)
        res_df.to_csv(results_path, index=False)

        summary = {
            "run": {
                "n_trials": n_trials,
                "seed": seed,
                "window_days": [regime["window_days"]],
                "k_options": K_OPTIONS,
                "max_days_options": MAX_DAYS_CLIENT_OPTIONS,
            }
        }
        with open(regime_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)

    return pd.read_csv(results_path)


def plot_all_sampling(
    regime_dirs: dict,
    metric: str = "bcubed_f1",
    vmin: float = None,
    recompute: bool = False,
    out: Path = None,
    title_override: str = None,
    cmap: str = "YlGnBu",
) -> Path:
    label, default_fname, default_vmin = _METRICS.get(metric, (metric, f"{metric}_all_sampling.pdf", 0.4))

    # 1. Load data for all 3 regimes
    pivots = []
    for regime in REGIMES:
        r_dir = regime_dirs[regime["key"]]
        df = load_or_run_regime(regime, r_dir, recompute=recompute)

        # Filter strictly by config options
        df = df[df["k"].isin(K_OPTIONS) & df["max_days_client"].isin(MAX_DAYS_CLIENT_OPTIONS)]
        pivot = df.pivot(index="k", columns="max_days_client", values=metric)
        pivot = pivot.sort_index(ascending=False)
        pivots.append(pivot)

    # 2. Compute global vmin and vmax dynamically from data for maximum color contrast
    if vmin is None:
        vmin = min(p.min().min() for p in pivots)
    global_max = max(p.max().max() for p in pivots)

    # 3. Create 3-panel figure (7.0 in wide, shallow 2.3 in high)
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2), sharey=False)

    for idx, (regime, pivot, ax) in enumerate(zip(REGIMES, pivots, axes)):
        sns.heatmap(
            pivot,
            ax=ax,
            cmap=cmap,
            annot=True,
            fmt=".2f",
            linewidths=0.5,
            linecolor="white",
            square=False,
            vmin=vmin,
            vmax=global_max,
            cbar=False,
            annot_kws={"size": 7.0},
        )
        ax.set_title(regime["title"], fontsize=7.5, fontweight="normal", pad=3)

        # Y-axis handling: K ticks on all panels, label on panel 0 only
        if idx == 0:
            ax.set_ylabel("K (devices)", fontsize=9.0)
        else:
            ax.set_ylabel("")

        if idx == 1:
            ax.set_xlabel(r"$\Delta t_{\mathrm{max}}$ (days)", fontsize=9.0, labelpad=4)
        else:
            ax.set_xlabel("")

        ax.tick_params(axis="x", labelsize=7)
        ax.tick_params(axis="y", labelsize=7, labelrotation=0)

    if title_override:
        fig.suptitle(title_override, fontsize=10.0, fontweight="bold", y=0.98)

    fig.tight_layout()
    fig.subplots_adjust(wspace=0.22)

    out = out or (regime_dirs["full"].parent / default_fname)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


def floor_min(val: float, default_vmin: float) -> float:
    return min(val, default_vmin)


def main():
    parser = argparse.ArgumentParser(description="Plot 3-panel ER metric heatmaps across sampling regimes.")
    parser.add_argument("--full", type=Path, default=RUNS_DIR / "sampling_sweep" / "full" / "results.csv",
                        help="Path to results.csv or summary.json for Full Dataset.")
    parser.add_argument("--n30", type=Path, default=RUNS_DIR / "sampling_sweep" / "n30" / "results.csv",
                        help="Path to results.csv or summary.json for Window N=30d.")
    parser.add_argument("--n60", type=Path, default=RUNS_DIR / "sampling_sweep" / "n60" / "results.csv",
                        help="Path to results.csv or summary.json for Window N=60d.")
    parser.add_argument("--metric", required=True, choices=list(_METRICS.keys()),
                        help="Metric to plot (e.g. bcubed_f1, mean_bcubed_precision, mean_bcubed_recall, bcubed_f05).")
    parser.add_argument("--recompute", action="store_true",
                        help="Rerun evaluation algorithm from raw DB instead of reading cached results.")
    parser.add_argument("--title", type=str, default=None,
                        help="Override main figure title.")
    parser.add_argument("--cmap", type=str, default="YlGnBu",
                        help="Colormap palette (default: YlGnBu. Try: viridis, YlGn, crest, magma).")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output file path (.pdf or .png).")
    args = parser.parse_args()

    regime_dirs = {
        "full": args.full,
        "n30":  args.n30,
        "n60":  args.n60,
    }

    out = plot_all_sampling(
        regime_dirs=regime_dirs,
        metric=args.metric,
        recompute=args.recompute,
        out=args.out,
        title_override=args.title,
        cmap=args.cmap,
    )
    print(f"Saved figure: {out}")


if __name__ == "__main__":
    main()

