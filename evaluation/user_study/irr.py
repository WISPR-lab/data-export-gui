"""

script for computing IRR from csv file of codes from 2 coders. 
original coded transcripts not included in this artifact to protect participant privacy.

CSV must be formatted with the following columns (case-sensitive):
- "Participant" (e.g., pN)
- "Row Number" (integer)
- "Coder 1 - Feature Use"  (string with code, separated by commas if multiple)
- "Coder 2 - Feature Use"  ^ 
- "Coder 1 - Prompted"  (string with code, no multi-label)
- "Coder 2 - Prompted"   ^ 
- "Coder 1 - Reaction"   ^
- "Coder 2 - Reaction"   ^              
"""

import json
import pandas as pd
from nltk.metrics import AnnotationTask
from nltk.metrics.distance import binary_distance, masi_distance

ROUND_DIGITS = 4


# whether each code category allows multi-labels (comma-separated)
CODE_CATEGORIES_MULTILABEL = {
    "Feature Use": True,  # calculated via masi distance
    "Prompted": False,
    "Reaction": False,
}

REQUIRED_COLUMNS = [
    "Participant",
    "Row Number",
    *(f"Coder 1 - {field}" for field in CODE_CATEGORIES_MULTILABEL),
    *(f"Coder 2 - {field}" for field in CODE_CATEGORIES_MULTILABEL),
]


def safe_masi_distance(set1: frozenset, set2: frozenset) -> float:
    if not set1 and not set2:
        return 0.0
    if not set1 or not set2:
        return 1.0
    return masi_distance(set1, set2)


def _parse_label(val, is_multilabel: bool):
    s = "" if pd.isna(val) else str(val).strip()
    if is_multilabel:
        return frozenset(x.strip() for x in s.split(",") if x.strip())
    return s if s else "NOCODE"  # placeholder for missing codes


def calculate_krippendorff(df: pd.DataFrame, active_only: bool = False) -> str:
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        print(f"Missing required columns: {sorted(missing)}")
        return None

    clean_ids = df["Participant"].dropna().astype(str).str.strip()
    slices = {"overall_pooled": df} | {
        f"{p}_only": df[clean_ids == p] for p in clean_ids.unique() if p
    }

    results = {}
    for slice_name, slice_df in slices.items():
        results[slice_name] = {}

        item_ids = [
            f"{str(p).strip() if pd.notna(p) and str(p).strip() else 'row'}_{r if pd.notna(r) else idx}"
            for idx, (p, r) in enumerate(
                zip(slice_df["Participant"], slice_df["Row Number"])
            )
        ]

        for field, is_multi in CODE_CATEGORIES_MULTILABEL.items():
            v1 = [_parse_label(v, is_multi) for v in slice_df[f"Coder 1 - {field}"]]
            v2 = [_parse_label(v, is_multi) for v in slice_df[f"Coder 2 - {field}"]]

            empty_val = frozenset() if is_multi else "NOCODE"
            task_data = []
            for item_id, a, b in zip(item_ids, v1, v2):
                if active_only and a == empty_val and b == empty_val:
                    continue
                task_data.append(("coder1", item_id, a))
                task_data.append(("coder2", item_id, b))

            dist_fn = safe_masi_distance if is_multi else binary_distance
            task = AnnotationTask(data=task_data, distance=dist_fn)

            try:
                score = round(task.alpha(), ROUND_DIGITS)
            except ZeroDivisionError:
                score = "undefined"

            metric_label = "multilabel --> MASI" if is_multi else "single label"
            results[slice_name][field] = {
                "metric": f"krippendorff_alpha ({metric_label})",
                "score": score,
            }

    return json.dumps(results, indent=2)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="compute krippendorff's alpha from csv."
    )
    parser.add_argument(
        "csv_path",
        type=str,
        help="path to the csv file with codes, see top of file for format",
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="filter out rows where both coders left the field blank",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.csv_path)
    print(calculate_krippendorff(df, active_only=args.active_only))