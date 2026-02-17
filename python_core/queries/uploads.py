import sqlite3
from python_core import cfg
from python_core.database.db_session import DatabaseSession

def get_uploads(db_path=cfg.DB_PATH):
    # Returns all rows from the upload table as a list of dictionaries
    with DatabaseSession(db_path, use_dict_factory=True) as conn:
        cursor = conn.execute("SELECT * FROM upload")
        return cursor.fetchall()
