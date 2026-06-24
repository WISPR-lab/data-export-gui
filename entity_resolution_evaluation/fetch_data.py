import urllib.request
import re
from pathlib import Path
import logging
import zipfile
import tarfile
import argparse
import shutil
from tqdm import tqdm
import sqlite3
import duckdb
import sqlglot

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

EXPECTED_FP_STALKER_ROWS = 15000  
EXPECTED_RBA_ROWS = 31269264

try:
    import entity_resolution_evaluation.config as cf
except ImportError:
    import config as cf


def _format_size_gb_mb(path):
    if not path.exists():
        return "N/A"
    size = path.stat().st_size
    return f"{size / (1024 ** 3):.2f} GB ({size / (1024 ** 2):.1f} MB)"


def _download_progress(name):
    pbar = None

    def hook(count, block_size, total_size):
        nonlocal pbar
        if total_size <= 0:
            return
        if pbar is None:
            pbar = tqdm(total=total_size, unit="B", unit_scale=True, desc=name)
        downloaded = min(count * block_size, total_size)
        pbar.n = downloaded
        pbar.refresh()
        if downloaded >= total_size:
            pbar.close()

    return hook


def initialize_dirs():
    cf.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    cf.NORMALIZED_DATA_DIR.mkdir(parents=True, exist_ok=True)


def db_properly_initialized(db_path, expected_rows=None, table_name=cf.DEFAULT_TABLE_NAME):
    db_path = Path(db_path)
    if not db_path.exists() or db_path.stat().st_size == 0:
        return False
    try:
        with duckdb.connect(str(db_path)) as conn:
            rows = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            res = rows == expected_rows if expected_rows is not None else rows > 0
            if not res:
                return False
            logging.info("%s is already properly initialized with %d records (%s).", db_path, expected_rows, _format_size_gb_mb(db_path))
            return True
    except Exception:
        return False


