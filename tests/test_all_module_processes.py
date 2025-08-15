import importlib
import unittest
from pathlib import Path
from unittest.mock import patch

MODULES_DIR = Path(__file__).parent.parent / "modules"


class TestAllModuleProcesses(unittest.TestCase):
    def test_all_main_functions(self):
        errors = []
        for pyfile in MODULES_DIR.glob("*.py"):
            if pyfile.name == "__init__.py":
                continue
            module_name = f"modules.{pyfile.stem}"
            try:
                module = importlib.import_module(module_name)
                # Try to call main() if it exists
                if hasattr(module, "main"):
                    with (
                        patch("builtins.input", return_value="test"),
                        patch("builtins.print"),
                    ):
                        try:
                            module.main()
                        except Exception as e:
                            errors.append((module_name, f"main() error: {e}"))
                # Try to call process_data() if it exists
                if hasattr(module, "process_data"):
                    try:
                        module.process_data()
                    except Exception as e:
                        errors.append((module_name, f"process_data() error: {e}"))
            except Exception as e:
                errors.append((module_name, f"import error: {e}"))
        if errors:
            for mod, err in errors:
                print(f"Error in {mod}: {err}")
        self.assertFalse(
            errors, "Some modules failed process or import. See above for details."
        )


if __name__ == "__main__":
    unittest.main()
