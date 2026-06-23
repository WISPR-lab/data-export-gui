import os
import json
import urllib.request
import pandas as pd
from pathlib import Path
import logging
import subprocess
import sqlite3
import zipfile
import tarfile
import argparse
import shutil
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

FP_STALKER_URL_1 = "https://raw.githubusercontent.com/Spirals-Team/FPStalker/master/extension1.txt.tar.gz"
FP_STALKER_URL_2 = "https://raw.githubusercontent.com/Spirals-Team/FPStalker/master/extension2.txt.tar.gz"
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


def _format_size_gb_mb(path):
    size = path.stat().st_size
    return f"{size / (1024 ** 3):.2f} GB ({size / (1024 ** 2):.1f} MB)"


class DownloadProgress:
    def __init__(self, name):
        self.name = name
        self.pbar = None

    def __call__(self, count, block_size, total_size):
        if total_size <= 0:
            return
        if self.pbar is None:
            self.pbar = tqdm(total=total_size, unit="B", unit_scale=True, desc=self.name)
        downloaded = min(count * block_size, total_size)
        self.pbar.n = downloaded
        self.pbar.refresh()
        if downloaded >= total_size:
            self.pbar.close()


def initialize_dirs():
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    NORMALIZED_DATA_DIR.mkdir(parents=True, exist_ok=True)


def hard_refresh():
    for path in (RAW_DATA_DIR, NORMALIZED_DATA_DIR):
        if path.exists():
            for child in path.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()


def download_with_resume(url, dest, retries, error_msg):
    logging.info("Downloading %s to %s...", url, dest)
    dest = Path(dest)
    if dest.exists() and (zipfile.is_zipfile(dest) or tarfile.is_tarfile(dest)):
        return True
    tmp_dest = dest.with_name(dest.name + ".part")

    for attempt in range(retries):
        try:
            urllib.request.urlretrieve(url, tmp_dest, reporthook=DownloadProgress(dest.name))
            tmp_dest.replace(dest)
            logging.info("Download completed successfully.")
            return True
        except Exception as e:
            if attempt == retries - 1:
                logging.error(error_msg, retries, e, url, dest)
            else:
                logging.warning("Attempt %d failed: %s. Retrying...", attempt + 1, e)
            if tmp_dest.exists():
                tmp_dest.unlink()
    return False


def fetch_data(retries=3, chunksize=None):
    if chunksize is None:
        ram_gb = _detect_available_ram_gb()
        if ram_gb:
            logging.info("Auto-detected %.2f GB of available memory.", ram_gb)
        else:
            logging.info("Could not auto-detect available memory, using default chunk size.")
        chunksize = _chunksize_for_ram(ram_gb)

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
    if (not RBA_DB.exists() or RBA_DB.stat().st_size == 0) and rba_path.exists():
        conn = sqlite3.connect(RBA_DB)
        rba_rows = 0
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            logging.info("Importing RBA dataset using chunksize %d...", chunksize)

            with zipfile.ZipFile(rba_path) as z:
                for name in z.namelist():
                    if name.endswith("rba-dataset.csv"):
                        with z.open(name) as f:
                            for i, chunk in enumerate(tqdm(pd.read_csv(f, chunksize=chunksize), desc="RBA import", unit="chunk")):
                                rba_rows += len(chunk)
                                chunk.to_sql('rba_data', conn, if_exists='append' if i > 0 else 'replace', index=False)
                        break
        finally:
            conn.close()


        logging.info("RBA import done: %d records, %s", rba_rows, _format_size_gb_mb(RBA_DB))

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
        try:
            with fp_stalker_sql.open("wb") as out_f:
                for tar_path in tqdm([fp_stalker_path_1, fp_stalker_path_2], desc="FP Stalker extract", unit="archive"):
                    subprocess.run(["tar", "-xOzf", str(tar_path)], stdout=out_f, check=True)
        except Exception as e:
            logging.error("Error extracting FP Stalker SQL: %s", e)
            return
    if not FP_STALKER_DB.exists() or FP_STALKER_DB.stat().st_size == 0:
        try:
            conn = sqlite3.connect(FP_STALKER_DB)
            with open(fp_stalker_sql) as f:
                sql = "\n".join(
                    line for line in f.read().splitlines()
                    if not line.lstrip().startswith(("SET ", "DELIMITER ", "LOCK TABLES", "UNLOCK TABLES", "USE "))
                )
                sql = sql.replace("COLLATE utf8_unicode_ci", "")
                conn.executescript(sql)
        finally:
            conn.close()


    logging.info(
        "Done. %s = %s; %s = %s",
        RBA_DB.name,
        _format_size_gb_mb(RBA_DB),
        FP_STALKER_DB.name,
        _format_size_gb_mb(FP_STALKER_DB),
    )

    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and materialize evaluation datasets")
    parser.add_argument("--chunksize", "--chunk-size", "-c", dest="chunksize", type=int, default=None, help="Pandas chunk size (number of rows to load at a time)")
    parser.add_argument("--hard-refresh", action="store_true", help="Delete generated evaluation data before fetching")
    args = parser.parse_args()
    if args.hard_refresh:
        hard_refresh()
    fetch_data(chunksize=args.chunksize)




