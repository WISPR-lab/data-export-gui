import json
from db_session import DatabaseSession
from field_normalization.user_agent import UserAgentParser
from field_normalization.device import normalize_device_fields
from field_normalization.geo import normalize_geo_fields
from field_normalization.origin import determine_origin


def normalize(upload_id: str, db_path: str = None) -> dict:
    def _get_config_value(name):
        import builtins
        if not hasattr(builtins, name):
            raise ValueError(f"Config value '{name}' not found in builtins.")
        return getattr(builtins, name)
    
    db_path = db_path or _get_config_value('DB_PATH')
    
    with DatabaseSession(db_path, use_dict_factory=True) as conn:
        print(f"[FieldNormalizeWorker] Starting normalization for upload_id={upload_id}")
        
        # Get platform from uploads table
        upload = conn.execute(
            "SELECT platform FROM uploads WHERE id = ?",
            (upload_id,)
        ).fetchone()
        platform = upload['platform'] if upload else None
        
        rows = conn.execute(
            """
            SELECT id, attributes
            FROM devices_raw
            WHERE upload_id = ?
            """,
            (upload_id,)
        ).fetchall()
        
        if not rows:
            print(f"[FieldNormalizeWorker] No devices_raw rows for upload_id={upload_id}")
            return {'status': 'success', 'message': 'No records to normalize'}
        
        ua_parser = UserAgentParser()
        updates = []
        
        for row in rows:
            attrs = json.loads(row['attributes'] or '{}')
            attrs.update(ua_parser.parse(attrs))
            
            attrs = normalize_device_fields(attrs)
            attrs = normalize_geo_fields(attrs)
            
            origin = determine_origin(platform, attrs)
            
            updates.append({
                'id': row['id'],
                'attributes': json.dumps(attrs),
                'origin': origin,
            })
        
        conn.executemany(
            """
            UPDATE devices_raw
            SET attributes = :attributes, origin = :origin
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
