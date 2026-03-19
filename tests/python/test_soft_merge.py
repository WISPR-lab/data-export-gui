import pytest
# Import worker first to establish proper module loading order (avoids circular imports)
import device_grouping.worker
from device_grouping.soft_merge import (
    soft_merge_single_upload,
    soft_merge_multi_upload_increment,
    _soft_match,
    _compute_is_generic
)


class TestSoftMatch:
    """Test the core soft-match logic"""
    
    def test_both_specific_same_model_match(self):
        """Both spec >= 2, same model → should match"""
        attrs_a = {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}
        attrs_b = {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}
        assert _soft_match(attrs_a, attrs_b, 2, 2) == True
    
    def test_both_specific_different_model_no_match(self):
        """Both spec >= 2, different models → should NOT match"""
        attrs_a = {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}
        attrs_b = {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 7'}
        assert _soft_match(attrs_a, attrs_b, 2, 2) == False
    
    def test_generic_apple_no_match(self):
        """Generic iPhone + specific iPhone, Apple → should NOT match (UA masking)"""
        attrs_a = {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone'}
        attrs_b = {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}
        assert _soft_match(attrs_a, attrs_b, 1, 2) == False
    
    def test_both_generic_apple_no_match(self):
        """Both generic Apple → should NOT match (UA masking)"""
        attrs_a = {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone'}
        attrs_b = {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone'}
        assert _soft_match(attrs_a, attrs_b, 1, 1) == False
    
    def test_generic_android_match(self):
        """Generic Android + specific Android, same model → should match (non-Apple)"""
        attrs_a = {'device_manufacturer': 'Samsung', 'device_model_name': 'Galaxy'}
        attrs_b = {'device_manufacturer': 'Samsung', 'device_model_name': 'Galaxy S21'}
        assert _soft_match(attrs_a, attrs_b, 1, 2) == True
    
    def test_different_manufacturers_no_match(self):
        """Different manufacturers → should NOT match"""
        attrs_a = {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}
        attrs_b = {'device_manufacturer': 'Samsung', 'device_model_name': 'Galaxy S21'}
        assert _soft_match(attrs_a, attrs_b, 2, 2) == False
    
    def test_missing_model_no_match(self):
        """Missing model field → should NOT match"""
        attrs_a = {'device_manufacturer': 'Apple'}
        attrs_b = {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}
        assert _soft_match(attrs_a, attrs_b, 2, 2) == False
    
    def test_ua_device_model_fallback(self):
        """Fallback to user_agent_device_model if device_model_name missing"""
        attrs_a = {'device_manufacturer': 'Apple', 'user_agent_device_model': 'iPhone 13'}
        attrs_b = {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}
        assert _soft_match(attrs_a, attrs_b, 2, 2) == True


class TestComputeIsGeneric:
    """Test is_generic flag computation"""
    
    def test_apple_generic_is_generic(self):
        """Apple device with spec < 2 → is_generic = 1"""
        atomic = {
            'specificity': 1,
            'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone'}
        }
        assert _compute_is_generic(atomic) == 1
    
    def test_apple_specific_not_generic(self):
        """Apple device with spec >= 2 → is_generic = 0"""
        atomic = {
            'specificity': 2,
            'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}
        }
        assert _compute_is_generic(atomic) == 0
    
    def test_samsung_generic_not_generic(self):
        """Samsung generic device → is_generic = 0 (non-Apple)"""
        atomic = {
            'specificity': 1,
            'attributes': {'device_manufacturer': 'Samsung', 'device_model_name': 'Galaxy'}
        }
        assert _compute_is_generic(atomic) == 0


class TestSoftMergeSingleUpload:
    """Test single-upload soft merge"""
    
    def test_two_matching_iphone_xrs(self):
        """Two iPhone 7s from same upload → should be merged into one profile"""
        atomics = [
            {
                'id': 'atomic_1',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 7'}
            },
            {
                'id': 'atomic_2',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 7'}
            }
        ]
        
        profiles = soft_merge_single_upload(atomics)
        
        assert len(profiles) == 1
        assert set(profiles[0]['atomic_devices_ids']) == {'atomic_1', 'atomic_2'}
        assert profiles[0]['system_soft_merge'] == 1  # 2 atomics merged
        assert profiles[0]['is_generic'] == 0  # spec=2, not generic
    
    def test_generic_apple_stays_separate(self):
        """Generic iPhone doesn't merge with iPhone 13 (Apple UA masking)"""
        atomics = [
            {
                'id': 'atomic_1',
                'specificity': 1,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone'}
            },
            {
                'id': 'atomic_2',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}
            }
        ]
        
        profiles = soft_merge_single_upload(atomics)
        
        assert len(profiles) == 2
        assert profiles[0]['system_soft_merge'] == 0
        assert profiles[0]['is_generic'] == 1
        assert profiles[1]['system_soft_merge'] == 0
        assert profiles[1]['is_generic'] == 0
    
    def test_three_atomics_merging(self):
        """Three matching atomics → merged into one profile"""
        atomics = [
            {
                'id': 'a1',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Samsung', 'device_model_name': 'Galaxy S21'}
            },
            {
                'id': 'a2',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Samsung', 'device_model_name': 'Galaxy S21'}
            },
            {
                'id': 'a3',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Samsung', 'device_model_name': 'Galaxy S21'}
            }
        ]
        
        profiles = soft_merge_single_upload(atomics)
        
        assert len(profiles) == 1
        assert len(profiles[0]['atomic_devices_ids']) == 3
        assert profiles[0]['system_soft_merge'] == 1


class TestSoftMergeMultiUploadIncrement:
    """Test multi-upload incremental soft merge"""
    
    def test_new_atomic_matches_one_profile(self):
        """New iPhone 7 matches existing profile with iPhone 7 → add to profile"""
        existing_profiles = [
            {
                'id': 'profile_1',
                'atomic_devices_ids': ['atomic_1'],
                'system_soft_merge': 0,
                'is_generic': 0
            }
        ]
        
        all_atomics = {
            'atomic_1': {
                'id': 'atomic_1',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 7'}
            },
            'atomic_2': {
                'id': 'atomic_2',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 7'}
            }
        }
        
        new_atomics = [all_atomics['atomic_2']]
        
        result = soft_merge_multi_upload_increment(new_atomics, existing_profiles, all_atomics)
        
        assert 'profile_1' in result['profiles_to_update']
        assert 'atomic_2' in result['profiles_to_update']['profile_1']
        assert len(result['new_profiles']) == 0
    
    def test_new_atomic_no_match(self):
        """New iPhone 7 with no matching profile → create new profile"""
        existing_profiles = [
            {
                'id': 'profile_1',
                'atomic_devices_ids': ['atomic_1'],
                'system_soft_merge': 0,
                'is_generic': 0
            }
        ]
        
        all_atomics = {
            'atomic_1': {
                'id': 'atomic_1',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}
            },
            'atomic_2': {
                'id': 'atomic_2',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 7'}
            }
        }
        
        new_atomics = [all_atomics['atomic_2']]
        
        result = soft_merge_multi_upload_increment(new_atomics, existing_profiles, all_atomics)
        
        assert len(result['profiles_to_update']) == 0
        assert len(result['new_profiles']) == 1
        assert 'atomic_2' in result['new_profiles'][0]['atomic_devices_ids']
    
    def test_new_atomic_multiple_matches_deferred(self):
        """New iPhone 7 matches 2+ profiles → create new profile, user disambiguates"""
        existing_profiles = [
            {
                'id': 'profile_1',
                'atomic_devices_ids': ['atomic_1'],
                'system_soft_merge': 0,
                'is_generic': 0
            },
            {
                'id': 'profile_2',
                'atomic_devices_ids': ['atomic_2'],
                'system_soft_merge': 0,
                'is_generic': 0
            }
        ]
        
        all_atomics = {
            'atomic_1': {
                'id': 'atomic_1',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 7'}
            },
            'atomic_2': {
                'id': 'atomic_2',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 7'}
            },
            'atomic_3': {
                'id': 'atomic_3',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 7'}
            }
        }
        
        new_atomics = [all_atomics['atomic_3']]
        
        result = soft_merge_multi_upload_increment(new_atomics, existing_profiles, all_atomics)
        
        # Should create new profile instead of auto-merging
        assert len(result['profiles_to_update']) == 0
        assert len(result['new_profiles']) == 1
        assert 'atomic_3' in result['new_profiles'][0]['atomic_devices_ids']
    
    def test_generic_device_creates_new_profile(self):
        """Generic iPhone → create new profile (no system-matched soft merge for generics)"""
        existing_profiles = [
            {
                'id': 'profile_1',
                'atomic_devices_ids': ['atomic_1'],
                'system_soft_merge': 0,
                'is_generic': 0
            }
        ]
        
        all_atomics = {
            'atomic_1': {
                'id': 'atomic_1',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 13'}
            },
            'atomic_2': {
                'id': 'atomic_2',
                'specificity': 1,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone'}
            }
        }
        
        new_atomics = [all_atomics['atomic_2']]
        
        result = soft_merge_multi_upload_increment(new_atomics, existing_profiles, all_atomics)
        
        # Generic iPhone should NOT merge with specific iPhone 13
        assert len(result['profiles_to_update']) == 0
        assert len(result['new_profiles']) == 1
        assert result['new_profiles'][0]['is_generic'] == 1
    
    def test_multiple_new_atomics(self):
        """Process multiple new atomics, some matching, some not"""
        existing_profiles = [
            {
                'id': 'iphone_profile',
                'atomic_devices_ids': ['iphone_1'],
                'system_soft_merge': 1,
                'is_generic': 0
            }
        ]
        
        all_atomics = {
            'iphone_1': {
                'id': 'iphone_1',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 7'}
            },
            'iphone_2': {
                'id': 'iphone_2',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Apple', 'device_model_name': 'iPhone 7'}
            },
            'samsung_1': {
                'id': 'samsung_1',
                'specificity': 2,
                'attributes': {'device_manufacturer': 'Samsung', 'device_model_name': 'Galaxy S21'}
            }
        }
        
        new_atomics = [all_atomics['iphone_2'], all_atomics['samsung_1']]
        
        result = soft_merge_multi_upload_increment(new_atomics, existing_profiles, all_atomics)
        
        # iphone_2 matches → should be added to iphone_profile
        assert 'iphone_profile' in result['profiles_to_update']
        assert 'iphone_2' in result['profiles_to_update']['iphone_profile']
        
        # samsung_1 doesn't match → should create new profile
        assert len(result['new_profiles']) == 1
        assert 'samsung_1' in result['new_profiles'][0]['atomic_devices_ids']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
