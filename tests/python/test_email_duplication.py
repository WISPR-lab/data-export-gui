import pytest
import json
import builtins
from semantic_map.worker import map as semantic_map


def test_email_duplication(sample_upload_with_raw_data, test_db_path):
    """Verify that exactly 1 email_addition event is created from facebook test data."""
    upload_id, raw_data_count = sample_upload_with_raw_data
    
    print(f"\n[TEST] Starting with {raw_data_count} raw_data rows")
    
    semantic_map(
        platform='facebook',
        upload_id=upload_id,
        db_path=test_db_path,
        manifest_dir=builtins.MANIFESTS_DIR
    )
    
    from db_session import DatabaseSession
    
    with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
        # Count all events
        all_events = conn.execute(
            'SELECT COUNT(*) as count FROM events WHERE upload_id = ?',
            (upload_id,)
        ).fetchone()
        
        # Count email events
        email_events = conn.execute(
            'SELECT COUNT(*) as count FROM events WHERE upload_id = ? AND event_action = ?',
            (upload_id, 'email_addition')
        ).fetchone()
        
        print(f"\n[TEST] Total events: {all_events['count']}")
        print(f"[TEST] Email events: {email_events['count']}")
        
        # Assert exactly 1 email event
        assert email_events['count'] == 1, f"Expected 1 email_addition event, got {email_events['count']}"
        
        # Show email event details
        emails = conn.execute(
            'SELECT id, timestamp, event_action FROM events WHERE upload_id = ? AND event_action = ?',
            (upload_id, 'email_addition')
        ).fetchall()
        
        print(f"\n[TEST] Email event details:")
        for row in emails:
            print(f"  - id={row['id']}, ts={row['timestamp']}, action={row['event_action']}")
