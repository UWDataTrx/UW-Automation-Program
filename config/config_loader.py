# Basic ConfigLoader implementation for config loading
import os
import json

class ConfigLoader:
    @staticmethod
    def load_file_paths():
        # Resolve project root and config path
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_dir = os.path.join(project_root, 'config')
        json_path = os.path.join(config_dir, 'file_paths.json')
        try:
            with open(json_path, 'r') as f:
                paths = json.load(f)
            # Expand environment variables in all file paths
            for k, v in paths.items():
                if isinstance(v, str):
                    paths[k] = os.path.expandvars(v)
            return paths
        except FileNotFoundError:
            raise FileNotFoundError(f"file_paths.json not found at {json_path}")
        except Exception as e:
            raise RuntimeError(f"Error loading file_paths.json: {e}")
