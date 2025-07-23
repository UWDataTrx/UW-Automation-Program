
import os
import sys
from pathlib import Path
import unittest
from config.config_loader import ConfigLoader
# Ensure project root is in sys.path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class TestFilePaths(unittest.TestCase):
    def setUp(self):
        # Load file paths using the static method
        self.paths = ConfigLoader.load_file_paths()

    def test_all_paths_exist(self):
        missing = []
        for key, rel_path in self.paths.items():
            abs_path = os.path.join(os.getcwd(), rel_path)
            if not os.path.exists(abs_path):
                missing.append((key, abs_path))
        if missing:
            for key, path in missing:
                print(f"Missing file for key '{key}': {path}")
        self.assertEqual(len(missing), 0, f"Missing files: {missing}")

if __name__ == "__main__":
    unittest.main()
