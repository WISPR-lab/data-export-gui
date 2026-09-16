import csv
import glob
import os
import statistics
from collections import defaultdict

TRIALS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trials")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

SIZES = ["original", "10x", "100x", "1000x"]
STAGES = ["extract", "semantic_map", "normalize", "group"]


def load():
    # (platform, size, stage) -> list of duration_ms / wasm_heap_after_bytes across trials
    dur = defaultdict(list)
    mem = defaultdict(list)
    # (platform, size) -> list of total_duration_ms across trials (one value per trial)
    total_dur = defaultdict(list)

    for f in glob.glob(os.path.join(TRIALS_DIR, "*.csv")):
        name = os.path.basename(f).replace(".csv", "")
        parts = name.split("_mem_perf")[0].split("_")
        platform, size = parts[0], "_".join(parts[1:])

        with open(f) as fh:
            rows = list(csv.DictReader(fh))

        for row in rows:
            stage = row["stage"]
            if stage == "after_pyodide_load":
                continue
            if row["duration_ms"]:
                dur[(platform, size, stage)].append(float(row["duration_ms"]))
            if row["wasm_heap_after_bytes"]:
                mem[(platform, size, stage)].append(float(row["wasm_heap_after_bytes"]))

        if rows:
            total_dur[(platform, size)].append(float(rows[-1]["total_duration_ms"]))

    return dur, mem, total_dur


def mean_std(values):
    if not values:
        return None, None
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return mean, std


def write_by_stage(dur, mem, out_path):
    rows = []
    for platform in ["facebook", "google"]:
        for size in SIZES:
            for stage in STAGES:
                t_mean, t_std = mean_std(dur.get((platform, size, stage), []))
                m_mean, m_std = mean_std(mem.get((platform, size, stage), []))
                if t_mean is None:
                    continue
                rows.append({
                    "platform": platform,
                    "size": size,
                    "stage": stage,
                    "time_s_mean": round(t_mean / 1000, 3),
                    "time_s_std": round(t_std / 1000, 3),
                    "peak_mem_mb_mean": round(m_mean / 1e6, 2) if m_mean is not None else "",
                    "peak_mem_mb_std": round(m_std / 1e6, 2) if m_std is not None else "",
                    "n_trials": len(dur[(platform, size, stage)]),
                })

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote", out_path)


def write_by_export(dur, mem, total_dur, out_path):
    # "peak memory" for the whole export = the group stage's peak (last stage, highest watermark)
    rows = []
    for platform in ["facebook", "google"]:
        for size in SIZES:
            t_mean, t_std = mean_std(total_dur.get((platform, size), []))
            m_mean, m_std = mean_std(mem.get((platform, size, "group"), []))
            if t_mean is None:
                continue
            rows.append({
                "platform": platform,
                "size": size,
                "time_s_mean": round(t_mean / 1000, 3),
                "time_s_std": round(t_std / 1000, 3),
                "peak_mem_mb_mean": round(m_mean / 1e6, 2) if m_mean is not None else "",
                "peak_mem_mb_std": round(m_std / 1e6, 2) if m_std is not None else "",
                "n_trials": len(total_dur[(platform, size)]),
            })

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote", out_path)


if __name__ == "__main__":
    dur, mem, total_dur = load()
    write_by_stage(dur, mem, os.path.join(OUT_DIR, "stats_by_stage.csv"))
    write_by_export(dur, mem, total_dur, os.path.join(OUT_DIR, "stats_by_export.csv"))
