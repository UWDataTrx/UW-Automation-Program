"""
Create a test merged_file.xlsx for testing the RowID error analyzer.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def create_test_merged_file():
    """Create a test merged file that might have RowID issues."""

    # Create sample data
    num_rows = 1000

    # Generate test data
    data = {
        "SOURCERECORDID": [f"REC{str(i).zfill(6)}" for i in range(num_rows)],
        "NDC": [
            f"{np.random.randint(10000, 99999)}-{np.random.randint(100, 999)}-{np.random.randint(10, 99)}"
            for _ in range(num_rows)
        ],
        "MemberID": [
            f"MBR{np.random.randint(100000, 999999)}" for _ in range(num_rows)
        ],
        "DATEFILLED": [
            datetime.now() - timedelta(days=np.random.randint(0, 365))
            for _ in range(num_rows)
        ],
        "QUANTITY": np.random.randint(1, 90, num_rows),
        "DAYSUPPLY": np.random.randint(30, 90, num_rows),
        "Drug Name": [f"Drug_{chr(65 + (i % 26))}" for i in range(num_rows)],
        "Pharmacy Name": [f"Pharmacy_{(i % 10) + 1}" for i in range(num_rows)],
        "Total AWP (Historical)": np.round(np.random.uniform(10.0, 500.0, num_rows), 2),
        "FormularyTier": np.random.choice(["1", "2", "3", "B", "G"], num_rows),
        "PHARMACYNPI": [
            f"{np.random.randint(1000000, 9999999)}" for _ in range(num_rows)
        ],
        "NABP": [f"{np.random.randint(1000000, 9999999)}" for _ in range(num_rows)],
        "Rxs": np.random.randint(1, 5, num_rows),
    }

    # Create DataFrame first
    df = pd.DataFrame(data)

    # Introduce some potential issues after DataFrame creation
    # 1. Some null values in critical columns
    df.loc[10:14, "DATEFILLED"] = None
    df.loc[20:24, "SOURCERECORDID"] = None

    # 2. Duplicate some records
    df.loc[100:104, "SOURCERECORDID"] = "DUP001"

    # 3. Add an existing RowID column with issues
    df["RowID"] = np.arange(num_rows)
    # Make some RowID values problematic
    df.loc[50:54, "RowID"] = None

    # Save to Excel
    df.to_excel("merged_file.xlsx", index=False)
    print(
        f"Created test merged_file.xlsx with {num_rows} rows and {len(df.columns)} columns"
    )
    print("Introduced issues:")
    print("- Null values in DATEFILLED and SOURCERECORDID")
    print("- Duplicate SOURCERECORDID values")
    print("- Existing RowID column with null values")

    return df


if __name__ == "__main__":
    create_test_merged_file()
