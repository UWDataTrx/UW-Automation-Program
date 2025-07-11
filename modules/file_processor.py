"""
File processing module for handling file operations and validation.
Extracted from app.py to improve cohesion and reduce file size.
"""

import pandas as pd
from pathlib import Path
import os
import sys
from tkinter import messagebox

from config.app_config import ProcessingConfig, AppConstants
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import write_shared_log


class FileProcessor:
    """Handles file operations and validation."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        
    def check_template(self, file_path):
        """Check if template file exists and is valid."""
        return Path(file_path).exists() and Path(file_path).suffix == '.xlsx'
    
    def import_file(self, file_type="File"):
        """Import and validate a file."""
        file_path = self.app.ui_factory.create_file_dialog(
            title=f"Select {file_type}",
            filetypes=ProcessingConfig.FILE_TYPES
        )
        
        if not file_path:
            return None
            
        try:
            # Validate file exists
            if not Path(file_path).exists():
                messagebox.showerror("Error", f"{file_type} not found.")
                return None
                
            # Load and validate the file
            df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
            
            # Log the import
            write_shared_log("FileProcessor", f"{file_type} imported successfully: {file_path}")
            
            return file_path, df
            
        except Exception as e:
            error_msg = f"Error importing {file_type}: {str(e)}"
            messagebox.showerror("Error", error_msg)
            write_shared_log("FileProcessor", error_msg, "ERROR")
            return None
    
    def validate_file_structure(self, df, required_columns=None):
        """Validate that the file has the required structure."""
        if required_columns is None:
            required_columns = ProcessingConfig.REQUIRED_COLUMNS
            
        try:
            ProcessingConfig.validate_required_columns(df)
            return True
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
            return False
    
    def prepare_file_paths(self, template_path, opportunity_name=None):
        """Prepare file paths for template operations."""
        if not template_path:
            raise ValueError("Template file path is not set.")
            
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
            "output": Path.cwd() / output_name
        }
    
    def safe_file_operation(self, operation, *args, **kwargs):
        """Safely perform file operations with error handling."""
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            error_msg = f"File operation failed: {str(e)}"
            messagebox.showerror("File Error", error_msg)
            write_shared_log("FileProcessor", error_msg, "ERROR")
            return None
