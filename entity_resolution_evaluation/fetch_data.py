import os
import json
import urllib.request
import pandas as pd
from pathlib import Path
import logging
import subprocess
import sqlite3
import zipfile
import argparse

FP_STALKER_URL_1 = "https://raw.githubusercontent.com/Spirals-Team/FPStalker/master/datasets/extension1.txt.tar.gz"
FP_STALKER_URL_2 = "https://raw.githubusercontent.com/Spirals-Team/FPStalker/master/datasets/extension2.txt.tar.gz"
RBA_URL = "https://zenodo.org/records/6782156/files/rba-dataset.zip?download=1"


RAW_DATA_DIR = Path(__file__).resolve().parent / "data" / "raw"
NORMALIZED_DATA_DIR = Path(__file__).resolve().parent / "data" / "normalized"
RBA_DB = RAW_DATA_DIR / "rba.db"
FP_STALKER_DB = RAW_DATA_DIR / "fp_stalker.db"

RBA_CHUNKSIZE = 20000  # number of rows per pandas chunk
RBA_DELETE_ZIP_AFTER_IMPORT = True  # delete the downloaded zip after a successful import


def _detect_available_ram_gb():
    # ponytail: cgroup/sysconf detection is a heuristic that may not reflect swap or dynamic limits.
    # Upgrade path: use psutil or resource module if robust system monitoring is needed.
    try:
        limit_file = Path("/sys/fs/cgroup/memory.max")
        if limit_file.exists():
            val = limit_file.read_text().strip()
            if val != "max":
                return float(val) / (1024 ** 3)
    except Exception:
        pass
    try:
        limit_file = Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")
        if limit_file.exists():
            val = int(limit_file.read_text().strip())
            if val < 10**15:
                return float(val) / (1024 ** 3)
    except Exception:
        pass
    try:
        return (os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')) / (1024 ** 3)
    except Exception:
        pass
    return None


def _chunksize_for_ram(ram_gb):
    """picks a safe pandas chunksize from available RAM (GB) in container"""
    if ram_gb is None:
        return RBA_CHUNKSIZE
    if ram_gb < 4:
        return 5000
    if ram_gb < 8:
        return 10000
    if ram_gb < 12:
        return 25000
    if ram_gb < 16:
        return 50000
    return 100000



def initialize_dirs():
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    NORMALIZED_DATA_DIR.mkdir(parents=True, exist_ok=True)


def download_with_resume(url, dest, retries, error_msg):
    dest = Path(dest)
    if dest.exists():
        return True
    for attempt in range(retries):
        try:
            urllib.request.urlretrieve(url, dest)
            return True
        except Exception as e:
            if attempt == retries - 1:
                logging.error(error_msg, retries, e, url, dest)
            elif dest.exists():
                dest.unlink()
    return False


def fetch_data(retries=3, ram_gb=None):
    if ram_gb is None:
        ram_gb = _detect_available_ram_gb()
        if ram_gb:
            print(f"Auto-detected {ram_gb:.2f} GB of available memory.")
        else:
            print("Could not auto-detect available memory, using default chunk size.")

    initialize_dirs()

    # RBA fetch
    rba_path = RAW_DATA_DIR / "rba-dataset.zip"
    if not download_with_resume(
        RBA_URL, 
        rba_path, 
        retries,
        "Could not download RBA dataset after %d attempts: %s. \n Download data directly from %s, place in %s, and rerun script."
    ):
        return
    
    # RBA CSV to SQLite (stream from ZIP in chunks; do NOT extract full CSV to disk)
    if not RBA_DB.exists() and rba_path.exists():
        conn = sqlite3.connect(RBA_DB)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            chunksize = _chunksize_for_ram(ram_gb)  # choose dynamically based on available RAM
            print(f"Importing RBA dataset using chunksize {chunksize}...")

            with zipfile.ZipFile(rba_path) as z:
                for name in z.namelist():
                    if name.endswith("rba-dataset.csv"):
                        with z.open(name) as f:
                            for i, chunk in enumerate(pd.read_csv(f, chunksize=chunksize)):
                                chunk.to_sql('rba_data', conn, if_exists='append' if i > 0 else 'replace', index=False)
                        break
        finally:
            conn.close()

        # remove the downloaded archive to avoid holding both ZIP and DB on disk
        if RBA_DELETE_ZIP_AFTER_IMPORT:
            try:
                rba_path.unlink()
            except Exception:
                pass

    # FP Stalker fetch
    fp_stalker_path_1 = RAW_DATA_DIR / "extension1.txt.tar.gz"
    fp_stalker_path_2 = RAW_DATA_DIR / "extension2.txt.tar.gz"
    
    if not download_with_resume(
        FP_STALKER_URL_1,
        fp_stalker_path_1,
        retries,
        "Could not download FP Stalker after %d attempts: %s. \n Download data directly from %s, place in %s, and rerun script."
    ):
        return
    
    if not download_with_resume(
        FP_STALKER_URL_2,
        fp_stalker_path_2,
        retries,
        "Could not download FP Stalker after %d attempts: %s. \n Download data directly from %s, place in %s, and rerun script."
    ):
        return

    # FP Stalker extract and load to SQLite
    fp_stalker_sql = RAW_DATA_DIR / "tableFingerprints.sql"
    if not fp_stalker_sql.exists():
        with fp_stalker_sql.open("wb") as out_f:
            subprocess.run(["tar", "-xOzf", str(fp_stalker_path_1)], stdout=out_f, check=True)
            subprocess.run(["tar", "-xOzf", str(fp_stalker_path_2)], stdout=out_f, check=True)
    
    if not FP_STALKER_DB.exists():
        conn = sqlite3.connect(FP_STALKER_DB)
        with open(fp_stalker_sql) as f:
            conn.executescript(f.read())
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and materialize evaluation datasets")
    parser.add_argument("--rba-memory-gb", "--ram", "--ram-gb", dest="rba_memory_gb", type=float, default=None, help="Available memory in GB to tune RBA chunksize (alias: --ram)")
    args = parser.parse_args()
    fetch_data(ram_gb=args.rba_memory_gb)




