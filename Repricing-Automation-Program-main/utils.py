import json
import logging
import os
from pathlib import Path

import pandas as pd


def load_file_paths(json_file="file_paths.json"):
    """
    Loads a JSON config file, replacing %OneDrive% with the user's OneDrive path.
    Returns a dictionary mapping keys to resolved absolute file paths.
    """
    try:
        with open(json_file, "r") as f:
            paths = json.load(f)

        # Resolve the user's OneDrive path
        onedrive_path = os.environ.get("OneDrive")
        if not onedrive_path:
            raise EnvironmentError(
                "OneDrive environment variable not found. Please ensure OneDrive is set up."
            )

        resolved_paths = {}
        for key, path in paths.items():
            if path.startswith("%OneDrive%"):
                path = path.replace("%OneDrive%", onedrive_path)
            resolved_paths[key] = str(Path(path).resolve())

        return resolved_paths

    except Exception:
        logging.exception(f"Failed to load or resolve file paths from {json_file}")
        raise


def standardize_pharmacy_ids(df):
    """
    Pads 'PHARMACYNPI' to 10 digits and 'NABP' to 7 digits in the DataFrame.

    Args:
        df (pd.DataFrame): Claims DataFrame.

    Returns:
        pd.DataFrame: Updated DataFrame with padded ID columns.
    """
    if "PHARMACYNPI" in df.columns:
        df["PHARMACYNPI"] = df["PHARMACYNPI"].astype(str).str.zfill(10)
    if "NABP" in df.columns:
        df["NABP"] = df["NABP"].astype(str).str.zfill(7)
    return df


def standardize_network_ids(network):
    """
    Pads 'pharmacy_npi' to 10 digits and 'pharmacy_nabp' to 7 digits in the network DataFrame.

    Args:
        network (pd.DataFrame): Network DataFrame.

    Returns:
        pd.DataFrame: Updated network DataFrame with padded ID columns.
    """
    if "pharmacy_npi" in network.columns:
        network["pharmacy_npi"] = network["pharmacy_npi"].astype(str).str.zfill(10)
    if "pharmacy_nabp" in network.columns:
        network["pharmacy_nabp"] = network["pharmacy_nabp"].astype(str).str.zfill(7)
    return network


def merge_with_network(df, network):
    """
    Performs a left join of df with network on ['PHARMACYNPI','NABP'] ⟷ ['pharmacy_npi','pharmacy_nabp'].

    Args:
        df (pd.DataFrame): Claims DataFrame.
        network (pd.DataFrame): Network DataFrame.

    Returns:
        pd.DataFrame: Merged DataFrame.
    """
    return df.merge(
        network,
        left_on=["PHARMACYNPI", "NABP"],
        right_on=["pharmacy_npi", "pharmacy_nabp"],
        how="left",
    )


def drop_duplicates_df(df):
    """
    Drops duplicate rows from the DataFrame.

    Args:
        df (pd.DataFrame): DataFrame to deduplicate.

    Returns:
        pd.DataFrame: Deduplicated DataFrame.
    """
    df = df.drop_duplicates()
    return df.drop_duplicates()


def clean_logic_and_tier(df, logic_col="Logic", tier_col="FormularyTier"):
    """
    Cleans 'Logic' as numeric.
    Cleans 'FormularyTier':
        - If all entries are numeric-like, coerces to numeric
        - Otherwise, strips and uppercases text for brand/generic disruptions
    """
    df[logic_col] = pd.to_numeric(df[logic_col], errors="coerce")

    # Inspect tier values
    sample = df[tier_col].dropna().astype(str).head(10)
    numeric_like = sample.str.replace(".", "", regex=False).str.isnumeric().all()

    if numeric_like:
        df[tier_col] = pd.to_numeric(df[tier_col], errors="coerce")
    else:
        df[tier_col] = df[tier_col].astype(str).str.strip().str.upper()

    return df


def filter_recent_date(df, date_col="DATEFILLED"):
    """
    Keeps only rows where date_col falls in the last 6 months (inclusive).

    Args:
        df (pd.DataFrame): DataFrame with date column.
        date_col (str): Name of the date column.

    Returns:
        pd.DataFrame: Filtered DataFrame.
    """
    latest = df[date_col].max()
    start = latest - pd.DateOffset(months=6) + pd.DateOffset(days=1)
    return df[(df[date_col] >= start) & (df[date_col] <= latest)]


def filter_logic_and_maintenance(
    df, logic_col="Logic", min_logic=5, max_logic=10, maint_col="Maint Drug?"
):
    """
    Filters rows where min_logic ≤ Logic ≤ max_logic and 'Maint Drug?' == 'Y'.

    Args:
        df (pd.DataFrame): DataFrame with logic and maintenance columns.
        logic_col (str): Name of the logic column.
        min_logic (int): Minimum logic threshold.
        max_logic (int): Maximum logic threshold.
        maint_col (str): Name of the maintenance column.

    Returns:
        pd.DataFrame: Filtered DataFrame.
    """
    return df[
        (df[logic_col] >= min_logic)
        & (df[logic_col] <= max_logic)
        & (df[maint_col] == "Y")
    ]


def filter_products_and_alternative(
    df, product_col="Product Name", alternative_col="Alternative"
):
    """
    Excludes rows where 'Product Name' contains albuterol, ventolin, epinephrine,
    or where 'Alternative' contains 'Covered' or 'Use different NDC'.

    Args:
        df (pd.DataFrame): DataFrame with product/alternative columns.
        product_col (str): Name of the product column.
        alternative_col (str): Name of the alternative column.

    Returns:
        pd.DataFrame: Filtered DataFrame.
    """
    exclude_pats = [r"\balbuterol\b", r"\bventolin\b", r"\bepinephrine\b"]
    for pat in exclude_pats:
        df = df[~df[product_col].str.contains(pat, case=False, na=False)]
    df = df[
        ~df[alternative_col]
        .astype(str)
        .str.contains(r"Covered|Use different NDC", case=False, regex=True, na=False)
    ]
    return df
