import pandas as pd
import json
import logging
import os
import csv
from pathlib import Path
import getpass
from datetime import datetime
from dataclasses import dataclass

# Load the audit log path from config
config_path = Path(__file__).parent.parent / "config" / "file_paths.json"
with open(config_path, "r") as f:
    file_paths = json.load(f)
shared_log_path = os.path.expandvars(file_paths["audit_log"])


@dataclass
class LogicMaintenanceConfig:
    """Configuration for logic and maintenance filtering."""

    logic_col: str = "Logic"
    min_logic: int = 5
    max_logic: int = 10
    maint_col: str = "Maint Drug?"


def ensure_directory_exists(path):
    """
    Ensures the directory for the given path exists.
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception as e:
        print(f"[ensure_directory_exists] Error: {e}")


def write_audit_log(script_name, message, status="INFO"):
    """
    Appends a log entry to the audit log in OneDrive in user-specific folders. Rotates log if too large.
    """
    try:
        username = getpass.getuser()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = [timestamp, username, script_name, message, status]

        # Map usernames to folder names (handle common variations)
        user_folder_mapping = {
            "DamionMorrison": "Damion Morrison",
            "Damion Morrison": "Damion Morrison",
            "DannyBushnell": "Danny Bushnell", 
            "Danny Bushnell": "Danny Bushnell",
            "BrettBauer": "Brett Bauer",
            "Brett Bauer": "Brett Bauer", 
            "BrendanReamer": "Brendan Reamer",
            "Brendan Reamer": "Brendan Reamer",
            "MitchellFrederick": "Mitchell Frederick",
            "Mitchell Frederick": "Mitchell Frederick",
            # Add variations for different username formats
            "damion.morrison": "Damion Morrison",
            "danny.bushnell": "Danny Bushnell",
            "brett.bauer": "Brett Bauer",
            "brendan.reamer": "Brendan Reamer", 
            "mitchell.frederick": "Mitchell Frederick"
        }

        # Get the correct folder name for this user
        user_folder = user_folder_mapping.get(username, "Other Users")
        
        # Get base log directory from config
        base_log_dir = Path(os.path.expandvars(file_paths["audit_log"])).parent
        user_log_dir = base_log_dir / user_folder
        
        # Create user-specific directory if it doesn't exist
        user_log_dir.mkdir(parents=True, exist_ok=True)
        
        # User-specific log file path
        user_log_path = user_log_dir / "Audit_Log.csv"

        write_header = not os.path.exists(user_log_path)
        ensure_directory_exists(user_log_path)

        # Log rotation: if file > 5MB, rotate (keep 3 backups)
        max_size = 5 * 1024 * 1024
        if (
            os.path.exists(user_log_path)
            and os.path.getsize(user_log_path) > max_size
        ):
            for i in range(2, 0, -1):
                prev = f"{user_log_path}.{i}"
                prev2 = f"{user_log_path}.{i + 1}"
                if os.path.exists(prev):
                    os.replace(prev, prev2)
            os.replace(user_log_path, f"{user_log_path}.1")

        with open(user_log_path, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if write_header:
                writer.writerow(["Timestamp", "User", "Script", "Message", "Status"])
            writer.writerow(log_entry)
    except Exception as e:
        print(f"[Audit Log] Error: {e}")
        # Fallback to original audit log if user-specific logging fails
        try:
            fallback_log_path = os.path.expandvars(file_paths["audit_log"])
            ensure_directory_exists(fallback_log_path)
            # Recreate log_entry in case of error in main try block
            fallback_username = getpass.getuser()
            fallback_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fallback_log_entry = [fallback_timestamp, fallback_username, script_name, message, status]
            
            with open(fallback_log_path, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                if not os.path.exists(fallback_log_path):
                    writer.writerow(["Timestamp", "User", "Script", "Message", "Status"])
                writer.writerow(fallback_log_entry)
        except Exception as fallback_error:
            print(f"[Audit Log Fallback] Error: {fallback_error}")


def log_exception(script_name, exc, status="ERROR"):
    """
    Standardized exception logging to audit log and console.
    """
    import traceback

    tb = traceback.format_exc()
    msg = f"{exc}: {tb}"
    print(f"[Exception] {msg}")
    write_audit_log(script_name, msg, status)


def load_file_paths(json_file="file_paths.json"):
    """
    Loads a JSON config file with relative paths and resolves them to absolute paths
    based on the script's location. This makes the system user-agnostic.
    Returns a dictionary mapping keys to resolved absolute file paths.
    """
    try:
        # Get the directory containing this utils.py file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Build path to the config file relative to utils.py
        config_path = os.path.join(script_dir, "..", "config", json_file)
        
        with open(config_path, "r") as f:
            paths = json.load(f)

        resolved_paths = {}
        for key, path in paths.items():
            if path.startswith("%OneDrive%"):
                # Legacy OneDrive path support for backward compatibility
                onedrive_path = os.environ.get("OneDrive")
                if not onedrive_path:
                    raise EnvironmentError(
                        "OneDrive environment variable not found. Please ensure OneDrive is set up."
                    )
                resolved_path = path.replace("%OneDrive%", onedrive_path)
            else:
                # Handle relative paths - resolve relative to the script's parent directory
                # This assumes all relative paths are relative to the UW-Automation-Program directory
                base_dir = os.path.join(script_dir, "..")
                resolved_path = os.path.join(base_dir, path)
            
            resolved_paths[key] = str(Path(resolved_path).resolve())

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


def filter_logic_and_maintenance(df, config=None):
    """
    Filters rows where min_logic ≤ Logic ≤ max_logic and 'Maint Drug?' == 'Y'.

    Args:
        df (pd.DataFrame): DataFrame with logic and maintenance columns.
        config (LogicMaintenanceConfig, optional): Configuration object with filtering parameters.
                                                 If None, uses default configuration.

    Returns:
        pd.DataFrame: Filtered DataFrame.
    """
    if config is None:
        config = LogicMaintenanceConfig()

    return df[
        (df[config.logic_col] >= config.min_logic)
        & (df[config.logic_col] <= config.max_logic)
        & (df[config.maint_col] == "Y")
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
