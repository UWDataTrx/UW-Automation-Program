# Basic ConfigLoader and ConfigManager implementation for config loading
import os
import json


class ConfigLoader:
    @staticmethod
    def load_file_paths():
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_dir = os.path.join(project_root, "config")
        json_path = os.path.join(config_dir, "file_paths.json")
        try:
            with open(json_path, "r") as f:
                paths = json.load(f)
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
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_dir = config_dir or os.path.join(self.project_root, "config")
        self._configs = {}

    def load(self, filename):
        path = os.path.join(self.config_dir, filename)
        try:
            with open(path, "r") as f:
                config = json.load(f)
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
        path = os.path.join(self.config_dir, filename)
        try:
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
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
