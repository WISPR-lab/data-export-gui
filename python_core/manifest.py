import yaml
import os
import builtins
import fnmatch
from python_core.logger import get_logger

logger = get_logger("manifest")


class Manifest:
    def __init__(
        self, platform: str, manifest_dir: str = None, validate: bool = True
    ) -> None:
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

        self.action_labels = {}
        taxonomy_path = os.path.join(manifest_dir, "__taxonomy.yaml")
        if os.path.exists(taxonomy_path):
            try:
                with open(taxonomy_path, "r", encoding="utf-8") as f:
                    taxonomy = yaml.safe_load(f) or {}
                allowed = ((taxonomy.get("fields") or {}).get("event.action") or {}).get("allowed_values") or {}
                self.action_labels = {
                    action: entry["short_name"]
                    for action, entry in allowed.items()
                    if isinstance(entry, dict) and entry.get("short_name")
                }
            except yaml.YAMLError as e:
                logger.warning("__taxonomy.yaml failed to parse, action labels unavailable: %s", e)

        for i, v in enumerate(self.config.get("views", [])):
            file_id = v.get("file", {}).get("id")
            if file_id:
                if file_id not in self.view_index_map:
                    self.view_index_map[file_id] = []
                self.view_index_map[file_id].append(i)

    def validate(self) -> bool:
        if "files" not in self.config:
            logger.warning("%s missing 'files' section.", self.platform)
            return False

        for fs in self.config.get("files", []):
            if "id" not in fs or "path" not in fs:
                logger.warning("file entry missing 'id' or 'path': %s", fs)
                return False

        if "views" not in self.config:
            logger.warning("%s missing 'views' section.", self.platform)
            return False
        for v in self.config.get("views", []):
            if "file" not in v or "id" not in v["file"]:
                logger.warning("view entry missing 'file.id': %s", v)
                return False
        return True

    def file_paths(self) -> list:
        paths = []
        for fs in self.config.get("files", []):
            path = fs.get("path")
            if path is not None:
                paths.append(path)
        return paths

    def _match_files(self, clean_name: str) -> list:
        return [
            fs
            for fs in self.config.get("files", [])
            if fs.get("path") and fnmatch.fnmatch(clean_name.lower(), fs["path"].lower())
        ]

    def get_file_cfgs(self, raw_filename: str) -> list:
        """Matches an OPFS-flattened filename ('___' standing in for '/') against manifest paths, retrying with a leading segment stripped for exports that wrap everything in one root folder."""
        clean_name = raw_filename.replace("\\", "/").replace("___", "/")

        matches = self._match_files(clean_name)
        if matches:
            return matches

        parts = clean_name.split("/", 1)
        if len(parts) > 1:
            matches = self._match_files(parts[1])
        return matches

    def views(self, manifest_file_id: str) -> list:
        if manifest_file_id not in self.view_index_map:
            print(
                f"[Manifest] No views found for file id '{manifest_file_id}' in platform '{self.platform}'."
            )
        indexes = self.view_index_map.get(manifest_file_id, [])
        return [self.config.get("views", [])[i] for i in indexes]
