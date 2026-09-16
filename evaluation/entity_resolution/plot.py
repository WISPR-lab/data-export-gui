"""
Plot BCubed metric heatmaps from a sweep run directory.

Usage:
    uv run python -m evaluation.entity_resolution.plot <run_dir>
    uv run python -m evaluation.entity_resolution.plot <run_dir> --metric mean_bcubed_recall
    uv run python -m evaluation.entity_resolution.plot <run_dir> --vmin 0.7
"""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


_METRICS = {
    "mean_bcubed_precision": ("B\u00b3 Precision", "precision.png", 0.8),
    "mean_bcubed_recall":    ("B\u00b3 Recall",    "recall.png",    0.2),
    "bcubed_f1":             ("B\u00b3 F1",         "f1.png",        0.4),
    "bcubed_f05":            ("B\u00b3 F0.5",       "f05.png",       0.6),
}


def plot(run_dir: Path, metric: str, vmin: float = None, out: Path = None) -> Path:
    label, default_fname, default_vmin = _METRICS.get(metric, (metric, f"{metric}.png", 0.5))
    vmin = vmin if vmin is not None else default_vmin

    results = pd.read_csv(run_dir / "results.csv")
    with open(run_dir / "summary.json") as f:
        summary = json.load(f)

    pivot = results.pivot(index="k", columns="max_days_client", values=metric)
    pivot = pivot.sort_index(ascending=False)
    pivot.index.name = "Devices (K)"
    pivot.columns.name = "Max Gap (days)"

    actual_min = pivot.min().min()
    if actual_min < vmin:
        print(f"[WARNING] {metric}: data min {actual_min:.3f} is below vmin {vmin:.3f} — gradient will clip.")

    run = summary["run"]
    window_days = run.get("window_days", [None])[0]
    n_trials = run["n_trials"]
    seed = run["seed"]
    subtitle = f"n_trials={n_trials}  seed={seed}  window_days={window_days}"

    fig, ax = plt.subplots(figsize=(2.7, 2.7))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="Greens",
        annot=True,
        fmt=".2f",
        linewidths=0.5,
        linecolor="white",
        square=True,
        vmin=vmin,
        vmax=1.0,
        cbar=False,
        annot_kws={"size": 7},
    )
    ax.set_title(label, fontsize=9, fontweight="bold", pad=6)
    ax.set_xlabel(r"$\Delta t_{\mathrm{max}}$ (days between records)", fontsize=8)
    ax.set_ylabel("K (tracking IDs sampled)", fontsize=8)
    ax.tick_params(labelsize=7)
    fig.tight_layout()

    out = out or run_dir / default_fname
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_all(run_dir: Path, vmin: float = None) -> list:
    return [plot(run_dir, metric=m, vmin=vmin) for m in _METRICS]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--metric", default=None,
                        help="Single metric to plot. Omit to plot all.")
    parser.add_argument("--vmin", type=float, default=None,
                        help="Override default vmin for gradient (warns if data goes below).")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output path. Only valid with --metric.")
    args = parser.parse_args()

    if args.metric:
        out = plot(args.run_dir, metric=args.metric, vmin=args.vmin, out=args.out)
        print(f"Saved: {out}")
    else:
        for out in plot_all(args.run_dir, vmin=args.vmin):
            print(f"Saved: {out}")


if __name__ == "__main__":
    main()
