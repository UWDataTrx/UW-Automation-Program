import unittest
from pathlib import Path


class TestDirectoryStructure(unittest.TestCase):
    def test_modules_folder_exists(self):
        self.assertTrue(Path("modules").exists(), "modules folder does not exist")

    def test_config_folder_exists(self):
        self.assertTrue(Path("config").exists(), "config folder does not exist")

    def test_utils_folder_exists(self):
        self.assertTrue(Path("utils").exists(), "utils folder does not exist")

    def test_main_files_exist(self):
        for fname in ["app.py", "merge.py", "bg_disruption.py", "tier_disruption.py"]:
            self.assertTrue(Path(fname).exists(), f"{fname} does not exist")

    def test_tests_folder_exists(self):
        self.assertTrue(Path("tests").exists(), "tests folder does not exist")


if __name__ == "__main__":
    unittest.main()
