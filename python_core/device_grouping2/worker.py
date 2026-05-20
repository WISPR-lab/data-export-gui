import pandas as pd
import json

from db_session import DatabaseSession
from level0 import level0 # deduplicate identical rows from events
from level1 import level1 # group on static IDs



def _get_config_value(name):
    import builtins
    if not hasattr(builtins, name):
        raise ValueError(f"Config value '{name}' not found in builtins.")
    return getattr(builtins, name)


def group(upload_id: str, db_path: str = None) -> None:
    db_path = db_path or _get_config_value('DB_PATH')
    
    json_columns = ['attributes', 'origins', 'upload_ids', 'file_ids', 'devices_raw_ids', 'atomic_devices_ids', 'tags', 'labels']
    with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_columns) as conn:
        
        # LEVEL 0
        dedup_events_df = level0(conn, upload_id)
        devices_df = pd.DataFrame(
            conn.execute(
            ''' SELECT id, upload_id, attributes, origin 
                FROM devices_raw
                WHERE upload_id = ?''', (upload_id,)
            ).fetchall()
        )
        df = _format_initial(dedup_events_df, devices_df)
    





def _format_initial(dedup_events_df, devices_df):
    dedup_events_df['table'] = 'events'
    dedup_events_df['timestamp'] = pd.to_datetime(dedup_events_df['timestamp'], errors='coerce')
    devices_df['table'] = 'devices_raw'
    df = pd.concat([devices_df, dedup_events_df], ignore_index=True)
    parsed_json = df['attributes'].apply(lambda x: json.loads(x) if pd.notna(x) else {})
    return df.drop(columns=['attributes']).join(
        pd.json_normalize(parsed_json).add_prefix('attr__')
    )
