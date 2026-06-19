import yaml
import os
import builtins
import fnmatch


class Manifest:
    def __init__(self, platform: str, manifest_dir: str = None, validate: bool = True) -> None:
        manifest_dir = manifest_dir or getattr(builtins, "MANIFESTS_DIR", "/manifests")
        self.platform = platform
        self.view_index_map = {}  # manifest file_id --> list of view indexes
        self.config = {}

        with open(
            os.path.join(manifest_dir, f"{platform}.yaml"), "r", encoding="utf-8"
        ) as f:
            self.config = yaml.safe_load(f)

        if validate and not self.validate():
            raise ValueError(f"[Manifest] '{platform}' failed validation.")

        for i, v in enumerate(self.config.get("views", [])):
            file_id = v.get("file", {}).get("id")
            if file_id:
                if file_id not in self.view_index_map:
                    self.view_index_map[file_id] = []
                self.view_index_map[file_id].append(i)

    def validate(self) -> bool:
        if "files" not in self.config:
            print(f"[Manifest] {self.platform} missing 'files' section.")
            return False

        for fs in self.config.get("files", []):
            if "id" not in fs or "path" not in fs:
                print(f"[Manifest] file entry missing 'id' or 'path': {fs}")
                return False

        if "views" not in self.config:
            print(f"[Manifest] {self.platform} missing 'views' section.")
            return False
        for v in self.config.get("views", []):
            if "file" not in v or "id" not in v["file"]:
                print(f"[Manifest] view entry missing 'file.id': {v}")
                return False
        return True

    def file_paths(self) -> list:
        paths = []
        for fs in self.config.get("files", []):
            path = fs.get("path")
            if path is not None:
                paths.append(path)
        return paths

    def get_file_cfg(self, raw_filename: str) -> dict:
        """ Since OPFS filenames are flattened as 'platform___path___filename', this needs to match to with the manifest format of 'path/filename' """
        clean_name = raw_filename.replace("\\", "/").replace(
            "___", "/"
        )  # handling flattened OPFS names too

        parts = clean_name.split("/", 1)
        if len(parts) > 1:
            clean_name = parts[1]  # Everything after the platform prefix

        for fs in self.config.get("files", []):
            path = fs.get("path")
            if path and fnmatch.fnmatch(clean_name.lower(), path.lower()):
                return fs
        return {}

    def views(self, manifest_file_id: str) -> list:
        if manifest_file_id not in self.view_index_map:
            print(
                f"[Manifest] No views found for file id '{manifest_file_id}' in platform '{self.platform}'."
            )
        indexes = self.view_index_map.get(manifest_file_id, [])
        return [self.config.get("views", [])[i] for i in indexes]
