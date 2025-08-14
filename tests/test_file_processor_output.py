import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.file_processor import FileProcessor
import unittest


class TestFileProcessor(unittest.TestCase):
    def test_prepare_file_paths_output(self):
        # Use a dummy template path
        template_path = "dummy_template.xlsx"
        fp = FileProcessor(app_instance=None)
        paths = fp.prepare_file_paths(template_path)
        output_path = paths["output"]
        self.assertTrue(str(output_path).endswith("_Rx Repricing_wf.xlsx"))
        # Create a dummy file at the output path
        with open(output_path, "w") as f:
            f.write("test")
        self.assertTrue(Path(output_path).exists())
        # Clean up
        Path(output_path).unlink()


if __name__ == "__main__":
    unittest.main()
