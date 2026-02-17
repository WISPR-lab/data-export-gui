import sqlite3
import json
from python_core.database.db_session import DatabaseSession
from .events_where_builder import build_search_conditions
from typing import List, Set, Union


def get_config_value(name, default):
    """Get config value from builtins (injected by JS) or use default."""
    try:
        import builtins
        return getattr(builtins, name, default)
    except (ImportError, AttributeError):
        return default


def search_events(query_string: str, filter_obj: dict, db_path=None):

    db_path = db_path or get_config_value('DB_PATH', '/mnt/data/timeline.db')

    where_clause, params = build_search_conditions(query_string, filter_obj)
    
    limit = filter_obj.get('size', 40)
    offset = filter_obj.get('from', 0)
    
    order = filter_obj.get('order', 'desc').upper()
    if order not in ['ASC', 'DESC']: order = 'DESC'


    with DatabaseSession(db_path, use_dict_factory=True) as conn:
        results = {
            "objects": _event_get_objects(conn, where_clause, params, limit, offset, order),
            "meta": {
                "total_count": _events_get_total_count(conn, where_clause, params), # for pagination
                "count_per_timeline": _events_get_count_per_timeline(conn, where_clause, params),  # for coloring Timelines in UI
            }
        }
    return results


def delete_events(event_ids: List[Union[int, str]] | Union[int, str], # accepts single id or list of ids
                  db_path=None):    
    if isinstance(event_ids, (int, str)):
        event_ids = [event_ids]
    
    db_path = db_path or get_config_value('DB_PATH', '/mnt/data/timeline.db')
    
    try:
        event_ids = [int(eid) for eid in event_ids]  # ensure all ids are strings for SQL query
    except ValueError:
        raise ValueError(f"events:delete_events --> All event_ids must be integers or strings, was {event_ids}.")

    with DatabaseSession(db_path) as conn:
        placeholders = ','.join(['?'] * len(event_ids))
        sql_delete = f"DELETE FROM events WHERE id IN ({placeholders})"
        conn.execute(sql_delete, event_ids)
        conn.commit()


def get_event_count(db_path=None):
    db_path = db_path or get_config_value('DB_PATH', '/mnt/data/timeline.db')
    with DatabaseSession(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM events")
        return cursor.fetchone()[0]


# --- search helpers, use conn -- #

def _events_get_total_count(conn: sqlite3.Connection, where_clause: str, params: list):
    # for pagination
    sql_count = f"SELECT COUNT(*) as count FROM events e {where_clause}"
    cursor = conn.execute(sql_count, params)
    total_count = cursor.fetchone()['count']
    return total_count


def _events_get_count_per_timeline(conn: sqlite3.Connection, where_clause: str, params: list):
    # for coloring Timelines in UI
    sql_timeline = f"""
        SELECT e.upload_id, COUNT(*) as count 
        FROM events e 
        {where_clause} 
        GROUP BY e.upload_id
    """
    cursor = conn.execute(sql_timeline, params)
    count_per_timeline = {row['upload_id']: row['count'] for row in cursor.fetchall()}
    return count_per_timeline



def _event_get_objects(conn: sqlite3.Connection,
                       where_clause: str, 
                       params: list, 
                       limit: int, 
                       offset: int, 
                       order: str):
    
    objects = []
    
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    
    sql_events = f"""
        SELECT 
            e.id, e.upload_id, e.timestamp, e.message, e.attributes, e.tags, e.labels,
            e.event_category, e.event_action, e.event_kind,
            f.opfs_filename as source_file, u.given_name as timeline_name, u.platform
        FROM events e
        LEFT JOIN uploaded_files f ON json_extract(e.file_ids, '$[0]') = f.id
        LEFT JOIN uploads u ON e.upload_id = u.id
        {where_clause}
        ORDER BY e.timestamp {order}
        LIMIT ? OFFSET ?
    """
    cursor = conn.execute(sql_events, params + [limit, offset])
    rows = cursor.fetchall()

    # format rows into Elastic-style "objects"
    for r in rows:
        # parse JSON fields if they are strings (depends on your db_session factory)
        attrs = json.loads(r['attributes']) if isinstance(r['attributes'], str) else (r['attributes'] or {})
        tags = json.loads(r['tags']) if isinstance(r['tags'], str) else (r['tags'] or [])
        labels = json.loads(r['labels']) if isinstance(r['labels'], str) else (r['labels'] or [])
        event_category = json.loads(r['event_category']) if isinstance(r['event_category'], str) else (r['event_category'] or [])
        
        # Flatten: attributes go into _source, but system fields override them
        source = {
            **attrs,  # Unpack attributes first
            "primary_timestamp": r['timestamp'], # UI expects this specific key often
            "timestamp": r['timestamp'],
            "message": r['message'],
            "category": event_category,
            "event_action": r['event_action'],
            "event_kind": r['event_kind'],
            "tags": tags,
            "labels": labels,
            "timeline_name": r['timeline_name'],
            "timeline_id": r['upload_id'],
            "platform": r['platform'],
            "filename": r['source_file']
        }

        objects.append({
            "_id": str(r['id']),
            "_index": r['upload_id'],
            "_source": source
        })
    return objects
