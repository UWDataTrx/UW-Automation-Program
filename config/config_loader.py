# Basic ConfigLoader implementation for config loading
import os
import json

class ConfigLoader:
    @staticmethod
    def load_file_paths():
        config_dir = os.path.dirname(__file__)
        json_path = os.path.join(config_dir, 'file_paths.json')
        try:
            with open(json_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"file_paths.json not found at {json_path}")
        except Exception as e:
            raise RuntimeError(f"Error loading file_paths.json: {e}")
