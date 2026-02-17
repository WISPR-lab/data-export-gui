import time
import sqlite3

def add_event_comment(event_id: int, comment_text: str, db_path) -> int:
    now_ms = time.time() * 1000
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        sql = """
            INSERT INTO event_comments (event_id, comment, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """
        cursor.execute(sql, (event_id, comment_text, now_ms, now_ms))
        conn.commit()
        
        return cursor.lastrowid 

def update_event_comment(comment_id: int, new_text: str, db_path) -> int:
    now_ms = time.time() * 1000
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        sql = """
            UPDATE event_comments 
            SET comment = ?, updated_at = ? 
            WHERE id = ?
        """
        cursor.execute(sql, (new_text, now_ms, comment_id))
        conn.commit()
        return cursor.rowcount

def delete_event_comment(comment_id: int, db_path) -> int:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        sql = "DELETE FROM event_comments WHERE id = ?"
        cursor.execute(sql, (comment_id,))
        conn.commit()
        return cursor.rowcount