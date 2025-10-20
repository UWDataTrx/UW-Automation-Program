# Replace the integer keys with the actual column names as strings, e.g.:
# df.to_parquet('bob.parquet')
import os

import pandas as pd

# converts from sql to BOB to run. Keep results naming convention and save in Python folder


input_file = "C:\\Users\\DamionMorrison\\OneDrive - True Rx Health Strategists\\True Community - Data Analyst\\UW Python Program\\UW-Automation-Program\\B.o.B\\templates\\Results 4.csv"
output_file = "bob.parquet"

dtype_dict = {
    "column_name_26": "str",
    "column_name_32": "str",
    "column_name_47": "str",
    "column_name_55": "str",
    "column_name_57": "str",
    "column_name_90": "str",
    "column_name_97": "str",
}

if not os.path.exists(input_file):
    print(f"Error: Input file '{input_file}' does not exist.")
else:
    try:
        df = pd.read_csv(input_file, dtype=dtype_dict)  # type: ignore
    except ValueError as e:
        print(f"Error reading CSV with dtype: {e}\nTrying without dtype...")
        try:
            df = pd.read_csv(input_file)
        except Exception as e2:
            print(f"Failed to read CSV: {e2}")
            df = None
    except Exception as e:
        print(f"Error reading CSV: {e}")
        df = None

    if df is not None:
        try:
            df.to_parquet(output_file)
            print(f"Done. Saved as {output_file}")
        except Exception as e:
            print(f"Error saving to Parquet: {e}")
