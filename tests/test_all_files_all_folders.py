import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent


class TestAllFilesAllFolders(unittest.TestCase):
    def test_import_and_run_main_process(self):
        errors = []
        checked_files = set()
        # Always include app.py explicitly
        app_py = PROJECT_ROOT / "app.py"
        if app_py.exists():
            checked_files.add(str(app_py.resolve()))
        # Only walk source folders: root, modules, utils, config, ui, etc.
        source_dirs = [
            PROJECT_ROOT,
            PROJECT_ROOT / "modules",
            PROJECT_ROOT / "utils",
            PROJECT_ROOT / "config",
            PROJECT_ROOT / "ui",
        ]
        for src_dir in source_dirs:
            if not src_dir.exists():
                continue
            for root, dirs, files in os.walk(src_dir):
                # Skip .venv, site-packages, and other external folders
                if any(
                    exclude in root
                    for exclude in [".venv", "site-packages", "__pycache__"]
                ):
                    continue
                for file in files:
                    if file.endswith(".py") and not file.startswith("test_"):
                        file_path = os.path.join(root, file)
                        file_path_resolved = str(Path(file_path).resolve())
                        if file_path_resolved in checked_files:
                            continue
                        checked_files.add(file_path_resolved)
                        rel_path = os.path.relpath(file_path, PROJECT_ROOT)
                        module_name = rel_path.replace(os.sep, ".")[:-3]
                        try:
                            spec = importlib.util.spec_from_file_location(
                                module_name, file_path
                            )
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                try:
                                    spec.loader.exec_module(module)
                                except SystemExit as e:
                                    errors.append(
                                        (file_path, f"SystemExit with code {e.code}")
                                    )
                                except Exception as e:
                                    errors.append((file_path, f"import error: {e}"))
                                # Try to call main() if it exists
                                if hasattr(module, "main"):
                                    with (
                                        patch("builtins.input", return_value="test"),
                                        patch("builtins.print"),
                                    ):
                                        try:
                                            module.main()
                                        except SystemExit as e:
                                            errors.append(
                                                (
                                                    file_path,
                                                    f"main() SystemExit with code {e.code}",
                                                )
                                            )
                                        except Exception as e:
                                            errors.append(
                                                (file_path, f"main() error: {e}")
                                            )
                                # Try to call process_data() if it exists
                                if hasattr(module, "process_data"):
                                    try:
                                        module.process_data()
                                    except SystemExit as e:
                                        errors.append(
                                            (
                                                file_path,
                                                f"process_data() SystemExit with code {e.code}",
                                            )
                                        )
                                    except Exception as e:
                                        errors.append(
                                            (file_path, f"process_data() error: {e}")
                                        )
                            else:
                                errors.append((file_path, "Spec or loader is None"))
                        except Exception as e:
                            errors.append((file_path, f"import error: {e}"))
        if errors:
            for file_path, error in errors:
                print(f"Error in {file_path}: {error}")
        self.assertFalse(
            errors, "Some files failed process or import. See above for details."
        )


if __name__ == "__main__":
    unittest.main()
