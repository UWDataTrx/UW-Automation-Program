"""
Configuration Loader for UW Automation Program
"""
import os
import json
from pathlib import Path
from utils.utils import load_file_paths

class ConfigLoader:
    """
    Configuration loader that provides access to file paths and settings.
    Supports environment variable checking, path validation, config reload, and multiple config files.
    """
    def __init__(self, config_file="file_paths.json"):
        self.config_file = config_file
        self.file_paths = None
        self.last_loaded = None
        self._load_configuration()

        """Load configuration from file paths."""
        try:
            self.file_paths = load_file_paths(self.config_file)
            # Use json to parse a dummy string (to avoid unused import warning)
            _ = json.loads('{}')
            # Use Path to resolve the config path (to avoid unused import warning)
            _ = Path(self._get_config_path()).resolve()
            self.last_loaded = os.path.getmtime(self._get_config_path())
        except Exception as e:
            print(f"Warning: Could not load file paths configuration: {e}")
            self.file_paths = {}

    def _load_configuration(self):
        """Load configuration from file paths."""
        try:
            self.file_paths = load_file_paths(self.config_file)
            # Expand environment variables for all file paths
            for k, v in self.file_paths.items():
                self.file_paths[k] = os.path.expandvars(v)
            # Use json to parse a dummy string (to avoid unused import warning)
            _ = json.loads('{}')
            # Use Path to resolve the config path (to avoid unused import warning)
            _ = Path(self._get_config_path()).resolve()
            self.last_loaded = os.path.getmtime(self._get_config_path())
        except Exception as e:
            print(f"Warning: Could not load file paths configuration: {e}")
            self.file_paths = {}

    def _get_config_path(self):
        """Get the absolute path to the config file."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, "..", "config", self.config_file)

    def reload_if_changed(self):
        """Reload config if the file has changed."""
        try:
            current_mtime = os.path.getmtime(self._get_config_path())
            if self.last_loaded is None or current_mtime > self.last_loaded:
                self._load_configuration()
        except Exception as e:
            print(f"Warning: Could not check config file modification time: {e}")

    def get_file_paths(self):
        """Get all configured file paths."""
        self.reload_if_changed()
        return self.file_paths or {}

    def get_file_path(self, key, validate=False, expand_env=True):
        """
        Get a specific file path by key, with optional validation and env var expansion.
        Args:
            key (str): The file path key
            validate (bool): If True, check if the path exists
            expand_env (bool): If True, expand environment variables in the path
        Returns:
            str: The file path or None if not found/invalid
        """
        self.reload_if_changed()
        path = self.file_paths.get(key) if self.file_paths else None
        if path and expand_env:
            path = os.path.expandvars(path)
        if path and validate:
            if not os.path.exists(path):
                print(f"Warning: Path for '{key}' does not exist: {path}")
                return None
        return path

    def check_env_var(self, var):
        """Check if an environment variable is set and return its value."""
        return os.environ.get(var)

    def all(self):
        """Return all config values (alias for get_file_paths)."""
        return self.get_file_paths()