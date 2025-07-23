import os
import json
from pathlib import Path


class ConfigLoader:
    @staticmethod
    def load_file_paths():
        project_root = Path(__file__).resolve().parent.parent
        config_dir = project_root / "config"
        json_path = config_dir / "file_paths.json"
        try:
            paths = json.loads(json_path.read_text(encoding="utf-8"))
            for k, v in paths.items():
                if isinstance(v, str):
                    paths[k] = os.path.expandvars(v)
            return paths
        except FileNotFoundError:
            raise FileNotFoundError(f"file_paths.json not found at {json_path}")
        except Exception as e:
            raise RuntimeError(f"Error loading file_paths.json: {e}")


class ConfigManager:
    def __init__(self, config_dir=None):
        self.project_root = Path(__file__).resolve().parent.parent
        self.config_dir = (
            Path(config_dir) if config_dir else self.project_root / "config"
        )
        self._configs = {}

    def load(self, filename):
        path = self.config_dir / filename
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
            for k, v in config.items():
                if isinstance(v, str):
                    config[k] = os.path.expandvars(v)
            self._configs[filename] = config
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {path}")
        except Exception as e:
            raise RuntimeError(f"Error loading config {filename}: {e}")

    def get(self, filename, key=None):
        config = self._configs.get(filename)
        if config is None:
            config = self.load(filename)
        if key:
            return config.get(key)
        return config

    def update(self, filename, key, value):
        config = self.get(filename)
        config[key] = value
        self._configs[filename] = config
        path = self.config_dir / filename
        try:
            path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"Error updating config {filename}: {e}")

    def reload(self, filename):
        return self.load(filename)

    def validate(self, filename, required_keys):
        config = self.get(filename)
        missing = [k for k in required_keys if k not in config]
        if missing:
            raise KeyError(f"Missing required keys in {filename}: {missing}")
        return True
