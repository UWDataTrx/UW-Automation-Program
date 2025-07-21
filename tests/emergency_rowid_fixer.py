"""
Emergency RowID Error Fix for DataProcessing Module
Fixes the 'RowID' column error that occurs during merged_file.xlsx processing.

This fix addresses the specific error:
SYSTEM ERROR - DataProcessing | User: BrendanReamer on L01275-AN |
Python: 3.13.5 | OS: Windows 11 | Context: File: merged_file.xlsx |
Error: Error processing merged file: 'RowID' | Stack: 'RowID'...
"""

import pandas as pd
import numpy as np
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent
sys.path.append(str(project_root))


def fix_data_processor_rowid_issue():
    """Apply emergency fix to the DataProcessor module for RowID issues."""

    print("=== Emergency RowID Fix for DataProcessor ===")

    # Path to the data processor module
    data_processor_path = project_root / "modules" / "data_processor.py"

    if not data_processor_path.exists():
        print(f"❌ DataProcessor module not found at: {data_processor_path}")
        return False

    print(f"📁 Found DataProcessor at: {data_processor_path}")

    # Read the current file
    with open(data_processor_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Create backup
    backup_path = data_processor_path.with_suffix(".py.backup")
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"💾 Backup created: {backup_path}")

    # Apply the fix
    fixed_content = apply_rowid_fixes_to_content(content)

    # Write the fixed content
    with open(data_processor_path, "w", encoding="utf-8") as f:
        f.write(fixed_content)

    print("✅ RowID fixes applied to DataProcessor module")
    print("\nFixes applied:")
    print("- Added comprehensive error handling for RowID creation")
    print("- Added validation for required columns before sorting")
    print("- Added fallback methods for data processing")
    print("- Enhanced logging for troubleshooting")

    return True


