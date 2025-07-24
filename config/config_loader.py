import os
import json
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class ConfigLoader:
    @staticmethod
    def load_file_paths():
        project_root = Path(__file__).resolve().parent.parent
        config_dir = project_root / "config"
        json_path = config_dir / "file_paths.json"
        try:
            paths = json.loads(json_path.read_text(encoding="utf-8"))
            # Fallback: allow user to specify OneDrive path in environment or config
            user_onedrive_path = os.environ.get("USER_ONEDRIVE_PATH")
            if not user_onedrive_path:
                # Try to load from config/user_onedrive_path.txt if it exists
                user_onedrive_config = config_dir / "user_onedrive_path.txt"
                if user_onedrive_config.exists():
                    user_onedrive_path = user_onedrive_config.read_text(encoding="utf-8").strip()
            # Try to find the correct OneDrive folder
            user_profile = os.environ.get("USERPROFILE")
            possible_onedrive_folders = []
            if user_onedrive_path:
                possible_onedrive_folders.append(user_onedrive_path)
            if user_profile:
                possible_onedrive_folders.append(os.path.join(user_profile, "OneDrive - True Rx Health Strategists"))
                possible_onedrive_folders.append(os.path.join(user_profile, "OneDrive"))
            # Also check environment variable
            env_onedrive = os.environ.get("OneDrive") or os.environ.get("ONEDRIVE")
            if env_onedrive:
                possible_onedrive_folders.insert(0, env_onedrive)
            # Pick the first that exists
            onedrive_env = None
            for folder in possible_onedrive_folders:
                if folder and os.path.exists(folder):
                    onedrive_env = folder
                    break
            if not onedrive_env:
                raise RuntimeError(
                    "Could not find OneDrive folder. Please ensure OneDrive is installed and synced, or set the OneDrive path manually. "
                    "You can set the USER_ONEDRIVE_PATH environment variable or create a config/user_onedrive_path.txt file with the correct path."
                )
            for k, v in paths.items():
                if isinstance(v, str):
                    # Replace %OneDrive% placeholder if present
                    v = v.replace("%OneDrive%", onedrive_env)
                    paths[k] = os.path.expandvars(v)
            return paths
        except FileNotFoundError:
            raise FileNotFoundError(f"file_paths.json not found at {json_path}")
        except Exception as e:
            raise RuntimeError(f"Error loading file_paths.json: {e}")


class ConfigManager:
    def __init__(self, config_dir=None):
        self.project_root = Path(__file__).resolve().parent.parent
        from project_settings import PROJECT_ROOT
        self.config_dir = Path(config_dir) if config_dir else PROJECT_ROOT / "config"
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
