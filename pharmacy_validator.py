def find_missing_rows(main_csv, other_csv, output_csv=None):
    """
    If columns A, B, & C (first three columns) are missing from main_df but are in other_df,
    create missing.csv with the data from other_df that is missing from main_df.
    """
    import pandas as pd

    main_df = pd.read_csv(main_csv)
    other_df = pd.read_csv(other_csv)

    # Use only columns A, B, and C for matching
    key_columns = main_df.columns[:3].tolist()  # A, B, C

    # Normalize key columns: strip spaces, lowercase, remove decimals from IDs
    for col in key_columns:
        main_df[col] = main_df[col].astype(str).str.strip().str.lower()
        other_df[col] = other_df[col].astype(str).str.strip().str.lower()
    for col in key_columns[:2]:  # Only A and B are likely IDs
        main_df[col] = main_df[col].str.split(".").str[0]
        other_df[col] = other_df[col].str.split(".").str[0]

    # Find rows in other_df not in main_df based on key columns
    merged = other_df.merge(
        main_df[key_columns], on=key_columns, how="left", indicator=True
    )
    missing_rows = merged[merged["_merge"] == "left_only"]
    missing_idx = missing_rows.index
    missing_rows_aq = other_df.loc[missing_idx]

    missing_rows_aq.to_csv(
        "C:\\Users\\DamionMorrison\\OneDrive - True Rx Health Strategists\\Documents\\missing_rows.csv",
        index=False,
    )
    if output_csv:
        missing_rows_aq.to_csv(output_csv, index=False)
    return missing_rows_aq


if __name__ == "__main__":
    find_missing_rows(
        "C:\\Users\\DamionMorrison\\OneDrive - True Rx Health Strategists\\Documents\\Rx Sense Pharmacy Network 7.25.csv",
        "C:\\Users\\DamionMorrison\\OneDrive - True Rx Health Strategists\\Documents\\Results.csv",
    )