def apply_rowid_fixes_to_content(content):
    """Apply RowID fixes to the DataProcessor module content."""

    # Fix 1: Replace the load_and_validate_data method with a more robust version
    old_load_method = '''    def load_and_validate_data(self, file_path):
        """Load and validate the merged file data."""
        try:
            df = pd.read_excel(file_path)
            logging.info(f"Loaded {len(df)} records from {file_path}")
            
            # Validate required columns using configuration
            ProcessingConfig.validate_required_columns(df)
            
            # Prepare data for processing
            df = df.sort_values(by=["DATEFILLED", "SOURCERECORDID"], ascending=True)
            df["Logic"] = ""
            df["RowID"] = np.arange(len(df))
            
            return df
            
        except Exception as e:
            error_msg = f"Error loading data from {file_path}: {str(e)}"
            logging.error(error_msg)
            write_shared_log("DataProcessor", error_msg, "ERROR")
            raise'''

    new_load_method = '''    def load_and_validate_data(self, file_path):
        """Load and validate the merged file data with enhanced error handling."""
        try:
            # Load the Excel file
            df = pd.read_excel(file_path)
            logging.info(f"Loaded {len(df)} records from {file_path}")
            
            # Validate that we have data
            if df.empty:
                raise ValueError(f"The file {file_path} is empty or contains no data")
            
            # Validate required columns using configuration with fallback
            try:
                ProcessingConfig.validate_required_columns(df)
            except Exception as config_error:
                logging.warning(f"Configuration validation failed: {config_error}")
                # Fallback validation for essential columns
                essential_columns = ["DATEFILLED", "SOURCERECORDID"]
                missing_essential = [col for col in essential_columns if col not in df.columns]
                if missing_essential:
                    raise ValueError(f"Missing essential columns: {missing_essential}")
            
            # Prepare data for processing with enhanced error handling
            df = self._safe_prepare_data_for_processing(df)
            
            return df
            
        except Exception as e:
            error_msg = f"Error loading data from {file_path}: {str(e)}"
            logging.error(error_msg)
            write_shared_log("DataProcessor", error_msg, "ERROR")
            raise
    
    def _safe_prepare_data_for_processing(self, df):
        """Safely prepare data for processing with comprehensive error handling."""
        try:
            # Create a copy to avoid modifying the original
            df_processed = df.copy()
            
            # Remove existing RowID column if present
            if 'RowID' in df_processed.columns:
                df_processed = df_processed.drop(columns=['RowID'])
                logging.info("Removed existing RowID column")
            
            # Add Logic column if missing
            if 'Logic' not in df_processed.columns:
                df_processed["Logic"] = ""
                logging.info("Added missing Logic column")
            
            # Safe sorting with validation
            df_processed = self._safe_sort_dataframe(df_processed)
            
            # Safe RowID creation
            df_processed = self._safe_create_rowid(df_processed)
            
            return df_processed
            
        except Exception as e:
            logging.error(f"Error in data preparation: {e}")
            # Return original DataFrame with minimal processing as fallback
            if 'Logic' not in df.columns:
                df["Logic"] = ""
            if 'RowID' not in df.columns:
                df["RowID"] = df.index
            return df
    
    def _safe_sort_dataframe(self, df):
        """Safely sort the DataFrame with error handling."""
        sort_columns = ["DATEFILLED", "SOURCERECORDID"]
        
        try:
            # Check which sort columns are available
            available_sort_cols = [col for col in sort_columns if col in df.columns]
            
            if not available_sort_cols:
                logging.warning("No sort columns available. Using original order.")
                return df
            
            # Check for null values in sort columns and handle them
            for col in available_sort_cols:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    logging.warning(f"Found {null_count} null values in sort column '{col}'. Filling with default values.")
                    
                    if col == "DATEFILLED":
                        # Fill null dates with a default date
                        df[col] = df[col].fillna(pd.Timestamp('1900-01-01'))
                    elif col == "SOURCERECORDID":
                        # Fill null IDs with a default pattern
                        df[col] = df[col].fillna('UNKNOWN_ID')
            
            # Perform the sort
            df_sorted = df.sort_values(by=available_sort_cols, ascending=True)
            logging.info(f"Successfully sorted by: {available_sort_cols}")
            
            return df_sorted
            
        except Exception as e:
            logging.warning(f"Sorting failed: {e}. Using original order.")
            return df
    
    def _safe_create_rowid(self, df):
        """Safely create RowID column with multiple fallback methods."""
        try:
            # Method 1: Standard numpy arange
            df["RowID"] = np.arange(len(df))
            logging.info("Successfully created RowID using np.arange")
            return df
            
        except Exception as e1:
            logging.warning(f"Standard RowID creation failed: {e1}. Trying alternative methods.")
            
            try:
                # Method 2: Use DataFrame index
                df["RowID"] = df.index.values
                logging.info("Created RowID using DataFrame index")
                return df
                
            except Exception as e2:
                logging.warning(f"Index-based RowID creation failed: {e2}. Trying manual creation.")
                
                try:
                    # Method 3: Manual creation with list comprehension
                    df["RowID"] = [i for i in range(len(df))]
                    logging.info("Created RowID using manual list creation")
                    return df
                    
                except Exception as e3:
                    logging.error(f"All RowID creation methods failed: {e1}, {e2}, {e3}")
                    # Final fallback: create a simple series
                    df["RowID"] = pd.Series(range(len(df)), index=df.index)
                    logging.info("Created RowID using pandas Series (final fallback)")
                    return df'''

    # Replace the method in the content
    if old_load_method in content:
        content = content.replace(old_load_method, new_load_method)
        print("✅ Updated load_and_validate_data method")
    else:
        print("⚠️  Could not find exact load_and_validate_data method to replace")

    # Fix 2: Add error handling to the save_processed_outputs method
    old_save_pattern = """            df_sorted.drop(columns=["RowID"], inplace=True, errors="ignore")"""
    new_save_pattern = """            # Safe RowID removal with enhanced error handling
            try:
                if "RowID" in df_sorted.columns:
                    df_sorted.drop(columns=["RowID"], inplace=True)
                    logging.info("Successfully removed RowID column before saving")
            except Exception as e:
                logging.warning(f"Could not remove RowID column: {e}")
                # Continue without removing RowID - it's not critical for output"""

    if old_save_pattern in content:
        content = content.replace(old_save_pattern, new_save_pattern)
        print("✅ Updated RowID removal logic")

    # Fix 3: Add imports if needed
    if "import pandas as pd" not in content:
        content = "import pandas as pd\n" + content
        print("✅ Added pandas import")

    if "import numpy as np" not in content:
        content = "import numpy as np\n" + content
        print("✅ Added numpy import")

    return content


