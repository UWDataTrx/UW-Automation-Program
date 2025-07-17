"""
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
        backup_file = (
            f"merged_file_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        df.to_excel(backup_file, index=False)
        print(f"💾 Backup created: {backup_file}")

        # Apply fixes
        print("🔧 Applying fixes...")

        # Remove existing RowID if present
        if "RowID" in df.columns:
            df = df.drop(columns=["RowID"])
            print("  - Removed existing RowID column")

        # Add Logic column if missing
        if "Logic" not in df.columns:
            df["Logic"] = ""
            print("  - Added missing Logic column")

        # Handle null values in critical columns
        sort_columns = ["DATEFILLED", "SOURCERECORDID"]
        for col in sort_columns:
            if col in df.columns and df[col].isnull().any():
                null_count = df[col].isnull().sum()
                if col == "DATEFILLED":
                    df[col] = df[col].fillna(pd.Timestamp("1900-01-01"))
                else:
                    df[col] = df[col].fillna("FIXED_UNKNOWN")
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
    input("\nPress Enter to close...")
