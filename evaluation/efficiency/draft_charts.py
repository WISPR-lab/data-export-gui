import glob
import csv
import os
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", context="paper")

COL_WIDTH_IN = 3.3
plt.rcParams.update({
    "font.size": 9,
    "axes.labelsize": 9,
    "legend.fontsize": 7.5,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.linewidth": 0.7,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "legend.frameon": False,
    "grid.linewidth": 0.5,
    "axes.spines.bottom": True,
    "xtick.bottom": True,
    "xtick.direction": "out",
    "xtick.major.size": 5,
    "xtick.major.pad": 2,
})

LINEWIDTH = 1.3
PLATFORM_STYLE = {"facebook": "-", "google": "--"}
PLATFORM_MARKER = {"facebook": "o", "google": "s"}
SIZE_COLOR = {
    "1000x": F"#864fff",
    "100x": "#3dadff", 
    "10x": "#66d574", 
    "original": "#ffc942",
}

SIZES = ["original", "10x", "100x", "1000x"]
STAGES = ["extract", "semantic_map", "normalize", "group"]
X = ["start"] + STAGES

CHART_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")


def load_data():
    files = glob.glob("evaluation/efficiency/trials/*.csv")
    data = defaultdict(list)
    for f in files:
        name = f.split("/")[-1].replace(".csv", "")
        parts = name.split("_mem_perf")[0].split("_")
        platform = parts[0]
        size = "_".join(parts[1:])
        with open(f) as fh:
            for row in csv.DictReader(fh):
                stage = row["stage"]
                if stage == "after_pyodide_load":
                    continue
                if row["duration_ms"]:
                    data[(platform, size, stage)].append(float(row["duration_ms"]))
    return {k: statistics.mean(v) for k, v in data.items()}


def time_cumulative(means):
    fig, ax = plt.subplots()
    for platform in ["facebook", "google"]:
        for size in SIZES:
            cum = [0.0]
            total = 0.0
            for stage in STAGES:
                total += means.get((platform, size, stage), 0)
                cum.append(total)
            cum_s = [v / 1000 for v in cum]  # ms -> s
            ax.plot(X, cum_s, PLATFORM_STYLE[platform], color=SIZE_COLOR[size],
                     marker=PLATFORM_MARKER[platform], markersize=4,
                     linewidth=LINEWIDTH)
    ax.set_ylabel("cumulative time (s)")
    ax.tick_params(axis="x", rotation=20)

    size_handles = [plt.Line2D([0], [0], color=SIZE_COLOR[s], linewidth=LINEWIDTH, label=s) for s in SIZES]
    plat_handles = [plt.Line2D([0], [0], color="gray", linestyle=PLATFORM_STYLE[p],
                                marker=PLATFORM_MARKER[p], markersize=4, label=p)
                     for p in ["facebook", "google"]]
    leg1 = ax.legend(handles=size_handles, loc="upper left", title="size", title_fontsize=7.5)
    ax.add_artist(leg1)
    ax.legend(handles=plat_handles, loc="upper left", bbox_to_anchor=(0.33, 1.0))

    fig.set_size_inches(COL_WIDTH_IN, 2.6)
    fig.tight_layout(pad=0.3)
    os.makedirs(CHART_DIR, exist_ok=True)
    out = os.path.join(CHART_DIR, "time_cumulative.png")
    fig.savefig(out, dpi=400, bbox_inches="tight")
    plt.close(fig)
    print("saved", out)


if __name__ == "__main__":
    means = load_data()
    time_cumulative(means)
