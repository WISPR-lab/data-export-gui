import csv
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

sns.set_theme(style="whitegrid", context="paper")

COL_WIDTH_IN = 3.375
FIG_HEIGHT_IN = 1.75
BASE_PT = 8.0
SMALL_PT = 7.0

plt.rcParams.update({
    "font.size": BASE_PT,
    "axes.labelsize": BASE_PT,
    "legend.fontsize": SMALL_PT,
    "xtick.labelsize": SMALL_PT,
    "ytick.labelsize": SMALL_PT,
    "axes.linewidth": 0.7,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "legend.frameon": False,
    "grid.linewidth": 0.5,
    "axes.spines.bottom": True,
    "xtick.bottom": True,
    "xtick.direction": "out",
    "xtick.major.size": 4,
    "xtick.major.pad": 2,
    "pdf.fonttype": 42,
})

CATEGORIES = ["Unprompted", "Prompted", "Not Used", "N/A"]
CAT_COLOR = {
    "Unprompted": "#414487",
    "Prompted":   "#21918c",
    "Not Used":   "#fde725",
    "N/A":        "#d9d9d9",
}
CAT_TEXT = {
    "Unprompted": "white",
    "Prompted":   "white",
    "Not Used":   "#1a1a1a",
    "N/A":        "#4d4d4d",
}

CHART_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_CSV = os.path.join(CHART_DIR, "feature_use.csv")


def load_data(path=DATA_CSV):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            feature = row.pop("feature")
            values = [v.strip() for v in row.values() if v and v.strip()]
            unknown = set(values) - set(CATEGORIES)
            if unknown:
                raise ValueError("unknown value(s) %s in row %r" % (sorted(unknown), feature))
            counts = {c: values.count(c) for c in CATEGORIES}
            rows.append((feature, counts, len(values)))
    return rows


def feature_use(rows):
    fig, ax = plt.subplots()

    labels = [textwrap.fill(f, 20) for f, _, _ in rows]
    y = list(range(len(rows)))[::-1]
    n = max(total for _, _, total in rows)

    for yi, (_, counts, _) in zip(y, rows):
        left = 0.0
        for cat in CATEGORIES:
            v = counts[cat]
            if v == 0:
                continue
            ax.barh(yi, v, left=left, height=0.62, color=CAT_COLOR[cat],
                    edgecolor="white", linewidth=1.0, zorder=3)
            ax.text(left + v / 2, yi, str(v), ha="center", va="center",
                    fontsize=SMALL_PT, color=CAT_TEXT[cat], zorder=4)
            left += v

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, n)
    ax.set_xticks(range(0, n + 1, max(1, n // 5)))
    ax.set_xlabel("participants (n = %d)" % n)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", zorder=0)
    ax.set_axisbelow(True)

    handles = [mpatches.Patch(facecolor=CAT_COLOR[c], label=c) for c in CATEGORIES]

    fig.set_size_inches(COL_WIDTH_IN, FIG_HEIGHT_IN)
    fig.tight_layout(pad=0.2, rect=(0, 0.11, 1, 1))
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.02),
               ncol=4, columnspacing=0.9, handlelength=1.0, handletextpad=0.4,
               borderpad=0.0)
    out = os.path.join(CHART_DIR, "feature_use.%s" % "pdf")
    fig.savefig(out, dpi=400)
    print("saved", out)
    plt.close(fig)


if __name__ == "__main__":
    feature_use(load_data())
