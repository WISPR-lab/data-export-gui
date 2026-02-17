import sqlite3
import os
import logging
import json


def convert_json(val):
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        # Fallback if data is corrupted or not valid JSON
        return val 
    
sqlite3.register_converter("JSON", convert_json)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_config_value(name, default):
    """Get config value from builtins (injected by JS) or use default."""
    try:
        import builtins
        return getattr(builtins, name, default)
    except (ImportError, AttributeError):
        return default


class DatabaseSession:
    # synchronous context manager for SQLite
    def __init__(self, db_path=None, schema_path=None, use_dict_factory=False):
        # Use injected globals if available, otherwise use defaults
        self.db_path = db_path or get_config_value('DB_PATH', '/mnt/data/timeline.db')
        self.schema_path = schema_path or get_config_value('SCHEMA_PATH', '/python_core/database/schema.sql')
        self.use_dict_factory = use_dict_factory
        self.conn = None
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        try:
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            detect_val = sqlite3.PARSE_DECLTYPES if self.use_dict_factory else 0
            
            self.conn = sqlite3.connect(self.db_path, detect_types=detect_val)

            if self.use_dict_factory:
                self.conn.row_factory = dict_factory
            # else: defaults to tuple, used in worker bc more efficient


            self.conn.execute('PRAGMA journal_mode=WAL; ')
            self.conn.execute('PRAGMA foreign_keys = ON;')
            
            if self.schema_path:
                if not os.path.exists(self.schema_path):
                    raise FileNotFoundError(f"Schema file not found at: {self.schema_path}")
                
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    self.conn.executescript(f.read())
                
                self.conn.commit()
                
            return self.conn

        except Exception as e:
            if self.conn:
                self.conn.close()
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