def hard_refresh():
    try:
        response = input("WARNING: This will delete all downloaded and processed evaluation data. Proceed? [y/N]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        response = "n"
    if response not in ("y", "yes"):
        logging.info("Aborting hard refresh.")
        import sys
        sys.exit(0)

    for path in (cf.RAW_DATA_DIR, cf.NORMALIZED_DATA_DIR):
        if path.exists():
            for child in path.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()


def refresh_db():
    try:
        response = input("WARNING: This will delete existing database files (rba.duckdb, fp_stalker.duckdb). Proceed? [y/N]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        response = "n"
    if response not in ("y", "yes"):
        logging.info("Aborting database refresh.")
        import sys
        sys.exit(0)

    for db_path in (cf.RBA_DB, cf.FP_STALKER_DB):
        db_path.unlink(missing_ok=True)


def download_with_resume(url, dest, retries, error_msg):
    logging.info("Downloading %s to %s...", url, dest)
    dest = Path(dest)
    if dest.exists() and (zipfile.is_zipfile(dest) or tarfile.is_tarfile(dest)):
        logging.info("%s already exists, skipping download.", dest.name)
        return True
    tmp_dest = dest.with_name(dest.name + ".part")

    for attempt in range(retries):
        try:
            urllib.request.urlretrieve(url, tmp_dest, reporthook=_download_progress(dest.name))
            tmp_dest.replace(dest)
            logging.info("Download completed successfully.")
            return True
        except Exception as e:
            if attempt == retries - 1:
                logging.error(error_msg, retries, e, url, dest)
            else:
                logging.warning("Attempt %d failed: %s. Retrying...", attempt + 1, e)
            tmp_dest.unlink(missing_ok=True)
    return False


def mysql_to_sqlite(mysql_sql):
    expressions = sqlglot.parse(mysql_sql, read="mysql")
    cleaned = [
        expr for expr in expressions
        if isinstance(expr, (sqlglot.exp.Create, sqlglot.exp.Insert))
    ]
    sql = ";\n".join(expr.sql(dialect="sqlite") for expr in cleaned)
    
    # Strip MySQL-specific character set, charset, and collation keywords that SQLite rejects
    sql = re.sub(r'(?i)\bCHARACTER\s+SET\s+\w+', '', sql)
    sql = re.sub(r'(?i)\bDEFAULT\s+CHARSET\s*=\s*\w+', '', sql)
    sql = re.sub(r'(?i)\bCOLLATE\s+\w+', '', sql)
    
    return sql


def fetch_data(retries=3):
    initialize_dirs()

    # RBA dataset
    if not db_properly_initialized(cf.RBA_DB, EXPECTED_RBA_ROWS):
        rba_path = cf.RAW_DATA_DIR / "rba-dataset.zip"
        if not download_with_resume(
            cf.RBA_URL, 
            rba_path, 
            retries,
            "Could not download RBA dataset after %d attempts: %s. \n Download data directly from %s, place in %s, and rerun script."
        ):
            return
        
        extracted_csv = cf.RAW_DATA_DIR / "rba-dataset.csv"
        logging.info("Extracting RBA CSV from ZIP...")
        with zipfile.ZipFile(rba_path) as z:
            for name in z.namelist():
                if name.endswith("rba-dataset.csv"):
                    z.extract(name, path=cf.RAW_DATA_DIR)
                    break
        
        logging.info("Importing RBA dataset into DuckDB...")
        with duckdb.connect(str(cf.RBA_DB)) as conn:
            conn.execute(f"CREATE TABLE {cf.DEFAULT_TABLE_NAME} AS SELECT * FROM read_csv_auto('{extracted_csv}')")
            rba_rows = conn.execute(f"SELECT COUNT(*) FROM {cf.DEFAULT_TABLE_NAME}").fetchone()[0]
            logging.info("RBA database contains %d records, %s", rba_rows, _format_size_gb_mb(cf.RBA_DB))
        
        extracted_csv.unlink(missing_ok=True)
        if cf.RBA_DELETE_ZIP_AFTER_IMPORT:
            rba_path.unlink(missing_ok=True)

    # FP Stalker pipeline
    if not db_properly_initialized(cf.FP_STALKER_DB, expected_rows=EXPECTED_FP_STALKER_ROWS):
        fp_stalker_path_1 = cf.RAW_DATA_DIR / "extension1.txt.tar.gz"
        fp_stalker_path_2 = cf.RAW_DATA_DIR / "extension2.txt.tar.gz"
        
        if not download_with_resume(
            cf.FP_STALKER_URL_1,
            fp_stalker_path_1,
            retries,
            "Could not download FP Stalker after %d attempts: %s. \n Download data directly from %s, place in %s, and rerun script."
        ):
            return
        
        if not download_with_resume(
            cf.FP_STALKER_URL_2,
            fp_stalker_path_2,
            retries,
            "Could not download FP Stalker after %d attempts: %s. \n Download data directly from %s, place in %s, and rerun script."
        ):
            return
    
        cf.FP_STALKER_TMP_SQL.unlink(missing_ok=True)
        cf.FP_STALKER_TMP_SQLITE.unlink(missing_ok=True)
        cf.FP_STALKER_DB.unlink(missing_ok=True)

        logging.info("Extracting FP Stalker SQL...")
        try:
            with cf.FP_STALKER_TMP_SQL.open("wb") as out_f:
                for tar_path in [fp_stalker_path_1, fp_stalker_path_2]:
                    with tarfile.open(tar_path, "r:gz") as tar:
                        for member in tar.getmembers():
                            if member.isfile():
                                f = tar.extractfile(member)
                                if f:
                                    out_f.write(f.read())
        except Exception as e:
            logging.error("Failed to extract FP Stalker SQL: %s", e)
            return

        logging.info("Importing FP Stalker MySQL to SQLite...")
        try:
            with sqlite3.connect(cf.FP_STALKER_TMP_SQLITE) as conn_sqlite:
                with open(cf.FP_STALKER_TMP_SQL) as f:
                    mysql_sql = f.read()
                sql = mysql_to_sqlite(mysql_sql)
                conn_sqlite.executescript(sql)
                logging.info("FP Stalker SQLite database created at %s, %s", cf.FP_STALKER_TMP_SQLITE, _format_size_gb_mb(cf.FP_STALKER_TMP_SQLITE))
        except Exception as e:
            logging.error("Failed to import FP Stalker MySQL to SQLite: %s", e)
            return
        
        logging.info("Importing FP Stalker SQLite to DuckDB...")
        try:
            with duckdb.connect(str(cf.FP_STALKER_DB)) as conn_duck:
                conn_duck.execute("INSTALL sqlite;")
                conn_duck.execute("LOAD sqlite;")
                conn_duck.execute(f"CALL sqlite_attach('{cf.FP_STALKER_TMP_SQLITE}')")
                conn_duck.execute(f"CREATE TABLE {cf.DEFAULT_TABLE_NAME} AS SELECT * FROM temp_fp_stalker.extensionDataScheme")
                fp_stalker_rows = conn_duck.execute(f"SELECT COUNT(*) FROM {cf.DEFAULT_TABLE_NAME}").fetchone()[0]
                logging.info("FP Stalker database contains %d records, %s", fp_stalker_rows, _format_size_gb_mb(cf.FP_STALKER_DB))
        except Exception as e:
            logging.error("Failed to import FP Stalker SQLite to DuckDB: %s", e)
            return
        
        cf.FP_STALKER_TMP_SQL.unlink(missing_ok=True)
        cf.FP_STALKER_TMP_SQLITE.unlink(missing_ok=True)

    logging.info(
        "Done. %s = %s; %s = %s",
        cf.RBA_DB.name,
        _format_size_gb_mb(cf.RBA_DB),
        cf.FP_STALKER_DB.name,
        _format_size_gb_mb(cf.FP_STALKER_DB),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and materialize evaluation datasets")
    parser.add_argument("--hard-refresh", action="store_true", help="Delete generated evaluation data before fetching")
    parser.add_argument("--refresh-db", action="store_true", help="Delete existing database files before fetching")
    args = parser.parse_args()
    if args.hard_refresh:
        hard_refresh()
    elif args.refresh_db:
        refresh_db()
    fetch_data()
