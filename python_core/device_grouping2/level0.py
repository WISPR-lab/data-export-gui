from db_session import DatabaseSession
import pandas as pd

"""
LEVEL 0 - deduplicate identical rows from events


For events, we consider rows with identical values in (attributes, timestamp, upload_id) as duplicates. 
We keep one and link the others to it via edges. This is useful for services like Discord that
have device IDs alongside almost every event, but many are the same.
"""


def level0(conn: DatabaseSession, upload_id: str) -> pd.DataFrame:
    edges_query = '''
        INSERT OR IGNORE INTO edges (id_a, id_b, type)
        WITH RankedEvents AS (
            SELECT 
                id, 
                MIN(id) OVER(PARTITION BY attributes, timestamp, upload_id) as id_a 
            FROM events
            WHERE treat_as_auth_device = 1
            AND upload_id = ?
        )
        SELECT 
            id_a, 
            id AS id_b, 
            'Deduplication' AS type
        FROM RankedEvents
        WHERE id != id_a;
    '''
    conn.execute(edges_query, (upload_id,))
    conn.commit()

    dedup_query = '''
        WITH RankedEvents AS (
            SELECT 
                id, 
                MIN(id) OVER(PARTITION BY attributes, timestamp, upload_id) as id_a 
            FROM events
            WHERE treat_as_auth_device = 1
            AND upload_id = ?
        )
        SELECT id, timestamp, upload_id, attributes, origin
        FROM events
        WHERE id IN (SELECT id_a FROM RankedEvents);
    '''
    dedup_events_df = pd.DataFrame(
        conn.execute(dedup_query, (upload_id,)).fetchall()
    )

    return dedup_events_df