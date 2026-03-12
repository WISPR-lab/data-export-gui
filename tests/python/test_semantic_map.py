import pytest
import json
import os
import builtins
from semantic_map.worker import map as semantic_map


class TestSemanticMap:
    """Test semantic_map.worker.map() on real facebook.zip data."""

    def test_map_extracts_auth_devices_from_facebook_zip(self, sample_upload_with_raw_data, test_db_path):
        """Verify that semantic mapping populates auth_devices_initial table."""
        upload_id, raw_data_count = sample_upload_with_raw_data
        
        assert raw_data_count > 0, "Sample data fixture should load at least one raw_data row"
        
        semantic_map(
            platform='facebook',
            upload_id=upload_id,
            db_path=test_db_path,
            manifest_dir=builtins.MANIFESTS_DIR
        )
        
        from db_session import DatabaseSession
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            auth_devices = conn.execute(
                'SELECT COUNT(*) as count FROM auth_devices_initial WHERE upload_id = ?',
                (upload_id,)
            ).fetchone()
            
            assert auth_devices['count'] > 0, f"Expected auth_devices_initial rows, got {auth_devices['count']}"
    
    def test_map_populates_attributes_field(self, sample_upload_with_raw_data, test_db_path):
        """Verify that auth_devices_initial has non-empty attributes."""
        upload_id, _ = sample_upload_with_raw_data
        
        semantic_map(
            platform='facebook',
            upload_id=upload_id,
            db_path=test_db_path,
            manifest_dir=builtins.MANIFESTS_DIR
        )
        
        from db_session import DatabaseSession
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            rows = conn.execute(
                'SELECT id, attributes FROM auth_devices_initial WHERE upload_id = ?',
                (upload_id,)
            ).fetchall()
            
            assert len(rows) > 0, "Should extract at least one auth device"
            
            for row in rows:
                attrs = json.loads(row['attributes'] or '{}')
                assert isinstance(attrs, dict), f"Attributes should be dict, got {type(attrs)}"
                assert len(attrs) > 0, f"Row {row['id']} has empty attributes"
