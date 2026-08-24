"""
evaluation/efficiency/batch_augment.py

Runs augmentation across multiple platforms and multipliers in one command.
Input:  evaluation/efficiency/data/<platform>_original.zip
Output: evaluation/efficiency/data/<platform>_<N>x.zip
        evaluation/efficiency/data/augment_summary.csv

Usage:
    uv run python -m evaluation.efficiency.batch_augment
"""

import csv
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.efficiency.augment import augment_zip, _fmt

DATA_DIR = REPO_ROOT / "evaluation" / "efficiency" / "data"
PLATFORMS = ["facebook", "google"]
MULTIPLIERS = [10, 100, 1000]

CSV_HEADER = [
    "platform", "multiplier",
    "source_zip_bytes", "output_zip_bytes",
    "whitelisted_bytes_original", "whitelisted_bytes_augmented",
    "total_bytes_augmented",
]


def main():
    rows = []

    for platform in PLATFORMS:
        src_zip = DATA_DIR / f"{platform}_original.zip"
        if not src_zip.exists():
            print(f"Skipping {platform}: {src_zip} does not exist.")
            continue

        for m in MULTIPLIERS:
            dst_zip = DATA_DIR / f"{platform}_{m}x.zip"
            print(f"Augmenting {platform} x{m} ...")
            wl_in, wl_out, total_out, zip_sz = augment_zip(str(src_zip), str(dst_zip), platform, m)
            print(f"  -> Written {dst_zip.name} ({_fmt(zip_sz)})")
            rows.append([
                platform, m,
                os.path.getsize(src_zip), zip_sz,
                wl_in, wl_out, total_out,
            ])

    summary_csv = DATA_DIR / "augment_summary.csv"
    with open(summary_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)
    print(f"\nWritten: {summary_csv}")


if __name__ == "__main__":
    main()
