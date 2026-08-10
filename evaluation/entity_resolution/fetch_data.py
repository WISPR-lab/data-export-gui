import urllib.request
import re
import tarfile
import sqlite3
import logging
import shutil
from pathlib import Path

import duckdb
import sqlglot
from tqdm import tqdm

try:
    import evaluation.entity_resolution.config as cf
except ImportError:
    import config as cf

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _db_ok():
    if not cf.FP_STALKER_DB.exists():
        return False
    if cf.FP_STALKER_DB.stat().st_size < 1024 * 100:
        return False
    try:
        with duckdb.connect(str(cf.FP_STALKER_DB)) as conn:
            rows = conn.execute(f"SELECT COUNT(*) FROM {cf.DB_TABLE}").fetchone()[0]
            return rows == cf.EXPECTED_FP_STALKER_ROWS
    except Exception:
        return False


def _download(url, dest, name):
    dest = Path(dest)
    if dest.exists() and tarfile.is_tarfile(dest):
        print(f"  {dest.name} already downloaded, skipping.")
        return
    tmp = dest.with_suffix(".part")
    pbar = None

    def _hook(count, block_size, total_size):
        nonlocal pbar
        if total_size <= 0:
            return
        if pbar is None:
            pbar = tqdm(total=total_size, unit="B", unit_scale=True, desc=name)
        pbar.n = min(count * block_size, total_size)
        pbar.refresh()
        if pbar.n >= total_size:
            pbar.close()

    print(f"  Downloading {url} ...")
    urllib.request.urlretrieve(url, tmp, reporthook=_hook)
    tmp.replace(dest)


def _mysql_to_sqlite(mysql_sql):
    expressions = sqlglot.parse(mysql_sql, read="mysql")
    cleaned = [e for e in expressions if isinstance(e, (sqlglot.exp.Create, sqlglot.exp.Insert))]
    sql = ";\n".join(e.sql(dialect="sqlite") for e in cleaned)
    sql = re.sub(r"(?i)\bCHARACTER\s+SET\s+\w+", "", sql)
    sql = re.sub(r"(?i)\bDEFAULT\s+CHARSET\s*=\s*\w+", "", sql)
    sql = re.sub(r"(?i)\bCOLLATE\s+\w+", "", sql)
    return sql


def fetch():
    if _db_ok():
        print(f"FP Stalker DB already present at {cf.FP_STALKER_DB} ({cf.EXPECTED_FP_STALKER_ROWS} rows). Nothing to do.")
        return

    try:
        answer = input(
            "\nThe FP Stalker dataset needs to be downloaded (~274 MB compressed).\n"
            "Download now? [y/N]: "
        ).strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        answer = "n"

    if answer not in ("y", "yes"):
        print("Download skipped. Cannot run evaluation without data.")
        raise SystemExit(1)

    cf.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    tar1 = cf.RAW_DATA_DIR / "extension1.txt.tar.gz"
    tar2 = cf.RAW_DATA_DIR / "extension2.txt.tar.gz"
    _download(cf.FP_STALKER_URL_1, tar1, "extension1")
    _download(cf.FP_STALKER_URL_2, tar2, "extension2")

    print("Extracting and merging SQL from tarballs...")
    cf.FP_STALKER_TMP_SQL.unlink(missing_ok=True)
    with cf.FP_STALKER_TMP_SQL.open("wb") as out:
        for tar_path in [tar1, tar2]:
            with tarfile.open(tar_path, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.isfile():
                        f = tar.extractfile(member)
                        if f:
                            out.write(f.read())

    print("Converting MySQL dump → SQLite...")
    cf.FP_STALKER_TMP_SQLITE.unlink(missing_ok=True)
    with open(cf.FP_STALKER_TMP_SQL) as f:
        sql = _mysql_to_sqlite(f.read())
    with sqlite3.connect(cf.FP_STALKER_TMP_SQLITE) as conn:
        conn.executescript(sql)

    print("Importing SQLite → DuckDB...")
    cf.FP_STALKER_DB.unlink(missing_ok=True)
    with duckdb.connect(str(cf.FP_STALKER_DB)) as conn:
        conn.execute("INSTALL sqlite;")
        conn.execute("LOAD sqlite;")
        conn.execute(f"CALL sqlite_attach('{cf.FP_STALKER_TMP_SQLITE}')")
        conn.execute(f"CREATE TABLE {cf.DB_TABLE} AS SELECT * FROM temp_fp_stalker.extensionDataScheme")
        rows = conn.execute(f"SELECT COUNT(*) FROM {cf.DB_TABLE}").fetchone()[0]
        print(f"FP Stalker DB created: {rows} rows at {cf.FP_STALKER_DB}")

    cf.FP_STALKER_TMP_SQL.unlink(missing_ok=True)
    cf.FP_STALKER_TMP_SQLITE.unlink(missing_ok=True)

    if not _db_ok():
        raise RuntimeError(f"DB validation failed after import (expected {cf.EXPECTED_FP_STALKER_ROWS} rows, got {rows}).")
    print("Data ready.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch and materialize the FP Stalker dataset")
    parser.add_argument("--hard-refresh", action="store_true", help="Delete all raw data and re-download")
    args = parser.parse_args()

    if args.hard_refresh:
        try:
            answer = input("WARNING: This will delete all downloaded evaluation data. Proceed? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            answer = "n"
        if answer in ("y", "yes"):
            shutil.rmtree(cf.RAW_DATA_DIR, ignore_errors=True)
            print("Cleared raw data directory.")
        else:
            raise SystemExit(0)

    fetch()
