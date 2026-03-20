import pytest
import uuid
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.append(repo_root)

python_core_path = os.path.join(repo_root, "python_core")
if python_core_path not in sys.path:
    sys.path.insert(0, python_core_path)

import builtins
from db_session import DatabaseSession
from user_merge.merge import merge_device_profiles
from user_merge.unmerge import unmerge_device_profiles
from device_grouping.computed_fields import merge_attrs, pick_most_specific


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        schema_path = os.path.join(repo_root, "schema.sql")
        
        # Initialize DB
        with DatabaseSession(db_path, schema_path=schema_path) as conn:
            pass
        
        # Set builtins for DatabaseSession to find
        builtins.DB_PATH = db_path
        builtins.SCHEMA_PATH = schema_path
        
        yield db_path
        
        del builtins.DB_PATH
        del builtins.SCHEMA_PATH


@pytest.fixture
def db_with_profiles(temp_db):
    """Create a database with sample atomic devices and device profiles."""
    json_cols = {'attributes', 'origins', 'tags', 'labels', 'atomic_devices_ids'}
    
    with DatabaseSession(temp_db, use_dict_factory=True, json_columns=json_cols) as conn:
        ts = datetime.now(timezone.utc).timestamp()
        
        # Create atomic devices
        atomic_ids = [str(uuid.uuid4()) for _ in range(4)]
        
        conn.execute(
            '''INSERT INTO atomic_devices 
               (id, attributes, origins, upload_ids, file_ids, devices_raw_ids, specificity)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (atomic_ids[0], json.dumps({'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}),
             json.dumps([{'origin': 'test_file.json', 'upload_id': 'upload1'}]),
             json.dumps(['upload1']), json.dumps(['file1']), json.dumps(['raw1']), 2)
        )
        
        conn.execute(
            '''INSERT INTO atomic_devices 
               (id, attributes, origins, upload_ids, file_ids, devices_raw_ids, specificity)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (atomic_ids[1], json.dumps({'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}),
             json.dumps([{'origin': 'test_file.json', 'upload_id': 'upload1'}]),
             json.dumps(['upload1']), json.dumps(['file1']), json.dumps(['raw2']), 2)
        )
        
        conn.execute(
            '''INSERT INTO atomic_devices 
               (id, attributes, origins, upload_ids, file_ids, devices_raw_ids, specificity)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (atomic_ids[2], json.dumps({'device_manufacturer': 'Apple', 'device_model_name': 'iPhone'}),
             json.dumps([{'origin': 'test_file.json', 'upload_id': 'upload1'}]),
             json.dumps(['upload1']), json.dumps(['file1']), json.dumps(['raw3']), 1)
        )
        
        conn.execute(
            '''INSERT INTO atomic_devices 
               (id, attributes, origins, upload_ids, file_ids, devices_raw_ids, specificity)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (atomic_ids[3], json.dumps({'device_manufacturer': 'Samsung', 'device_model_name': 'Galaxy S21'}),
             json.dumps([{'origin': 'test_file.json', 'upload_id': 'upload1'}]),
             json.dumps(['upload1']), json.dumps(['file1']), json.dumps(['raw4']), 2)
        )
        
        # Create device profiles
        profile_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        conn.execute(
            '''INSERT INTO device_profiles 
               (id, atomic_devices_ids, attributes, specificity, model, manufacturer, origins, 
                system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (profile_ids[0], json.dumps([atomic_ids[0], atomic_ids[1]]),
             json.dumps({'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}),
             2, 'iPhone 13', 'Apple', json.dumps([{'origin': 'merged', 'upload_id': 'upload1'}]),
             1, 0, None, None, '[]', '[]', ts, ts)
        )
        
        conn.execute(
            '''INSERT INTO device_profiles 
               (id, atomic_devices_ids, attributes, specificity, model, manufacturer, origins, 
                system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (profile_ids[1], json.dumps([atomic_ids[2]]),
             json.dumps({'device_manufacturer': 'Apple', 'device_model_name': 'iPhone'}),
             1, 'iPhone', 'Apple', json.dumps([{'origin': 'merged', 'upload_id': 'upload1'}]),
             0, 1, None, None, '[]', '[]', ts, ts)
        )
        
        conn.execute(
            '''INSERT INTO device_profiles 
               (id, atomic_devices_ids, attributes, specificity, model, manufacturer, origins, 
                system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (profile_ids[2], json.dumps([atomic_ids[3]]),
             json.dumps({'device_manufacturer': 'Samsung', 'device_model_name': 'Galaxy S21'}),
             2, 'Galaxy S21', 'Samsung', json.dumps([{'origin': 'merged', 'upload_id': 'upload1'}]),
             0, 0, None, None, '[]', '[]', ts, ts)
        )
        
        conn.commit()
    
    return temp_db, profile_ids, atomic_ids


class TestMergeDeviceProfiles:
    
    def test_merge_success(self, db_with_profiles):
        """Test successful merge of two profiles."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        src_id = profile_ids[2]  # Samsung
        tgt_id = profile_ids[0]  # iPhone 13
        
        result = merge_device_profiles(src_id, tgt_id)
        
        assert result['status'] == 'ok'
        assert result['merged_profile_id'] == tgt_id
        
        # Verify source profile is deleted
        json_cols = {'attributes', 'origins', 'tags', 'labels', 'atomic_devices_ids'}
        with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
            src = conn.execute('SELECT * FROM device_profiles WHERE id = ?', (src_id,)).fetchone()
            assert src is None
            
            # Verify target profile contains both atomics
            tgt = conn.execute('SELECT * FROM device_profiles WHERE id = ?', (tgt_id,)).fetchone()
            assert tgt is not None
            assert len(tgt['atomic_devices_ids']) == 3  # 2 original + 1 from src
    
    def test_merge_source_not_found(self, db_with_profiles):
        """Test merge with non-existent source profile."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        fake_id = str(uuid.uuid4())
        tgt_id = profile_ids[0]
        
        result = merge_device_profiles(fake_id, tgt_id)
        
        assert result['status'] == 'error'
        assert 'not found' in result['message'].lower()
    
    def test_merge_target_not_found(self, db_with_profiles):
        """Test merge with non-existent target profile."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        src_id = profile_ids[2]
        fake_id = str(uuid.uuid4())
        
        result = merge_device_profiles(src_id, fake_id)
        
        assert result['status'] == 'error'
        assert 'not found' in result['message'].lower()
    
    def test_merge_hard_merged_profiles_ineligible(self, db_with_profiles):
        """Test that two hard-merged profiles (both specificity >= 3) cannot be merged."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        
        # Create two hard-merged profiles
        json_cols = {'attributes', 'origins', 'tags', 'labels', 'atomic_devices_ids'}
        with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
            ts = datetime.now(timezone.utc).timestamp()
            hard_id1 = str(uuid.uuid4())
            hard_id2 = str(uuid.uuid4())
            
            conn.execute(
                '''INSERT INTO device_profiles 
                   (id, atomic_devices_ids, attributes, specificity, model, manufacturer, origins, 
                    system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (hard_id1, json.dumps([atomic_ids[0]]),
                 json.dumps({'device_id': '12345'}),
                 3, 'Model', 'Mfr', json.dumps([]),
                 0, 0, None, None, '[]', '[]', ts, ts)
            )
            
            conn.execute(
                '''INSERT INTO device_profiles 
                   (id, atomic_devices_ids, attributes, specificity, model, manufacturer, origins, 
                    system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (hard_id2, json.dumps([atomic_ids[1]]),
                 json.dumps({'device_id': '67890'}),
                 3, 'Model2', 'Mfr2', json.dumps([]),
                 0, 0, None, None, '[]', '[]', ts, ts)
            )
            conn.commit()
        
        result = merge_device_profiles(hard_id1, hard_id2)
        
        assert result['status'] == 'ineligible'
        assert 'deterministic' in result['message'].lower() or 'hard' in result['message'].lower()
    
    def test_merge_hard_merged_into_specific_allowed(self, db_with_profiles):
        """Test that hard-merged profile CAN be merged into specific profile."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        
        # Create a hard-merged profile
        json_cols = {'attributes', 'origins', 'tags', 'labels', 'atomic_devices_ids'}
        with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
            ts = datetime.now(timezone.utc).timestamp()
            hard_id = str(uuid.uuid4())
            
            conn.execute(
                '''INSERT INTO device_profiles 
                   (id, atomic_devices_ids, attributes, specificity, model, manufacturer, origins, 
                    system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (hard_id, json.dumps([atomic_ids[2]]),
                 json.dumps({'device_id': '12345'}),
                 3, 'Model', 'Mfr', json.dumps([]),
                 0, 0, None, None, '[]', '[]', ts, ts)
            )
            conn.commit()
        
        # Merge hard-merged into specific profile (not hard-merged)
        result = merge_device_profiles(hard_id, profile_ids[0])
        
        assert result['status'] == 'ok'
        assert result['merged_profile_id'] == profile_ids[0]
    
    def test_merge_two_generic_profiles_ineligible(self, db_with_profiles):
        """Test that two generic profiles cannot be merged."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        
        # Profile 1 is generic Apple (is_generic=1)
        generic_id = profile_ids[1]
        
        # Create another generic profile
        json_cols = {'attributes', 'origins', 'tags', 'labels', 'atomic_devices_ids'}
        with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
            ts = datetime.now(timezone.utc).timestamp()
            generic_id2 = str(uuid.uuid4())
            
            conn.execute(
                '''INSERT INTO device_profiles 
                   (id, atomic_devices_ids, attributes, specificity, model, manufacturer, origins, 
                    system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (generic_id2, json.dumps([atomic_ids[2]]),
                 json.dumps({'device_manufacturer': 'Apple', 'device_model_name': 'iPad'}),
                 1, 'iPad', 'Apple', json.dumps([]),
                 0, 1, None, None, '[]', '[]', ts, ts)
            )
            conn.commit()
        
        result = merge_device_profiles(generic_id, generic_id2)
        
        assert result['status'] == 'ineligible'
        assert 'generic' in result['message'].lower()

    def test_merge_generic_into_specific_preserves_specificity(self, db_with_profiles):
        """Test that merging generic 'iPhone' into 'iPhone XR' preserves 'iPhone XR' as the model."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        
        json_cols = {'attributes', 'origins', 'tags', 'labels', 'atomic_devices_ids'}
        
        # Create a generic iPhone atomic (just "iPhone")
        with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
            ts = datetime.now(timezone.utc).timestamp()
            generic_atomic_id = str(uuid.uuid4())
            
            conn.execute(
                '''INSERT INTO atomic_devices 
                   (id, attributes, origins, upload_ids, file_ids, devices_raw_ids, specificity)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (generic_atomic_id, json.dumps({'device_manufacturer': 'Apple', 'device_model_name': 'iPhone'}),
                 json.dumps([{'origin': 'test_file.json', 'upload_id': 'upload1'}]),
                 json.dumps(['upload1']), json.dumps(['file1']), json.dumps(['raw_generic']), 1)
            )
            
            # Create a specific iPhone XR atomic
            iphone_xr_atomic_id = str(uuid.uuid4())
            conn.execute(
                '''INSERT INTO atomic_devices 
                   (id, attributes, origins, upload_ids, file_ids, devices_raw_ids, specificity)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (iphone_xr_atomic_id, json.dumps({'device_manufacturer': 'Apple', 'device_model_name': 'iPhone XR'}),
                 json.dumps([{'origin': 'test_file.json', 'upload_id': 'upload2'}]),
                 json.dumps(['upload2']), json.dumps(['file2']), json.dumps(['raw_xr']), 2)
            )
            
            # Create a generic profile with just the generic iPhone atomic
            generic_profile_id = str(uuid.uuid4())
            conn.execute(
                '''INSERT INTO device_profiles 
                   (id, atomic_devices_ids, attributes, specificity, model, manufacturer, origins, 
                    system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (generic_profile_id, json.dumps([generic_atomic_id]),
                 json.dumps({'device_manufacturer': 'Apple', 'device_model_name': 'iPhone'}),
                 1, 'iPhone', 'Apple', json.dumps([{'origin': 'test_file.json', 'upload_id': 'upload1'}]),
                 0, 1, None, None, '[]', '[]', ts, ts)
            )
            
            # Create a specific profile with the iPhone XR atomic
            specific_profile_id = str(uuid.uuid4())
            conn.execute(
                '''INSERT INTO device_profiles 
                   (id, atomic_devices_ids, attributes, specificity, model, manufacturer, origins, 
                    system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (specific_profile_id, json.dumps([iphone_xr_atomic_id]),
                 json.dumps({'device_manufacturer': 'Apple', 'device_model_name': 'iPhone XR'}),
                 2, 'iPhone XR', 'Apple', json.dumps([{'origin': 'test_file.json', 'upload_id': 'upload2'}]),
                 0, 0, None, None, '[]', '[]', ts, ts)
            )
            conn.commit()
        
        # Merge generic iPhone into specific iPhone XR
        result = merge_device_profiles(generic_profile_id, specific_profile_id)
        
        assert result['status'] == 'ok'
        
        # Verify the merged profile has "iPhone XR" as the model, not "iPhone"
        with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
            merged = conn.execute('SELECT * FROM device_profiles WHERE id = ?', (specific_profile_id,)).fetchone()
            assert merged is not None
            assert merged['model'] == 'iPhone XR', f"Expected model to be 'iPhone XR', got '{merged['model']}'"
            assert len(merged['atomic_devices_ids']) == 2
            # Verify both atomics are present
            assert generic_atomic_id in merged['atomic_devices_ids']
            assert iphone_xr_atomic_id in merged['atomic_devices_ids']


class TestUnmergeDeviceProfiles:
    
    def test_unmerge_success(self, db_with_profiles):
        """Test successful unmerge of a profile."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        profile_id = profile_ids[0]  # Has 2 atomics
        atomic_to_extract = atomic_ids[0]
        
        result = unmerge_device_profiles(profile_id, atomic_to_extract)
        
        assert result['status'] == 'ok'
        assert 'new_profile_id' in result
        assert result['updated_profile_id'] == profile_id
        new_profile_id = result['new_profile_id']
        
        # Verify new profile was created
        json_cols = {'attributes', 'origins', 'tags', 'labels', 'atomic_devices_ids'}
        with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
            new_profile = conn.execute('SELECT * FROM device_profiles WHERE id = ?', (new_profile_id,)).fetchone()
            assert new_profile is not None
            assert new_profile['atomic_devices_ids'] == [atomic_to_extract]
            assert new_profile['user_label'] is None
            
            # Verify updated profile has remaining atomic
            updated = conn.execute('SELECT * FROM device_profiles WHERE id = ?', (profile_id,)).fetchone()
            assert updated is not None
            assert len(updated['atomic_devices_ids']) == 1  # 2 - 1 extracted
            assert atomic_to_extract not in updated['atomic_devices_ids']
    
    def test_unmerge_profile_not_found(self, db_with_profiles):
        """Test unmerge with non-existent profile."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        fake_id = str(uuid.uuid4())
        
        result = unmerge_device_profiles(fake_id, atomic_ids[0])
        
        assert result['status'] == 'error'
        assert 'not found' in result['message'].lower()
    
    def test_unmerge_single_atomic_ineligible(self, db_with_profiles):
        """Test that profiles with only 1 atomic cannot be unmerged."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        profile_id = profile_ids[1]  # Has only 1 atomic
        
        result = unmerge_device_profiles(profile_id, atomic_ids[2])
        
        assert result['status'] == 'ineligible'
        assert 'only 1 atomic' in result['message'].lower()
    
    def test_unmerge_atomic_not_in_profile(self, db_with_profiles):
        """Test unmerge with atomic not in the profile."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        profile_id = profile_ids[0]
        wrong_atomic = atomic_ids[3]  # Not in profile 0
        
        result = unmerge_device_profiles(profile_id, wrong_atomic)
        
        assert result['status'] == 'error'
        assert 'not in profile' in result['message'].lower()
    
    def test_unmerge_hard_merged_profile_ineligible(self, db_with_profiles):
        """Test that hard-merged profiles (specificity >= 3) cannot be unmerged."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        
        # Create a hard-merged profile
        json_cols = {'attributes', 'origins', 'tags', 'labels', 'atomic_devices_ids'}
        with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
            ts = datetime.now(timezone.utc).timestamp()
            hard_id = str(uuid.uuid4())
            hard_atomic = str(uuid.uuid4())
            
            conn.execute(
                '''INSERT INTO atomic_devices 
                   (id, attributes, origins, upload_ids, file_ids, devices_raw_ids, specificity)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (hard_atomic, json.dumps({'device_id': 'imei_12345'}),
                 json.dumps([{'origin': 'test', 'upload_id': 'upload1'}]),
                 json.dumps(['upload1']), json.dumps(['file1']), json.dumps(['raw1']), 3)
            )
            
            conn.execute(
                '''INSERT INTO device_profiles 
                   (id, atomic_devices_ids, attributes, specificity, model, manufacturer, origins, 
                    system_soft_merge, is_generic, user_label, notes, tags, labels, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (hard_id, json.dumps([hard_atomic, atomic_ids[0]]),
                 json.dumps({'device_id': 'imei_12345'}),
                 3, 'Model', 'Mfr', json.dumps([]),
                 0, 0, None, None, '[]', '[]', ts, ts)
            )
            conn.commit()
        
        result = unmerge_device_profiles(hard_id, hard_atomic)
        
        assert result['status'] == 'ineligible'
        assert 'hard-merged' in result['message'].lower()
    
    def test_unmerge_preserves_metadata(self, db_with_profiles):
        """Test that unmerge preserves target profile metadata."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        profile_id = profile_ids[0]
        
        json_cols = {'attributes', 'origins', 'tags', 'labels', 'atomic_devices_ids'}
        with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
            # Update profile with metadata
            ts = datetime.now(timezone.utc).timestamp()
            conn.execute(
                '''UPDATE device_profiles 
                   SET user_label = ?, notes = ?, tags = ?, labels = ?
                   WHERE id = ?''',
                ('My Device', 'Test notes', json.dumps(['work', 'phone']), 
                 json.dumps(['personal']), profile_id)
            )
            conn.commit()
        
        result = unmerge_device_profiles(profile_id, atomic_ids[0])
        
        assert result['status'] == 'ok'
        
        with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
            updated = conn.execute('SELECT * FROM device_profiles WHERE id = ?', (profile_id,)).fetchone()
            assert updated['user_label'] == 'My Device'
            assert updated['notes'] == 'Test notes'
            # Database returns parsed JSON lists since we specified json_columns
            assert updated['tags'] == ['work', 'phone']
            assert updated['labels'] == ['personal']


class TestMergeUnmergeIntegration:
    
    def test_merge_then_unmerge_roundtrip(self, db_with_profiles):
        """Test merging two profiles then unmerging them."""
        db_path, profile_ids, atomic_ids = db_with_profiles
        src_id = profile_ids[2]
        tgt_id = profile_ids[0]
        src_atomic = atomic_ids[3]
        
        # Merge
        merge_result = merge_device_profiles(src_id, tgt_id)
        assert merge_result['status'] == 'ok'
        
        # Now unmerge the extracted atomic
        unmerge_result = unmerge_device_profiles(tgt_id, src_atomic)
        assert unmerge_result['status'] == 'ok'
        
        # Verify new profile was created with the extracted atomic
        json_cols = {'attributes', 'origins', 'tags', 'labels', 'atomic_devices_ids'}
        with DatabaseSession(db_path, use_dict_factory=True, json_columns=json_cols) as conn:
            new_profile = conn.execute(
                'SELECT * FROM device_profiles WHERE id = ?', 
                (unmerge_result['new_profile_id'],)
            ).fetchone()
            assert new_profile['atomic_devices_ids'] == [src_atomic]


class TestMergeAttrsWithMixedTypes:
    """Test merge_attrs and pick_most_specific with various data types."""
    
    def test_pick_most_specific_strings_only(self):
        """Test pick_most_specific with only string values."""
        result = pick_most_specific(['iPhone', 'iPhone XR', 'iPhone'])
        assert result == 'iPhone XR', "Should pick the most specific (with variant)"
    
    def test_pick_most_specific_with_generic(self):
        """Test pick_most_specific filters out generic names."""
        result = pick_most_specific(['iPhone', 'iPhone 13', 'phone'])
        assert result == 'iPhone 13', "Should pick the specific model over generic"
    
    def test_pick_most_specific_empty_strings(self):
        """Test pick_most_specific with empty strings."""
        result = pick_most_specific(['', 'iPhone XR', ''])
        assert result == 'iPhone XR', "Should ignore empty strings"
    
    def test_pick_most_specific_non_strings(self):
        """Test pick_most_specific with non-string values filters them out."""
        result = pick_most_specific([123, 456, 'iPhone XR'])
        assert result == 'iPhone XR', "Should ignore non-string values"
    
    def test_pick_most_specific_all_non_strings(self):
        """Test pick_most_specific with only non-string values returns empty string."""
        result = pick_most_specific([123, 456, True])
        assert result == '', "Should return empty string when no strings found"
    
    def test_merge_attrs_with_strings(self):
        """Test merge_attrs with string values only."""
        attrs_list = [
            {'model': 'iPhone', 'manufacturer': 'Apple'},
            {'model': 'iPhone XR', 'manufacturer': 'Apple'}
        ]
        result = merge_attrs(attrs_list, mode='soft')
        assert result['model'] == 'iPhone XR', "Should pick most specific model"
        assert result['manufacturer'] == 'Apple', "Should keep common values"
    
    def test_merge_attrs_with_mixed_types(self):
        """Test merge_attrs with mixed string and integer types."""
        attrs_list = [
            {'model': 'iPhone', 'api_level': 14, 'os_version': '14.5'},
            {'model': 'iPhone XR', 'api_level': 15, 'os_version': '15.0'}
        ]
        result = merge_attrs(attrs_list, mode='soft')
        # Strings should use pick_most_specific
        assert result['model'] == 'iPhone XR', "Should pick most specific model"
        assert result['os_version'] == '14.5', "Should use first non-empty string value for mixed types"
        # Integers should use first-non-empty
        assert result['api_level'] == 14, "Should use first non-empty value for integers"
    
    def test_merge_attrs_with_integers_only(self):
        """Test merge_attrs with integer values only."""
        attrs_list = [
            {'api_level': 14, 'build_number': 1},
            {'api_level': 15, 'build_number': 2}
        ]
        result = merge_attrs(attrs_list, mode='soft')
        # Non-string types should use first-non-empty logic
        assert result['api_level'] == 14, "Should use first non-empty value for integers"
        assert result['build_number'] == 1, "Should use first non-empty value for integers"
    
    def test_merge_attrs_sparse_fields(self):
        """Test merge_attrs when fields are missing in some dicts."""
        attrs_list = [
            {'model': 'iPhone', 'manufacturer': 'Apple'},
            {'model': None, 'os': 'iOS'},  # model is None/empty
            {'model': 'iPhone 13', 'manufacturer': None}
        ]
        result = merge_attrs(attrs_list, mode='soft')
        # Should skip None/falsy values and pick the best non-empty one
        assert result['model'] == 'iPhone 13', "Should skip None and pick specific model"
        assert result['manufacturer'] == 'Apple', "Should use first non-empty value"
        assert result['os'] == 'iOS', "Should preserve unique fields"

