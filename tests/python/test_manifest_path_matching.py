import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../python_core'))

from manifest import Manifest


class TestManifestPathMatching:
    """Test manifest file path matching with glob patterns and OPFS flattened names."""

    def test_matches_opfs_flattened_subscriber_info(self):
        """Test matching OPFS flattened filename against manifest glob pattern."""
        manifest = Manifest('google', manifest_dir='manifests', validate=False)
        
        # OPFS filename (flattened with ___)
        opfs_filename = "google___Google Account___bob.researcher24.SubscriberInfo.html"
        
        cfg = manifest.get_file_cfg(opfs_filename)
        
        assert cfg.get('id') == 'ggl_subscriber_info', f"Expected ggl_subscriber_info, got {cfg.get('id')}"
        assert cfg.get('path') == 'Google Account/*.SubscriberInfo.html'

    def test_matches_opfs_flattened_change_history(self):
        """Test matching ChangeHistory OPFS filename."""
        manifest = Manifest('google', manifest_dir='manifests', validate=False)
        
        opfs_filename = "google___Google Account___bob.researcher24.ChangeHistory.html"
        cfg = manifest.get_file_cfg(opfs_filename)
        
        assert cfg.get('id') == 'ggl_change_history', f"Expected ggl_change_history, got {cfg.get('id')}"
        assert cfg.get('path') == 'Google Account/*.ChangeHistory.html'

    def test_matches_opfs_flattened_devices_csv(self):
        """Test matching Devices CSV OPFS filename with wildcard in manifest."""
        manifest = Manifest('google', manifest_dir='manifests', validate=False)
        
        # Test with wildcard pattern - manifest uses "Devices - A list of devices*"
        opfs_filename = "google___Access Log Activity___Devices - A list of devices (i.e. Nest, Pixel, iPh.csv"
        cfg = manifest.get_file_cfg(opfs_filename)
        
        assert cfg.get('id') == 'ggl_access_log_devices', \
            f"Expected ggl_access_log_devices, got {cfg.get('id')}"

    def test_matches_takeout_myactivity(self):
        """Test matching Takeout MyActivity HTML."""
        manifest = Manifest('google', manifest_dir='manifests', validate=False)
        
        opfs_filename = "google___My Activity___Takeout___MyActivity.html"
        cfg = manifest.get_file_cfg(opfs_filename)
        
        assert cfg.get('id') == 'ggl_takeout_activity', \
            f"Expected ggl_takeout_activity, got {cfg.get('id')}"

    def test_no_match_returns_empty_dict(self):
        """Test that non-matching filename returns empty dict."""
        manifest = Manifest('google', manifest_dir='manifests', validate=False)
        
        opfs_filename = "google___Some Other Folder___RandomFile.txt"
        cfg = manifest.get_file_cfg(opfs_filename)
        
        assert cfg == {}, f"Expected empty dict for non-matching file, got {cfg}"

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        manifest = Manifest('google', manifest_dir='manifests', validate=False)
        
        # Mixed case
        opfs_filename = "GOOGLE___Google Account___BOB.RESEARCHER24.SubscriberInfo.HTML"
        cfg = manifest.get_file_cfg(opfs_filename)
        
        assert cfg.get('id') == 'ggl_subscriber_info', \
            f"Expected case-insensitive match, got {cfg.get('id')}"

    def test_wildcard_pattern_matching(self):
        """Test that wildcard patterns in manifest paths work correctly."""
        manifest = Manifest('google', manifest_dir='manifests', validate=False)
        
        # Manifest uses "Devices - A list of devices*" which matches any filename starting with that prefix
        # Test various forms of the Devices filename
        test_filenames = [
            "google___Access Log Activity___Devices - A list of devices.csv",
            "google___Access Log Activity___Devices - A list of devices (i.e. Nest, Pixel, iPh.csv",
            "google___Access Log Activity___Devices - A list of devices that have accessed your account.csv",
        ]
        
        for opfs_filename in test_filenames:
            cfg = manifest.get_file_cfg(opfs_filename)
            assert cfg.get('id') == 'ggl_access_log_devices', \
                f"Expected ggl_access_log_devices for {opfs_filename}, got {cfg.get('id')}"
