"""
Template processing module for handling Excel template operations.
Extracted from app.py to improve cohesion and reduce file size.

This module provides:
- Template backup creation
- Excel data formatting
- Column filtering for templates
- Data preparation for Excel export
"""

import pandas as pd
import shutil
import os
import sys
from pathlib import Path
import logging

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import write_shared_log, create fallback if not available
try:
    from utils.utils import write_shared_log
except ImportError:
    # Fallback function if utils.utils is not available
    def write_shared_log(script_name, message, status="INFO"):
        """Fallback logging function when utils.utils is not available"""
        print(f"[{status}] {script_name}: {message}")


class TemplateProcessor:
    """
    Handles Excel template operations with a focus on simplicity and reliability.

    This class manages template backup, data formatting, and Excel export operations
    while maintaining separation of concerns from the main application logic.
    """

    def __init__(self, app_instance):
        """Initialize with reference to the main application instance."""
        self.app = app_instance

    def create_template_backup(self, paths):
        """Create backup of template and prepare output file."""
        try:
            # Backup original template
            shutil.copy(paths["template"], paths["backup"])
            logging.info(f"Template backed up to {paths['backup']}")

            # Remove old output if it exists
            if paths["output"].exists():
                try:
                    os.remove(paths["output"])
                except PermissionError:
                    raise RuntimeError(
                        f"Cannot overwrite {paths['output']} — please close it in Excel."
                    )

            # Copy template to output location
            shutil.copy(paths["template"], paths["output"])
            write_shared_log(
                "TemplateProcessor", f"Template backup created: {paths['backup']}"
            )

        except Exception as e:
            error_msg = f"Failed to create template backup: {str(e)}"
            logging.error(error_msg)
            write_shared_log("TemplateProcessor", error_msg, "ERROR")
            raise

    def format_dataframe(self, df):
        """Format DataFrame for Excel export."""
        # Format datetime columns
        datetime_columns = df.select_dtypes(include=["datetime64"]).columns
        for col in datetime_columns:
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

        # Fill NaN values
        return df.fillna("")

    def filter_template_columns(self, df):
        """Filter columns for template pasting."""
        try:
            # Ensure 'ClientName' and 'Logic' columns exist and are in the correct order
            if "ClientName" in df.columns and "Logic" in df.columns:
                client_name_idx = df.columns.get_loc("ClientName")
                logic_idx = df.columns.get_loc("Logic")

                if client_name_idx <= logic_idx:
                    # Select columns from 'ClientName' to 'Logic' (inclusive)
                    selected_columns = df.columns[client_name_idx : logic_idx + 1]
                    logging.info(
                        f"Pasting only these columns: {selected_columns.tolist()}"
                    )
                    return df[selected_columns]
                else:
                    logging.warning(
                        "'Logic' column appears before 'ClientName'; returning full DataFrame."
                    )
                    return df
            else:
                raise ValueError(
                    "Required columns 'ClientName' or 'Logic' are missing."
                )

        except Exception as e:
            logging.warning(f"Error filtering columns: {e}. Using full DataFrame.")
            return df

    def prepare_template_data(self, processed_file):
        """Prepare data for template pasting."""
        try:
            df = pd.read_excel(processed_file)
            df = self.format_dataframe(df)

            return {"data": df.values, "nrows": df.shape[0], "ncols": df.shape[1]}
        except Exception as e:
            error_msg = f"Failed to prepare template data: {str(e)}"
            logging.error(error_msg)
            write_shared_log("TemplateProcessor", error_msg, "ERROR")
            raise

    def prepare_excel_data(self, paste_data, formulas):
        """Prepare data for Excel, preserving formulas."""
        data_to_write = []

        for i in range(paste_data["nrows"]):
            row = []
            for j in range(paste_data["ncols"]):
                if formulas[i][j] == "":
                    row.append(paste_data["data"][i][j])
                else:
                    row.append(None)
            data_to_write.append(row)

        return data_to_write

    def validate_template_requirements(self, template_path):
        """Validate that template meets requirements."""
        if not template_path:
            raise ValueError("Template file path is not set.")

        template = Path(template_path)
        if not template.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        if template.suffix != ".xlsx":
            raise ValueError("Template must be an Excel file (.xlsx)")

        return True

    def show_toast(self, message, duration=3000):
        """Show a toast notification."""
        try:
            import tkinter as tk
            from tkinter import messagebox

            toast = tk.Toplevel(self.app.root)
            toast.overrideredirect(True)
            toast.configure(bg="black")

            # Position bottom-right
            self.app.root.update_idletasks()
            screen_width = toast.winfo_screenwidth()
            screen_height = toast.winfo_screenheight()
            x = screen_width - 320
            y = screen_height - 100
            toast.geometry(f"300x50+{x}+{y}")

            label = tk.Label(
                toast, text=message, bg="black", fg="white", font=("Arial", 11)
            )
            label.pack(fill="both", expand=True)

            toast.after(duration, toast.destroy)

        except Exception as e:
            logging.warning(f"Toast notification failed: {e}")
            # Fallback to messagebox
            from tkinter import messagebox

            messagebox.showinfo("Notification", message)
