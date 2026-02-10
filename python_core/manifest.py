import yaml
import re
import os
import logging
from cfg import MANIFESTS_DIR

class Manifest:

    def __init__(self, platform, manifest_dir=MANIFESTS_DIR, validate=True):
        self.platform = platform
        self.view_index_map = {}  # manifest file_id --> list of view indexes
        self.config = {}
        
        with open(os.path.join(manifest_dir, f"{platform}.yaml"), 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        if validate and not self.validate():
            raise ValueError(f"[Manifest] '{platform}' failed validation.")
        
        for i, v in enumerate(self.config.get('views', [])):
            file_id = v.get('file', {}).get('id')
            if file_id:
                if file_id not in self.view_index_map:
                    self.view_index_map[file_id] = []
                self.view_index_map[file_id].append(i)


    def validate(self):
        if 'files' not in self.config:
            print(f"[Manifest] {self.platform} missing 'files' section.")
            return False
        
        for fs in self.config.get('files', []):
            if 'id' not in fs or 'path' not in fs:
                print(f"[Manifest] file entry missing 'id' or 'path': {fs}")
                return False
            
        if 'views' not in self.config:
            print(f"[Manifest] {self.platform} missing 'views' section.")
            return False
        for v in self.config.get('views', []):
            if 'file' not in v or 'id' not in v['file']:
                print(f"[Manifest] view entry missing 'file.id': {v}")
                return False
        return True

    def file_paths(self):
        paths = []
        for fs in self.config.get('files', []):
            path = fs.get('path')
            if path is not None:
                paths.append(path)
        return paths
    

    def get_file_cfg(self, raw_filename):
        # Matches a filename to a file_source definition.
        clean_name = raw_filename.replace('\\', '/').replace('___', '/') # handling flattened OPFS names too
        
        for fs in self.config.get('files', []):
            path = fs.get('path')
            if path and clean_name.lower().endswith(path.lower()):
                return fs
        return {}
    
    
    def views(self, manifest_file_id):
        if manifest_file_id not in self.view_index_map:
            print(f"[Manifest] No views found for file id '{manifest_file_id}' in platform '{self.platform}'.") 
        indexes = self.view_index_map.get(manifest_file_id, [])
        return [self.config.get('views', [])[i] for i in indexes]




    # def __init__(self, configs):
    #     self.configs = configs
    #     self.file_map = self._build_file_map()
    #     self.source_view_map = self._build_source_view_map()

    # @classmethod
    # def from_directory(cls, platform, dir_path=MANIFESTS_DIR):
    #     """
    #     Scans a directory for .yaml files and loads them into a Manifest instance.
    #     """
    #     logger = logging.getLogger(__name__)
    #     configs = []
        
    #     if not os.path.exists(dir_path):
    #         logger.warning(f"Manifest directory not found: {dir_path}")
    #         return cls([])

    #     for filename in os.listdir(dir):
    #         if not filename.endswith('.yaml'):
    #             continue
            
    #         full_path = os.path.join(dir_path, filename)
    #         try:
    #             with open(full_path, 'r', encoding='utf-8') as f:
    #                 doc = yaml.safe_load(f)
    #                 if doc:
    #                     configs.append(doc)
    #         except Exception as e:
    #             logger.error(f"Failed to load manifest file {filename}: {e}")
    #             # Continue loading others
        
    #     return cls(configs)

    # def _build_file_map(self):
    #     """
    #     Builds a map of { file_suffix : { 'source_id': ..., 'parser_config': ... } }
    #     """
    #     file_map = []
    #     for config in self.configs:
    #         file_sources = config.get('file_sources', [])
    #         for fs in file_sources:
    #             path = fs.get('path')
    #             if path:
    #                 file_map.append({
    #                     'suffix': path,
    #                     'source_id': fs.get('id'),
    #                     'parser_config': fs.get('parser', {})
    #                 })
    #     return file_map

    # def _build_source_view_map(self):
    #     """
    #     Builds a map of { source_id : [ view_config, ... ] }
    #     """
    #     view_map = {}
    #     for config in self.configs:
    #         views = config.get('views', [])
    #         for view in views:
    #             # Support both new 'file_source.id' and old 'source_id' syntax if needed
    #             # The user's latest update uses:
    #             # - file_source: { id: "..." }
    #             # But previously used source_id: "..."
                
    #             source_id = None
    #             fs_block = view.get('file_source')
    #             if fs_block:
    #                 source_id = fs_block.get('id')
    #             else:
    #                 source_id = view.get('source_id')
                
    #             if source_id:
    #                 if source_id not in view_map:
    #                     view_map[source_id] = []
    #                 view_map[source_id].append(view)
    #     return view_map

    # def get_file_config(self, filename):
    #     """
    #     Matches a filename to a file_source definition.
    #     Returns (source_id, parser_config) or (None, None).
    #     Matches if filename ends with the path defined in file_sources.
    #     """
    #     # Normalize filename to forward slashes just in case
    #     clean_name = filename.replace('\\', '/').replace('___', '/') # Handling flattened OPFS names too
        
    #     for entry in self.file_map:
    #         # Suffix match
    #         if clean_name.lower().endswith(entry['suffix'].lower()):
    #             return entry['source_id'], entry['parser_config']
    #     return None, None

    # def get_views_for_source(self, source_id):
    #     """
    #     Returns a list of view configurations for a given source_id.
    #     """
    #     return self.source_view_map.get(source_id, [])
