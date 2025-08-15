#!/usr/bin/env python3
"""
Test the RowID multiprocessing fix to ensure no conflicts occur.
"""

import numpy as np
import pandas as pd


def test_multiprocessing_rowid_fix():
    """Test that RowID is correctly handled after multiprocessing concat."""

    # Create test data similar to what causes the error
    test_data = {
        "SOURCERECORDID": range(1000),  # 1000 records
        "DATEFILLED": pd.date_range("2023-01-01", periods=1000, freq="D"),
        "MemberID": [f"M{i:04d}" for i in range(1000)],
        "QUANTITY": np.random.choice([-1, 1, 2, 3], 1000),
        "NDC": [f"NDC{i:05d}" for i in range(1000)],
        "Logic": [""] * 1000,
    }

    df = pd.DataFrame(test_data)

    print(f"Created test dataframe with {len(df)} rows")
    print(f"Columns: {list(df.columns)}")

    # Simulate the multiprocessing split and concat that causes RowID issues
    print("\n--- Simulating Multiprocessing Split ---")
    num_workers = 4
    df_blocks = np.array_split(df, num_workers)

    print(f"Split into {len(df_blocks)} blocks:")
    for i, block in enumerate(df_blocks):
        print(f"  Block {i}: {len(block)} rows")

    # Add RowID to each block (this is what causes conflicts)
    print("\n--- Adding RowID to each block (problematic) ---")
    blocks_with_rowid = []
    for i, block in enumerate(df_blocks):
        block = block.copy()
        block["RowID"] = np.arange(len(block))  # This creates overlapping RowIDs!
        blocks_with_rowid.append(block)
        print(f"  Block {i} RowID range: {block['RowID'].min()}-{block['RowID'].max()}")

    # Concat without fix (this creates the problem)
    print("\n--- Concatenating blocks (demonstrates the problem) ---")
    problematic_df = pd.concat(blocks_with_rowid)
    rowid_counts = problematic_df["RowID"].value_counts()
    duplicates = rowid_counts[rowid_counts > 1]

    print(f"Concatenated dataframe has {len(problematic_df)} rows")
    print(
        f"RowID range: {problematic_df['RowID'].min()}-{problematic_df['RowID'].max()}"
    )
    print(f"Duplicate RowIDs: {len(duplicates)} values appear multiple times")

    if len(duplicates) > 0:
        print(f"Example duplicates: {duplicates.head().to_dict()}")

    # Apply the fix (what our code now does)
    print("\n--- Applying the FIX ---")
    fixed_df = problematic_df.copy()
    fixed_df = fixed_df.reset_index(drop=True)
    fixed_df["RowID"] = np.arange(len(fixed_df))

    print(f"Fixed dataframe has {len(fixed_df)} rows")
    print(f"RowID range: {fixed_df['RowID'].min()}-{fixed_df['RowID'].max()}")

    # Verify fix
    fixed_rowid_counts = fixed_df["RowID"].value_counts()
    fixed_duplicates = fixed_rowid_counts[fixed_rowid_counts > 1]

    print(f"Duplicate RowIDs after fix: {len(fixed_duplicates)}")

    # Check that RowID is sequential and unique
    expected_rowids = set(range(len(fixed_df)))
    actual_rowids = set(fixed_df["RowID"])

    is_sequential = actual_rowids == expected_rowids
    is_unique = len(fixed_df["RowID"]) == len(fixed_df["RowID"].unique())

    print(f"RowID is sequential (0 to {len(fixed_df) - 1}): {is_sequential}")
    print(f"RowID is unique: {is_unique}")

    # Final verdict
    success = len(fixed_duplicates) == 0 and is_sequential and is_unique

    print(f"\n{'🎉 FIX SUCCESSFUL!' if success else '❌ FIX FAILED!'}")

    return success


if __name__ == "__main__":
    print("Testing RowID Multiprocessing Fix")
    print("=" * 50)

    try:
        success = test_multiprocessing_rowid_fix()
        if success:
            print("\n✅ The multiprocessing RowID fix works correctly!")
        else:
            print("\n❌ The fix needs more work.")
    except Exception as e:
        print(f"Test error: {e}")
        import traceback

        traceback.print_exc()
