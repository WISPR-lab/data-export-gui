import sqlite3
import os
import logging


class DatabaseSession:
    """
    Synchronous Context Manager for SQLite.
    Ensures connection is closed and schema is initialized.
    """
    def __init__(self, db_path, schema_path=None):
        self.db_path = db_path   # e.g. /mnt/data/forensics.db
        self.schema_path = schema_path  # e.g. database/schema.sql
        self.conn = None
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        try:
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            self.conn = sqlite3.connect(self.db_path)
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