import os
import json
from pathlib import Path


class ConfigLoader:
    """
    Centralized configuration loader that resolves paths and
    environment-specific overrides.
    """

    def __init__(self, config_path="file_paths.json"):
        self.config_path = config_path
        self.config = {}
        self.onedrive_path = os.environ.get("OneDrive")
        if not self.onedrive_path:
            raise EnvironmentError("OneDrive environment variable not found.")
        self._load()

    def _load(self):
        with open(self.config_path, "r") as f:
            raw_config = json.load(f)
        self.config = {key: self._resolve(path) for key, path in raw_config.items()}

    def _resolve(self, path):
        if path.startswith("%OneDrive%"):
            return str(Path(path.replace("%OneDrive%", self.onedrive_path)).resolve())
        return str(Path(path).resolve())

    def get(self, key):
        return self.config.get(key)

    def all(self):
        return self.config


# Usage example:
# cfg = ConfigLoader()
# print(cfg.get("reprice"))
# print(cfg.all())