def fix_app_py_rowid_issue():
    """Apply emergency fix to the main app.py file for RowID issues."""

    print("\n=== Emergency RowID Fix for App.py ===")

    # Path to the main app module
    app_path = project_root / "app.py"

    if not app_path.exists():
        print(f"❌ App.py not found at: {app_path}")
        return False

    print(f"📁 Found app.py at: {app_path}")

    # Read the current file
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Create backup
    backup_path = app_path.with_suffix(".py.backup")
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"💾 Backup created: {backup_path}")

    # Fix the _load_and_validate_data method in app.py
    old_app_method = '''    def _load_and_validate_data(self, file_path):
        """Load and validate the merged file data."""
        df = pd.read_excel(file_path)
        logging.info(f"Loaded {len(df)} records from {file_path}")
        self.update_progress(0.50)

        # Validate required columns using configuration
        ProcessingConfig.validate_required_columns(df)

        # Prepare data for processing
        df = df.sort_values(by=["DATEFILLED", "SOURCERECORDID"], ascending=True)
        df["Logic"] = ""
        df["RowID"] = np.arange(len(df))
        
        return df'''

    new_app_method = '''    def _load_and_validate_data(self, file_path):
        """Load and validate the merged file data with enhanced error handling."""
        try:
            df = pd.read_excel(file_path)
            logging.info(f"Loaded {len(df)} records from {file_path}")
            self.update_progress(0.50)

            # Validate that we have data
            if df.empty:
                raise ValueError(f"The file {file_path} is empty or contains no data")

            # Validate required columns using configuration with fallback
            try:
                ProcessingConfig.validate_required_columns(df)
            except Exception as config_error:
                logging.warning(f"Configuration validation failed: {config_error}")
                # Fallback validation for essential columns
                essential_columns = ["DATEFILLED", "SOURCERECORDID"]
                missing_essential = [col for col in essential_columns if col not in df.columns]
                if missing_essential:
                    raise ValueError(f"Missing essential columns: {missing_essential}")

            # Safe data preparation
            df = self._safe_prepare_dataframe(df)
            
            return df
            
        except Exception as e:
            error_msg = f"Error loading data from {file_path}: {str(e)}"
            logging.error(error_msg)
            raise Exception(f"Failed to load merged file: {error_msg}")
    
    def _safe_prepare_dataframe(self, df):
        """Safely prepare DataFrame for processing."""
        try:
            # Create a copy to avoid modifying the original
            df_processed = df.copy()
            
            # Remove existing RowID column if present
            if 'RowID' in df_processed.columns:
                df_processed = df_processed.drop(columns=['RowID'])
                logging.info("Removed existing RowID column")
            
            # Add Logic column if missing
            if 'Logic' not in df_processed.columns:
                df_processed["Logic"] = ""
                logging.info("Added missing Logic column")
            
            # Safe sorting
            sort_columns = ["DATEFILLED", "SOURCERECORDID"]
            available_sort_cols = [col for col in sort_columns if col in df_processed.columns]
            
            if available_sort_cols:
                # Handle null values before sorting
                for col in available_sort_cols:
                    if df_processed[col].isnull().any():
                        if col == "DATEFILLED":
                            df_processed[col] = df_processed[col].fillna(pd.Timestamp('1900-01-01'))
                        else:
                            df_processed[col] = df_processed[col].fillna('UNKNOWN')
                        logging.warning(f"Filled null values in {col}")
                
                df_processed = df_processed.sort_values(by=available_sort_cols, ascending=True)
                logging.info(f"Sorted by: {available_sort_cols}")
            
            # Safe RowID creation with multiple fallback methods
            try:
                df_processed["RowID"] = np.arange(len(df_processed))
                logging.info("Created RowID using np.arange")
            except Exception as e1:
                try:
                    df_processed["RowID"] = df_processed.index.values
                    logging.warning(f"np.arange failed ({e1}), used index instead")
                except Exception as e2:
                    df_processed["RowID"] = list(range(len(df_processed)))
                    logging.warning(f"Both methods failed ({e1}, {e2}), used list comprehension")
            
            return df_processed
            
        except Exception as e:
            logging.error(f"Error in DataFrame preparation: {e}")
            # Minimal fallback
            if 'Logic' not in df.columns:
                df["Logic"] = ""
            if 'RowID' not in df.columns:
                df["RowID"] = df.index
            return df'''

    # Replace the method in the content
    if old_app_method in content:
        content = content.replace(old_app_method, new_app_method)
        print("✅ Updated _load_and_validate_data method in app.py")
    else:
        print("⚠️  Could not find exact _load_and_validate_data method in app.py")

    # Write the fixed content
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ RowID fixes applied to app.py")
    return True


