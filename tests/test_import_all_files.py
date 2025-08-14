import unittest
import os
from pathlib import Path
import importlib.util


class TestAllPythonFiles(unittest.TestCase):
    def test_import_all_python_files(self):
        errors = []
        for root, dirs, files in os.walk(Path(__file__).parent.parent):
            for file in files:
                if file.endswith(".py") and not file.startswith("test_"):
                    file_path = os.path.join(root, file)
                    module_name = file_path.replace(os.sep, ".")[:-3]
                    try:
                        spec = importlib.util.spec_from_file_location(
                            module_name, file_path
                        )
                        if spec is not None and spec.loader is not None:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                        else:
                            errors.append(
                                (file_path, "Could not create module spec or loader")
                            )
                    except Exception as e:
                        errors.append((file_path, str(e)))
        if errors:
            for file_path, error in errors:
                print(f"Error importing {file_path}: {error}")
        self.assertFalse(errors, "Some files failed to import. See above for details.")


if __name__ == "__main__":
    unittest.main()
