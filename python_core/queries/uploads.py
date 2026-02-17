import sqlite3
from python_core.database.db_session import DatabaseSession


def get_config_value(name, default):
    """Get config value from builtins (injected by JS) or use default."""
    try:
        import builtins
        return getattr(builtins, name, default)
    except (ImportError, AttributeError):
        return default


def get_uploads(db_path=None):
    # Returns all rows from the uploads table as a list of dictionaries
    db_path = db_path or get_config_value('DB_PATH', '/mnt/data/timeline.db')
    with DatabaseSession(db_path, use_dict_factory=True) as conn:
        cursor = conn.execute("SELECT * FROM uploads")
        return cursor.fetchall()
