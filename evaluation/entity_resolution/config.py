from pathlib import Path

# Base directories
EVAL_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = EVAL_DIR / "data" / "raw"
# URLs
FP_STALKER_URL_1 = "https://raw.githubusercontent.com/Spirals-Team/FPStalker/master/extension1.txt.tar.gz"
FP_STALKER_URL_2 = "https://raw.githubusercontent.com/Spirals-Team/FPStalker/master/extension2.txt.tar.gz"
EXPECTED_FP_STALKER_ROWS = 15000

# Database paths
FP_STALKER_DB = RAW_DATA_DIR / "fp_stalker.duckdb"
FP_STALKER_TMP_SQL = RAW_DATA_DIR / "fp_stalker.tmp.sql"
FP_STALKER_TMP_SQLITE = RAW_DATA_DIR / "fp_stalker.tmp.sqlite"
DB_TABLE = "imported_data"

# run settings

RUNS_DIR = EVAL_DIR / "runs"

K_OPTIONS = [2, 4, 6, 8, 10, 12]
MAX_DAYS_CLIENT_OPTIONS = [1, 7, 14, 30, 60, 90]
DEFAULT_N_TRIALS = 500
DEFAULT_SEED = 13
