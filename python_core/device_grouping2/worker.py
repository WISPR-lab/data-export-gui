import pandas as pd
import json

from db_session import DatabaseSession
from .level0 import level0 # deduplicate identical rows from events
from .level1 import level1 # group on static IDs
from .level2 import level2 # group on UA/OS upgrades
from .level3 import level3 # group on class-level device models


def _get_config_value(name):
    import builtins
    if not hasattr(builtins, name):
        raise ValueError(f"Config value '{name}' not found in builtins.")
    return getattr(builtins, name)


def group(upload_id: str, db_path: str = None) -> None:
    db_path = db_path or _get_config_value('DB_PATH')
    
    json_columns = ['attributes', 'origins', 'upload_ids', 'file_ids', 'devices_raw_ids', 'atomic_devices_ids', 'tags', 'labels']
    with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_columns) as conn:
        
        # 1. Intra-upload Event Deduplication (Level 0)
        dedup_events_df = level0(conn, upload_id)
        devices_df = pd.DataFrame(
            conn.execute(
                '''SELECT id, upload_id, attributes, origin 
                   FROM devices_raw
                   WHERE upload_id = ?''', (upload_id,)
            ).fetchall()
        )
        df = _format_initial(dedup_events_df, devices_df)
        
        # 2. Compute and insert Level 1 and Level 2 edges
        level1_edges = level1(df)
        conn.executemany(
            'INSERT OR IGNORE INTO edges (id_a, id_b, type) VALUES (?, ?, ?)',
            level1_edges[['id_a', 'id_b', 'type']].values.tolist()
        )
        
        level2_edges = level2(df)
        conn.executemany(
            'INSERT OR IGNORE INTO edges (id_a, id_b, type) VALUES (?, ?, ?)',
            level2_edges[['id_a', 'id_b', 'type']].values.tolist()
        )

        conn.commit()

        # 3. Compute and insert Level 3 (Device Profiles / Class-Level merges) edges
        level3_edges = level3(conn, upload_id)
        conn.executemany(
            'INSERT OR IGNORE INTO edges (id_a, id_b, type) VALUES (?, ?, ?)',
            level3_edges[['id_a', 'id_b', 'type']].values.tolist()
        )

        conn.commit()


def _format_initial(dedup_events_df, devices_df):
    if dedup_events_df.empty:
        dedup_events_df = pd.DataFrame(columns=['id', 'upload_id', 'attributes', 'origin', 'timestamp'])
    dedup_events_df['table'] = 'events'
    dedup_events_df['timestamp'] = pd.to_datetime(dedup_events_df['timestamp'], errors='coerce')
    
    if devices_df.empty:
        devices_df = pd.DataFrame(columns=['id', 'upload_id', 'attributes', 'origin'])
    devices_df['table'] = 'devices_raw'
    
    df = pd.concat([devices_df, dedup_events_df], ignore_index=True)
    if df.empty:
        return pd.DataFrame(columns=['id', 'upload_id', 'origin', 'table'])
        
    parsed_json = df['attributes'].apply(lambda x: json.loads(x) if (isinstance(x, str) and x) else (x if isinstance(x, dict) else {}))
    return df.drop(columns=['attributes']).join(
        pd.json_normalize(parsed_json).add_prefix('attr__')
    )
