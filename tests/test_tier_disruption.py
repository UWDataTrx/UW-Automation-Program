import os
import shutil

from modules.tier_disruption import process_data


def test_process_tier_runs(tmp_path):
    # Ensure file_paths.json is available in the working directory
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
    src = os.path.abspath(os.path.join(config_dir, "file_paths.json"))
    dst = os.path.abspath("file_paths.json")
    if not os.path.exists(dst):
        shutil.copy(src, dst)
    process_data()
