import json
from db_session import DatabaseSession
from field_normalization.user_agent import UserAgentParser
from field_normalization.device import normalize_device_fields
from field_normalization.geo import normalize_geo_fields


def normalize(upload_id: str, db_path: str = None) -> dict:
    def _get_config_value(name):
        import builtins
        if not hasattr(builtins, name):
            raise ValueError(f"Config value '{name}' not found in builtins.")
        return getattr(builtins, name)
    
    db_path = db_path or _get_config_value('DB_PATH')
    
    with DatabaseSession(db_path, use_dict_factory=True) as conn:
        print(f"[FieldNormalizeWorker] Starting normalization for upload_id={upload_id}")
        rows = conn.execute(
            """
            SELECT id, attributes
            FROM auth_devices_initial
            WHERE upload_id = ?
            """,
            (upload_id,)
        ).fetchall()
        
        if not rows:
            print(f"[FieldNormalizeWorker] No auth_devices_initial rows for upload_id={upload_id}")
            return {'status': 'success', 'message': 'No records to normalize'}
        
        ua_parser = UserAgentParser()
        updates = []
        
        for row in rows:
            attrs = json.loads(row['attributes'] or '{}')
            attrs.update(ua_parser.parse(attrs))
            
            attrs = normalize_device_fields(attrs)
            attrs = normalize_geo_fields(attrs)
            
            updates.append({
                'id': row['id'],
                'attributes': json.dumps(attrs),
            })
        
        conn.executemany(
            """
            UPDATE auth_devices_initial
            SET attributes = :attributes
            WHERE id = :id
            """,
            updates
        )
        conn.commit()
        print(f"[FieldNormalizationWorker] Normalization Complete")
        
        print(f"[normalize] Normalized {len(updates)} records")
        return {
            'status': 'success',
            'message': f'Normalized {len(updates)} records',
            'records_normalized': len(updates),
            'unique_uas_parsed': len(ua_parser._cache),
        }
