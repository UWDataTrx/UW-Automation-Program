import pandas as pd
import json
import logging
import os
import csv
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
import getpass  # noqa: E402
from datetime import datetime  # noqa: E402
from dataclasses import dataclass  # noqa: E402

# Load the audit log path from config using pathlib
config_path = Path(__file__).parent.parent / "config" / "file_paths.json"
with config_path.open("r") as f:
    file_paths = json.load(f)
audit_log_path = Path(os.path.expandvars(file_paths["audit_log"]))


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
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[ensure_directory_exists] Error: {e}")


def write_audit_log(script_name, message, status="INFO"):
    """
    Appends a log entry to the shared audit log in OneDrive. Rotates log if too large.
    """
    try:
        username = getpass.getuser()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = [timestamp, username, script_name, message, status]

        base_log_dir = audit_log_path.parent
        user_log_dir = base_log_dir / username
        user_log_path = user_log_dir / "Audit_Log.csv"

        write_header = not user_log_path.exists()
        if not user_log_dir.exists():
            try:
                user_log_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"[Audit Log] Could not create user log folder: {e}")

        max_size = 5 * 1024 * 1024
        if user_log_path.exists() and user_log_path.stat().st_size > max_size:
            for i in range(2, 0, -1):
                prev = user_log_path.with_suffix(f".csv.{i}")
                prev2 = user_log_path.with_suffix(f".csv.{i + 1}")
                if prev.exists():
                    prev.replace(prev2)
            user_log_path.replace(user_log_path.with_suffix(".csv.1"))

        with user_log_path.open(mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if write_header:
                writer.writerow(["Timestamp", "User", "Script", "Message", "Status"])
            writer.writerow(log_entry)
    except Exception as e:
        print(f"[Audit Log] Error: {e}")


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
    Loads a JSON config file, replacing %OneDrive% with the user's OneDrive path.
    Returns a dictionary mapping keys to resolved absolute file paths.
    """
    # Always use the config directory for file_paths.json
    config_dir = Path(__file__).parent.parent / "config"
    json_path = config_dir / "file_paths.json"
    try:
        with json_path.open("r") as f:
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
        logging.exception(f"Failed to load or resolve file paths from {json_path}")
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