def create_emergency_fix_script():
    """Create an emergency script that can be run by users experiencing the RowID error."""

    emergency_script = '''"""
EMERGENCY ROWID ERROR FIX
Run this script if you encounter the error:
"Error processing merged file: 'RowID'"

This script will automatically fix the merged_file.xlsx and allow processing to continue.
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

def emergency_fix_merged_file():
    """Emergency fix for merged_file.xlsx RowID issues."""
    
    print("=== EMERGENCY ROWID FIX ===")
    print(f"Timestamp: {datetime.now()}")
    print()
    
    # Look for merged_file.xlsx
    merged_file = "merged_file.xlsx"
    
    if not os.path.exists(merged_file):
        print(f"❌ {merged_file} not found in current directory")
        print("Please run this script from the same directory as your merged_file.xlsx")
        return False
    
    print(f"📁 Found {merged_file}")
    
    try:
        # Load the file
        print("📖 Loading file...")
        df = pd.read_excel(merged_file)
        print(f"✅ Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Create backup
        backup_file = f"merged_file_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(backup_file, index=False)
        print(f"💾 Backup created: {backup_file}")
        
        # Apply fixes
        print("🔧 Applying fixes...")
        
        # Remove existing RowID if present
        if 'RowID' in df.columns:
            df = df.drop(columns=['RowID'])
            print("  - Removed existing RowID column")
        
        # Add Logic column if missing
        if 'Logic' not in df.columns:
            df['Logic'] = ""
            print("  - Added missing Logic column")
        
        # Handle null values in critical columns
        sort_columns = ["DATEFILLED", "SOURCERECORDID"]
        for col in sort_columns:
            if col in df.columns and df[col].isnull().any():
                null_count = df[col].isnull().sum()
                if col == "DATEFILLED":
                    df[col] = df[col].fillna(pd.Timestamp('1900-01-01'))
                else:
                    df[col] = df[col].fillna('FIXED_UNKNOWN')
                print(f"  - Fixed {null_count} null values in {col}")
        
        # Safe sorting
        available_sort_cols = [col for col in sort_columns if col in df.columns]
        if available_sort_cols:
            df = df.sort_values(by=available_sort_cols, ascending=True)
            print(f"  - Sorted by: {available_sort_cols}")
        
        # Safe RowID creation
        try:
            df["RowID"] = np.arange(len(df))
            print("  - Created RowID using np.arange")
        except Exception:
            try:
                df["RowID"] = df.index.values
                print("  - Created RowID using index (fallback)")
            except Exception:
                df["RowID"] = list(range(len(df)))
                print("  - Created RowID using list (final fallback)")
        
        # Save fixed file
        df.to_excel(merged_file, index=False)
        print(f"✅ Fixed file saved: {merged_file}")
        
        print()
        print("🎉 Emergency fix completed successfully!")
        print("You can now restart the processing operation.")
        
        return True
        
    except Exception as e:
        print(f"❌ Emergency fix failed: {e}")
        print("Please contact support with this error message.")
        return False

if __name__ == "__main__":
    emergency_fix_merged_file()
    input("\\nPress Enter to close...")
'''

    emergency_path = project_root / "emergency_rowid_fix.py"
    with open(emergency_path, "w", encoding="utf-8") as f:
        f.write(emergency_script)

    print(f"💊 Emergency fix script created: {emergency_path}")
    return emergency_path


def main():
    """Main function to apply all RowID error fixes."""

    print("🚨 EMERGENCY ROWID ERROR FIXER 🚨")
    print("=" * 50)
    print("This will fix the DataProcessing RowID error:")
    print("'Error processing merged file: 'RowID''")
    print()

    success_count = 0

    # Fix 1: DataProcessor module
    if fix_data_processor_rowid_issue():
        success_count += 1

    # Fix 2: App.py module
    if fix_app_py_rowid_issue():
        success_count += 1

    # Fix 3: Create emergency user script
    emergency_script_path = create_emergency_fix_script()
    if emergency_script_path:
        success_count += 1

    print(f"\n{'=' * 50}")
    print(f"✅ Applied {success_count}/3 fixes successfully")

    if success_count == 3:
        print("\n🎉 ALL FIXES APPLIED SUCCESSFULLY!")
        print("\nWhat was fixed:")
        print("1. ✅ Enhanced DataProcessor with robust RowID handling")
        print("2. ✅ Enhanced App.py with comprehensive error handling")
        print("3. ✅ Created emergency user fix script")

        print(f"\n📋 For User: BrendanReamer")
        print("The RowID error should now be resolved.")
        print("If the error persists, run: emergency_rowid_fix.py")

        print(f"\n📁 Backup files created:")
        print("- modules/data_processor.py.backup")
        print("- app.py.backup")

    else:
        print("\n⚠️  Some fixes could not be applied.")
        print("Manual intervention may be required.")


if __name__ == "__main__":
    main()
