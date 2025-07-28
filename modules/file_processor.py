import pandas as pd
import sys
import pathlib
from pathlib import Path

# Ensure project root is in sys.path before importing other modules
project_root = pathlib.Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from tkinter import messagebox  # noqa: E402

try:
    from config.app_config import ProcessingConfig, AppConstants
    from utils.utils import write_audit_log
except ImportError:
    # Fallback if imports are not available
    ProcessingConfig = None
    AppConstants = None

    def write_audit_log(script_name, message, status="INFO"):
        """Fallback logging function when utils.utils is not available"""
        print(f"[{status}] {script_name}: {message}")


class FileProcessor:
    """Handles file operations and validation."""

    def __init__(self, app_instance):
        self.app = app_instance

    def check_template(self, file_path):
        """Check if template file exists and is valid."""
        return Path(file_path).exists() and Path(file_path).suffix == ".xlsx"

    def import_file(self, file_type="File"):
        """Import and validate a file."""
        filetypes = (
            ProcessingConfig.FILE_TYPES
            if ProcessingConfig is not None
            else [("All Files", "*.*")]
        )
        file_path = self.app.ui_factory.create_file_dialog(
            title=f"Select {file_type}", filetypes=filetypes
        )

        if not file_path:
            return None

        try:
            # Validate file exists
            if not Path(file_path).exists():
                messagebox.showerror("Error", f"{file_type} not found.")
                return None

            # Load and validate the file
            df = (
                pd.read_csv(file_path)
                if file_path.endswith(".csv")
                else pd.read_excel(file_path)
            )

            # Log the import
            write_audit_log(
                "FileProcessor", f"{file_type} imported successfully: {file_path}"
            )

            return file_path, df

        except Exception as e:
            error_msg = f"Error importing {file_type}: {str(e)}"
            messagebox.showerror("Error", error_msg)
            write_audit_log("FileProcessor", error_msg, "ERROR")
            return None

    def validate_file_structure(self, df, required_columns=None):
        """Validate that the file has the required structure."""
        if ProcessingConfig is None:
            messagebox.showerror(
                "Validation Error", "ProcessingConfig is not available."
            )
            return False

        if required_columns is None:
            required_columns = ProcessingConfig.REQUIRED_COLUMNS

        try:
            ProcessingConfig.validate_required_columns(df)
            return True
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
            write_audit_log("FileProcessor", f"Validation Error: {str(e)}", "ERROR")
            return False

    def prepare_file_paths(self, template_path, opportunity_name=None):
        """Prepare file paths for template operations."""
        if not template_path:
            raise ValueError("Template file path is not set.")

        if AppConstants is None:
            raise ValueError("AppConstants is not available.")

        template = Path(template_path)
        backup_name = template.stem + AppConstants.BACKUP_SUFFIX

        # Use opportunity name in output filename if provided
        if opportunity_name:
            output_name = f"{opportunity_name}_Rx Repricing_wf.xlsx"
        else:
            output_name = AppConstants.UPDATED_TEMPLATE_NAME

        return {
            "template": template,
            "backup": Path.cwd() / backup_name,
            "output": Path.cwd() / output_name,
        }
