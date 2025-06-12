# utils.py
import pandas as pd
import json
import logging

def load_file_paths(json_file='file_paths.json'):
    """
    Loads a JSON file mapping named keys to file paths.

    Args:
        json_file (str): Path to the JSON configuration file.

    Returns:
        dict: Mapping of keys to file paths.
    """
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception:
        logging.exception(f"Failed to load file paths from {json_file}")
        raise

def standardize_pharmacy_ids(df):
    """
    Pads 'PHARMACYNPI' to 10 digits and 'NABP' to 7 digits in the DataFrame.

    Args:
        df (pd.DataFrame): Claims DataFrame.

    Returns:
        pd.DataFrame: Updated DataFrame with padded ID columns.
    """
    if 'PHARMACYNPI' in df.columns:
        df['PHARMACYNPI'] = df['PHARMACYNPI'].astype(str).str.zfill(10)
    if 'NABP' in df.columns:
        df['NABP'] = df['NABP'].astype(str).str.zfill(7)
    return df

def standardize_network_ids(network):
    """
    Pads 'pharmacy_npi' to 10 digits and 'pharmacy_nabp' to 7 digits in the network DataFrame.

    Args:
        network (pd.DataFrame): Network DataFrame.

    Returns:
        pd.DataFrame: Updated network DataFrame with padded ID columns.
    """
    if 'pharmacy_npi' in network.columns:
        network['pharmacy_npi'] = network['pharmacy_npi'].astype(str).str.zfill(10)
    if 'pharmacy_nabp' in network.columns:
        network['pharmacy_nabp'] = network['pharmacy_nabp'].astype(str).str.zfill(7)
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
        left_on=['PHARMACYNPI', 'NABP'],
        right_on=['pharmacy_npi', 'pharmacy_nabp'],
        how='left'
    )

def drop_duplicates_df(df):
    """
    Drops duplicate rows from the DataFrame.

    Args:
        df (pd.DataFrame): DataFrame to deduplicate.

    Returns:
        pd.DataFrame: Deduplicated DataFrame.
    """
    return df.drop_duplicates()

def clean_logic_and_tier(df, logic_col='Logic', tier_col='FormularyTier'):
    """
    Coerces the 'Logic' and 'FormularyTier' columns to numeric, coercing errors to NaN.

    Args:
        df (pd.DataFrame): DataFrame with logic/tier columns.
        logic_col (str): Name of the logic column.
        tier_col (str): Name of the tier column.

    Returns:
        pd.DataFrame: DataFrame with numeric logic and tier columns.
    """
    df[logic_col] = pd.to_numeric(df[logic_col], errors='coerce')
    df[tier_col] = pd.to_numeric(df[tier_col], errors='coerce')
    return df

def filter_recent_date(df, date_col='DATEFILLED'):
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
    df,
    logic_col='Logic',
    min_logic=5,
    max_logic=10,
    maint_col='Maint Drug?'
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
        (df[logic_col] >= min_logic) &
        (df[logic_col] <= max_logic) &
        (df[maint_col] == 'Y')
    ]

def filter_products_and_alternative(
    df,
    product_col='Product Name',
    alternative_col='Alternative'
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
    df = df[~df[alternative_col].astype(str)
        .str.contains(r'Covered|Use different NDC', case=False, regex=True, na=False)]
    return df