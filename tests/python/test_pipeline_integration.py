import pytest
import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
import builtins

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'python_core'))

from db_session import DatabaseSession
try:
    from conftest import init_db
except ImportError:
    # Fallback if conftest isn't in path or named differently
    def init_db(db_path):
        import sqlite3
        repo_root = Path(__file__).parent.parent.parent
        schema_path = repo_root / 'schema.sql'
        with DatabaseSession(db_path, schema_path=str(schema_path)) as conn:
            pass

from extractors.worker import extract
from semantic_map.worker import map as semantic_map
from field_normalization.worker import normalize
from device_grouping.worker import group as device_group


@pytest.fixture(scope="module")
def test_db_path():
    """Create temp test database for the entire module."""
    tmpdir = tempfile.mkdtemp(prefix='test_pipeline_')
    db_path = os.path.join(tmpdir, 'test.db')
    
    init_db(db_path)
    
    yield db_path
    
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)


@pytest.fixture(autouse=True)
def inject_db_config(test_db_path):
    """Inject test DB path into builtins for config access."""
    original_db_path = getattr(builtins, 'DB_PATH', None)
    builtins.DB_PATH = test_db_path
    
    yield
    
    if original_db_path:
        builtins.DB_PATH = original_db_path
    elif hasattr(builtins, 'DB_PATH'):
        delattr(builtins, 'DB_PATH')


class TestPipelineIntegration:
    """Test full extraction → semantic_map → field_normalization → device_grouping pipeline."""
    
    @staticmethod
    def _insert_raw_data(db_path, upload_id, platform, manifest_file_id):
        """Helper: insert test raw_data rows."""
        with DatabaseSession(db_path) as conn:
            conn.execute(
                'INSERT INTO uploads (id, platform, given_name) VALUES (?, ?, ?)',
                (upload_id, platform, f'test-{platform}')
            )
            conn.execute(
                'INSERT INTO uploaded_files (id, upload_id, path, manifest_file_id) VALUES (?, ?, ?, ?)',
                (str(1), upload_id, 'test.json', manifest_file_id)
            )
            conn.execute(
                'INSERT INTO raw_data (id, upload_id, file_id, data) VALUES (?, ?, ?, ?)',
                (str(1), upload_id, str(1), '{"test": "data"}')
            )
            conn.commit()
    
    @staticmethod
    def _insert_semantic_map_auth_devices(db_path, upload_id, count=3):
        """Helper: insert test auth_devices_initial rows (simulating semantic_map output)."""
        with DatabaseSession(db_path) as conn:
            # We need an entry in uploads, uploaded_files, and raw_data to satisfy FKs
            conn.execute(
                'INSERT OR IGNORE INTO uploads (id, platform, given_name) VALUES (?, ?, ?)',
                (upload_id, 'facebook', f'test-{upload_id}')
            )
            for i in range(count):
                file_id = f"file_{upload_id}_{i}"
                raw_data_id = f"raw_{upload_id}_{i}"
                auth_id = f"auth_{upload_id}_{i}"
                
                conn.execute(
                    'INSERT OR IGNORE INTO uploaded_files (id, upload_id, path) VALUES (?, ?, ?)',
                    (file_id, upload_id, f'test_{i}.json')
                )
                conn.execute(
                    'INSERT OR IGNORE INTO raw_data (id, upload_id, file_id, data) VALUES (?, ?, ?, ?)',
                    (raw_data_id, upload_id, file_id, '{}')
                )
                
                attrs = {
                    'user_agent_original': f'Mozilla/5.0 (iPhone; CPU iPhone OS 14_{i} like Mac OS X)',
                    'device_model_name': f'iPhone 12' if i < 2 else f'iPad Pro',
                    'device_manufacturer': 'Apple',
                    'user_agent_os_type': 'iOS' if i < 2 else 'iPadOS',
                }
                conn.execute(
                    'INSERT INTO auth_devices_initial (id, upload_id, file_id, raw_data_id, attributes) VALUES (?, ?, ?, ?, ?)',
                    (auth_id, upload_id, file_id, raw_data_id, json.dumps(attrs))
                )
            conn.commit()
    
    def test_field_normalization_standalone(self, test_db_path):
        """Test field_normalization worker independently."""
        upload_id = 'test-field-norm-001'
        self._insert_semantic_map_auth_devices(test_db_path, upload_id, count=2)
        
        result = normalize(upload_id, db_path=test_db_path)
        
        assert result['status'] == 'success'
        assert result['records_normalized'] == 2
        assert result['unique_uas_parsed'] == 2
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            rows = conn.execute(
                'SELECT id, attributes FROM auth_devices_initial WHERE upload_id = ?',
                (upload_id,)
            ).fetchall()
            
            for row in rows:
                attrs = json.loads(row['attributes'])
                assert 'user_agent_os_type' in attrs or 'user_agent_os_type' in attrs
    
    def test_device_grouping_hard_merge(self, test_db_path):
        """Test device_grouping hard merge (PASS 1)."""
        upload_id = 'test-hard-merge-001'
        
        with DatabaseSession(test_db_path) as conn:
            conn.execute(
                'INSERT INTO uploads (id, platform, given_name) VALUES (?, ?, ?)',
                (upload_id, 'test', 'test-upload')
            )
            
            for i in range(2):
                attrs = {
                    'device_imei': '123456789012345' if i == 0 else '123456789012345',
                    'device_model_name': f'iPhone {i}',
                }
                conn.execute(
                    'INSERT INTO auth_devices_initial (id, upload_id, file_id, attributes) VALUES (?, ?, ?, ?)',
                    (str(i), upload_id, str(i), json.dumps(attrs))
                )
            conn.commit()
        
        device_group(upload_id, db_path=test_db_path)
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            auth_devices = conn.execute(
                'SELECT id FROM auth_devices WHERE EXISTS (SELECT 1 FROM auth_devices_initial WHERE upload_id = ?)',
                (upload_id,)
            ).fetchall()
            
            assert len(auth_devices) >= 1
    
    def test_device_grouping_soft_merge(self, test_db_path):
        """Test device_grouping soft merge (PASS 2)."""
        upload_id = 'test-soft-merge-001'
        self._insert_semantic_map_auth_devices(test_db_path, upload_id, count=3)
        
        device_group(upload_id, db_path=test_db_path)
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            device_groups = conn.execute(
                'SELECT id, auth_devices_ids, initial_soft_merge FROM device_groups'
            ).fetchall()
            
            assert len(device_groups) > 0
            
            for dg in device_groups:
                ids_list = json.loads(dg['auth_devices_ids'])
                assert isinstance(ids_list, list)
                assert len(ids_list) >= 1
    
    def test_full_pipeline_end_to_end(self, test_db_path):
        """Test complete pipeline: insert auth_devices → normalize → group."""
        upload_id = 'test-e2e-001'
        self._insert_semantic_map_auth_devices(test_db_path, upload_id, count=4)
        
        norm_result = normalize(upload_id, db_path=test_db_path)
        assert norm_result['status'] == 'success'
        assert norm_result['records_normalized'] == 4
        
        device_group(upload_id, db_path=test_db_path)
        
        with DatabaseSession(test_db_path, use_dict_factory=True) as conn:
            device_groups = conn.execute(
                'SELECT COUNT(*) as count FROM device_groups'
            ).fetchone()
            
            assert device_groups['count'] > 0
