import uuid
import json
import builtins
from db_session import DatabaseSession


def log_merge_event(profile_id: str, action: str, atomic_ids: list, 
                    user_initiated: bool = False, 
                    system_reason: str = None, 
                    user_reason: str = None) -> str:
    # log a merge/unmerge operation
    db_path = builtins.DB_PATH
    event_id = str(uuid.uuid4())
    
    with DatabaseSession(db_path) as conn:
        conn.execute(
            '''INSERT INTO soft_merge_history
               (id, action, profile_id, atomic_ids_added_or_removed, 
                user_initiated, system_reason, user_reason)
               VALUES (:id, :action, :profile_id, :atomic_ids, 
                       :user_initiated, :system_reason, :user_reason)''',
            {
                'id': event_id,
                'action': action,
                'profile_id': profile_id,
                'atomic_ids': json.dumps(atomic_ids),
                'user_initiated': user_initiated,
                'system_reason': system_reason,
                'user_reason': user_reason,
            }
        )
        conn.commit()
    
    return event_id
