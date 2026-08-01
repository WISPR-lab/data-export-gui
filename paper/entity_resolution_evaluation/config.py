from pathlib import Path

# Base directories
EVAL_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = EVAL_DIR / "data" / "raw"
NORMALIZED_DATA_DIR = EVAL_DIR / "data" / "normalized"

# Database paths
RBA_DB = RAW_DATA_DIR / "rba.duckdb"
FP_STALKER_DB = RAW_DATA_DIR / "fp_stalker.duckdb"
FP_STALKER_TMP_SQL = RAW_DATA_DIR / "fp_stalker.tmp.sql"
FP_STALKER_TMP_SQLITE = RAW_DATA_DIR / "fp_stalker.tmp.sqlite"

# URLs
FP_STALKER_URL_1 = "https://raw.githubusercontent.com/Spirals-Team/FPStalker/master/extension1.txt.tar.gz"
FP_STALKER_URL_2 = "https://raw.githubusercontent.com/Spirals-Team/FPStalker/master/extension2.txt.tar.gz"
RBA_URL = "https://zenodo.org/records/6782156/files/rba-dataset.zip?download=1"

# Settings
DEFAULT_TABLE_NAME = "imported_data"
RBA_DELETE_ZIP_AFTER_IMPORT = False  # delete the downloaded zip after a successful import
