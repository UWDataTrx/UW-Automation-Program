import logging
import os
import re
import sys
from pathlib import Path

import pandas as pd

# Ensure project root is in sys.path before importing project_settings
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


from modules.audit_helper import (log_file_access,  # noqa: E402
                                  log_user_session_end, log_user_session_start,
                                  make_audit_entry)
from utils.utils import (clean_logic_and_tier,  # noqa: E402
                         drop_duplicates_df, filter_logic_and_maintenance,
                         filter_products_and_alternative, filter_recent_date,
                         write_audit_log)

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Prevent double logging
logger.propagate = False
# Add console handler for terminal output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

try:
    import importlib.util

    if importlib.util.find_spec("xlsxwriter") is None:
        print(
            "The 'xlsxwriter' module is not installed. Please install it using 'pip install xlsxwriter'."
        )
        sys.exit(1)
except Exception:
    print("Error checking for 'xlsxwriter' module.")
    sys.exit(1)



# ---------------------------------------------------------------------------
# Tier summarization helper
# ---------------------------------------------------------------------------
def summarize_by_tier(df, col, from_val, to_val):
    # Update logic/tier filtering to use 1-10 instead of 5-10
    filtered = df[(df[col] == from_val) & (df["FormularyTier"] == to_val)]
    pt = pd.pivot_table(
        filtered,
        values=["Rxs", "MemberID"],
        index=["Product Name"],
        aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique},
    )
    pt = pt.rename(columns={"Rxs": "Total Rxs", "MemberID": "Unique Members"})
    rxs = filtered["Rxs"].sum()
    members = filtered["MemberID"].nunique()
    return pt, rxs, members


def load_tier_disruption_data(file_paths):
    """Load all required data files for tier disruption processing."""
    # Load claims with fallback
    if not file_paths.get("reprice"):
        write_audit_log(
            "tier_disruption.py",
            "No reprice/template file provided.",
            status="ERROR",
        )
        print("No reprice/template file provided. Skipping claims loading.")
        return None

    try:
        claims = pd.read_excel(file_paths["reprice"], sheet_name="Claims Table")
    except Exception as e:
        logger.error(f"Error loading claims: {e}")
        make_audit_entry(
            "tier_disruption.py", f"Claims Table fallback error: {e}", "FILE_ERROR"
        )
        claims = pd.read_excel(file_paths["reprice"], sheet_name=0)

    print(f"claims shape: {claims.shape}")
    claims.info()

    # Load reference tables
    medi = pd.read_excel(
        file_paths["medi_span"], usecols=["NDC", "Maint Drug?", "Product Name"]
    )
    print(f"medi shape: {medi.shape}")

    u = pd.read_excel(
        file_paths["u_disrupt"], sheet_name="Universal NDC", usecols=["NDC", "Tier"]
    )
    print(f"u shape: {u.shape}")

    e = pd.read_excel(
        file_paths["e_disrupt"],
        sheet_name="Alternatives NDC",
        usecols=["NDC", "Tier", "Alternative"],
    )
    print(f"e shape: {e.shape}")

    if file_paths["n_disrupt"].lower().endswith(".csv"):
        network = pd.read_csv(
            file_paths["n_disrupt"],
            usecols=["pharmacy_nabp", "pharmacy_npi", "pharmacy_is_excluded"],
        )
    else:
        network = pd.read_excel(
            file_paths["n_disrupt"],
            usecols=["pharmacy_nabp", "pharmacy_npi", "pharmacy_is_excluded"],
        )
    print(f"network shape: {network.shape}")
    print(f"Raw network['pharmacy_nabp'] sample: {network['pharmacy_nabp'].head(10).tolist()}")
    print(f"Raw network['pharmacy_npi'] sample: {network['pharmacy_npi'].head(10).tolist()}")
    print(f"Unique values in raw network['pharmacy_is_excluded']: {network['pharmacy_is_excluded'].unique()}")

    return claims, medi, u, e, network


def process_tier_data_pipeline(claims, reference_data, network):
    """Process the data pipeline for tier disruption."""
    medi, u, e = reference_data

    # Merge reference data
    df = claims.merge(medi, on="NDC", how="left")
    print(f"After merge with medi: {df.shape}")
    df = df.merge(u.rename(columns={"Tier": "Universal Tier"}), on="NDC", how="left")
    print(f"After merge with u: {df.shape}")
    df = df.merge(e.rename(columns={"Tier": "Exclusive Tier"}), on="NDC", how="left")
    print(f"After merge with e: {df.shape}")
    # Unified pharmacy_id creation and merging
    df['pharmacy_id'] = df.apply(lambda row: str(row['PHARMACYNPI']) if pd.notna(row['PHARMACYNPI']) else str(row['NABP']), axis=1)
    network['pharmacy_id'] = network.apply(lambda row: str(row['pharmacy_npi']) if pd.notna(row['pharmacy_npi']) else str(row['pharmacy_nabp']), axis=1)
    df = pd.merge(df, network[['pharmacy_id', 'pharmacy_is_excluded']], on='pharmacy_id', how='left')
    print(f"After merge on pharmacy_id: {df.shape}")
    # Map exclusions: True/False/REVIEW
    def map_excluded(val):
        if pd.isna(val) or str(val).strip() == "":
            return "REVIEW"
        v = str(val).strip().lower()
        if v in {"yes", "y", "true", "1"}:
            return True
        elif v in {"no", "n", "false", "0"}:
            return False
        return "REVIEW"
    df["pharmacy_is_excluded"] = df["pharmacy_is_excluded"].apply(map_excluded)
    # Fill missing IDs
    import numpy as np
    df["PHARMACYNPI"] = df["PHARMACYNPI"].replace([np.nan, '', float('nan')], "N/A")
    import numpy as np
    df["NABP"] = df["NABP"].fillna("N/A").replace(['', float('nan')], "N/A")

    # Date parsing, deduplication, type cleaning, and filters
    df["DATEFILLED"] = pd.to_datetime(df["DATEFILLED"], errors="coerce")
    print(f"After DATEFILLED to_datetime: {df.shape}")

    df = drop_duplicates_df(df)
    print(f"After drop_duplicates_df: {df.shape}")

    df = clean_logic_and_tier(df)
    print(f"After clean_logic_and_tier: {df.shape}")

    df = filter_recent_date(df)
    print(f"After filter_recent_date: {df.shape}")

    df = filter_logic_and_maintenance(df)
    print(f"After filter_logic_and_maintenance: {df.shape}")

    df = filter_products_and_alternative(df)
    print(f"After filter_products_and_alternative: {df.shape}")

    return df


def handle_tier_pharmacy_exclusions(df, file_paths):
    """Handle pharmacy exclusions for tier disruption."""
    # Ensure 'pharmacy_is_excluded' column contains actual boolean values with type inference
    if "pharmacy_is_excluded" in df.columns:
        def map_excluded(val):
            if pd.isna(val):
                return None
            v = str(val).strip().lower()
            if v in {"yes", "y", "true", "1"}:
                return True
            elif v in {"no", "n", "false", "0"}:
                return False
            logger.warning(f"Unexpected pharmacy_is_excluded value encountered: {val}")
            return None
        df["pharmacy_is_excluded"] = df["pharmacy_is_excluded"].apply(map_excluded)
        logger.info(
            f"pharmacy_is_excluded value counts: {df['pharmacy_is_excluded'].value_counts(dropna=False).to_dict()}"
        )


        # Identify rows where pharmacy_is_excluded is NA or 'unknown'
        unknown_mask = df["pharmacy_is_excluded"].isna() | (df["pharmacy_is_excluded"] == "unknown")
        unknown_pharmacies = df[unknown_mask]
        logger.info(f"Unknown/NA pharmacies count: {unknown_pharmacies.shape[0]}")

        if not unknown_pharmacies.empty:
            output_file_path = file_paths["pharmacy_validation"]
            logger.info(
                f"Preparing to write unknown/NA pharmacies to pharmacy validation log: {output_file_path}"
            )
            unknown_pharmacies_output = unknown_pharmacies[["PHARMACYNPI", "NABP"]].fillna("N/A")
            unknown_pharmacies_output["Result"] = unknown_pharmacies["pharmacy_is_excluded"].fillna("NA")
            logger.info(f"Rows to write: {len(unknown_pharmacies_output)}")

            try:
                output_file_path_obj = Path(output_file_path)
                if output_file_path_obj.exists():
                    logger.info(
                        f"Existing pharmacy validation log found at: {output_file_path}"
                    )
                    # Handle both CSV and Excel files with proper encoding
                    try:
                        if str(output_file_path_obj).lower().endswith('.csv'):
                            # Try different encodings for CSV files
                            try:
                                existing_df = pd.read_csv(output_file_path_obj, encoding='utf-8')
                            except UnicodeDecodeError:
                                logger.warning("UTF-8 failed, trying latin-1 encoding...")
                                existing_df = pd.read_csv(output_file_path_obj, encoding='latin-1')
                        else:
                            # Handle Excel files
                            existing_df = pd.read_excel(output_file_path_obj)
                    except Exception as read_error:
                        logger.error(f"Failed to read existing file: {read_error}")
                        logger.info("Creating backup and starting fresh...")
                        backup_path = output_file_path_obj.with_suffix(f"{output_file_path_obj.suffix}.backup")
                        output_file_path_obj.rename(backup_path)
                        existing_df = pd.DataFrame()
                    
                    logger.info(f"Existing log rows: {len(existing_df)}")
                    combined_df = pd.concat(
                        [existing_df, unknown_pharmacies_output], ignore_index=True
                    )
                    combined_df = combined_df.drop_duplicates()
                    logger.info(
                        f"Combined log rows after append and deduplication: {len(combined_df)}"
                    )
                else:
                    logger.info(
                        f"No existing pharmacy validation log found. Creating new file at: {output_file_path}"
                    )
                    combined_df = unknown_pharmacies_output

                # Save based on file extension
                if str(output_file_path_obj).lower().endswith('.csv'):
                    combined_df.to_csv(output_file_path_obj, index=False, encoding='utf-8')
                else:
                    combined_df.to_excel(output_file_path_obj, index=False)
                logger.info(
                    f"Successfully wrote {len(unknown_pharmacies_output)} unknown/NA pharmacy rows to '{output_file_path}'. Total rows now: {len(combined_df)}."
                )

            except Exception as e:
                logger.error(
                    f"Error updating pharmacy validation file '{output_file_path}': {e}"
                )
                make_audit_entry(
                    "tier_disruption.py",
                    f"Pharmacy validation file update error: {e}",
                    "FILE_ERROR",
                )
                # Fallback - just write the new data
                try:
                    unknown_pharmacies_output.to_excel(output_file_path, index=False)
                    logger.info(
                        f"Fallback: Wrote {len(unknown_pharmacies_output)} unknown/NA pharmacy rows to '{output_file_path}'."
                    )
                except Exception as fallback_e:
                    logger.error(
                        f"Fallback error writing to '{output_file_path}': {fallback_e}"
                    )

    return df


def create_tier_definitions():
    """Create the tier definitions for analysis."""
    return [
        ("Universal_Positive 2-1", "Universal Tier", 1, 2),
        ("Universal_Positive 3-1", "Universal Tier", 1, 3),
        ("Universal_Positive 3-2", "Universal Tier", 2, 3),
        ("Universal_Negative 1-2", "Universal Tier", 2, 1),
        ("Universal_Negative 1-3", "Universal Tier", 3, 1),
        ("Universal_Negative 2-3", "Universal Tier", 3, 2),
        ("Exclusive_Positive 2-1", "Exclusive Tier", 1, 2),
        ("Exclusive_Positive 3-1", "Exclusive Tier", 1, 3),
        ("Exclusive_Positive 3-2", "Exclusive Tier", 2, 3),
        ("Exclusive_Negative 1-2", "Exclusive Tier", 2, 1),
        ("Exclusive_Negative 1-3", "Exclusive Tier", 3, 1),
        ("Exclusive_Negative 2-3", "Exclusive Tier", 3, 2),
    ]


def process_tier_pivots(df, tiers):
    """Process tier pivot tables and collect statistics."""
    tab_members = {}
    tab_rxs = {}
    tier_pivots = []

    for name, col, from_val, to_val in tiers:
        pt, rxs, members = summarize_by_tier(df, col, from_val, to_val)
        tier_pivots.append((name, pt, members, rxs))
        tab_members[name] = members
        tab_rxs[name] = rxs

    return tier_pivots, tab_members, tab_rxs


def process_exclusions(df):
    """Process exclusions data and create pivot table."""
    exclusions = df[df["Exclusive Tier"] == "Nonformulary"]
    ex_pt = exclusions.pivot_table(
        values=["Rxs", "MemberID"],
        index=["Product Name", "Alternative"],
        aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique},
    )
    ex_pt = ex_pt.rename(columns={"Rxs": "Total Rxs", "MemberID": "Unique Members"})
    exc_rxs = exclusions["Rxs"].sum()
    exc_members = exclusions["MemberID"].nunique()

    return ex_pt, exc_rxs, exc_members


def create_summary_dataframe(tab_members, tab_rxs, total_claims, total_members):
    """Create the summary DataFrame with calculated statistics."""
    uni_pos_keys = [
        "Universal_Positive 2-1",
        "Universal_Positive 3-1",
        "Universal_Positive 3-2",
    ]
    uni_neg_keys = [
        "Universal_Negative 1-2",
        "Universal_Negative 1-3",
        "Universal_Negative 2-3",
    ]
    ex_pos_keys = [
        "Exclusive_Positive 2-1",
        "Exclusive_Positive 3-1",
        "Exclusive_Positive 3-2",
    ]
    ex_neg_keys = [
        "Exclusive_Negative 1-2",
        "Exclusive_Negative 1-3",
        "Exclusive_Negative 2-3",
    ]

    uni_pos_utilizers = sum(tab_members[k] for k in uni_pos_keys)
    uni_pos_claims = sum(tab_rxs[k] for k in uni_pos_keys)
    uni_pos_pct = uni_pos_claims / total_claims if total_claims else 0

    uni_neg_utilizers = sum(tab_members[k] for k in uni_neg_keys)
    uni_neg_claims = sum(tab_rxs[k] for k in uni_neg_keys)
    uni_neg_pct = uni_neg_claims / total_claims if total_claims else 0

    ex_pos_utilizers = sum(tab_members[k] for k in ex_pos_keys)
    ex_pos_claims = sum(tab_rxs[k] for k in ex_pos_keys)
    ex_pos_pct = ex_pos_claims / total_claims if total_claims else 0

    ex_neg_utilizers = sum(tab_members[k] for k in ex_neg_keys)
    ex_neg_claims = sum(tab_rxs[k] for k in ex_neg_keys)
    ex_neg_pct = ex_neg_claims / total_claims if total_claims else 0

    exc_utilizers = tab_members["Exclusions"]
    exc_claims = tab_rxs["Exclusions"]
    exc_pct = exc_claims / total_claims if total_claims else 0

    return pd.DataFrame(
        {
            "Formulary": [
                "Universal Positive",
                "Universal Negative",
                "Exclusive Positive",
                "Exclusive Negative",
                "Exclusions",
            ],
            "Utilizers": [
                uni_pos_utilizers,
                uni_neg_utilizers,
                ex_pos_utilizers,
                ex_neg_utilizers,
                exc_utilizers,
            ],
            "Rxs": [
                uni_pos_claims,
                uni_neg_claims,
                ex_pos_claims,
                ex_neg_claims,
                exc_claims,
            ],
            "% of claims": [
                uni_pos_pct,
                uni_neg_pct,
                ex_pos_pct,
                ex_neg_pct,
                exc_pct,
            ],
            "": ["", "", "", "", ""],
            "Totals": [
                f"Members: {total_members}",
                f"Claims: {total_claims}",
                "",
                "",
                "",
            ],
        }
    )


def create_network_analysis(df):
    """Create network analysis for excluded pharmacies."""
    # Ensure any blanks in pharmacy_is_excluded are marked as 'REVIEW' before filtering
    df["pharmacy_is_excluded"] = df["pharmacy_is_excluded"].replace([None, '', pd.NA], "REVIEW")
    # Only include rows where pharmacy_is_excluded is True or REVIEW
    network_df = df[df["pharmacy_is_excluded"].isin([True, "REVIEW"])]
    filter_phrases = [
        "CVS",
        "Walgreens",
        "Kroger",
        "Walmart",
        "Rite Aid",
        "Optum",
        "Express Scripts",
        "DMR",
        "Williams Bro",
        "Publix",
    ]
    filter_phrases_escaped = [re.escape(phrase.lower()) for phrase in filter_phrases]
    regex_pattern = "|".join([f"\b{p}\b" for p in filter_phrases_escaped])
    network_df = network_df[
        ~network_df["Pharmacy Name"]
        .str.lower()
        .str.contains(regex_pattern, case=False, regex=True, na=False)
    ]
    # Build network sheet as a DataFrame with required columns
    if {"PHARMACYNPI", "NABP", "Pharmacy Name", "MemberID", "Rxs", "pharmacy_is_excluded"}.issubset(network_df.columns):
        network_df["PHARMACYNPI"] = network_df["PHARMACYNPI"].replace([None, '', pd.NA, float('nan')], "N/A")
        network_df["NABP"] = network_df["NABP"].replace([None, '', pd.NA, float('nan')], "N/A")
        network_sheet = network_df[["PHARMACYNPI", "NABP", "Pharmacy Name", "MemberID", "Rxs", "pharmacy_is_excluded"]].copy()
        network_sheet = network_sheet.rename(columns={"MemberID": "Unique Members", "Rxs": "Total Rxs"})
        # Drop duplicates so each pharmacy only appears once
        network_sheet = network_sheet.drop_duplicates(subset=["PHARMACYNPI", "NABP", "Pharmacy Name"])
        return network_sheet, None
    else:
        return None, None


def write_excel_sheets(
    writer, df, summary_df, tier_pivots, ex_pt, exc_members, network_df, network_pivot
):
    """Write all sheets to the Excel file."""
    from utils.utils import write_audit_log

    # Validate writer path
    output_path = getattr(writer, "path", None)
    if not output_path or not str(output_path).strip():
        output_path = "Unknown_Tier_Disruption_Report.xlsx"
        logger.warning(
            "Output filename was empty or invalid. Defaulting to 'Unknown_Tier_Disruption_Report.xlsx'."
        )
        write_audit_log(
            "tier_disruption.py",
            "Output filename was empty or invalid. Defaulting to 'Unknown_Tier_Disruption_Report.xlsx'.",
            "WARNING",
        )

    # Write Summary sheet
    summary_df.to_excel(writer, sheet_name="Summary", index=False)

    # Write tier pivots
    for name, pt, members, _ in tier_pivots:
        pt.to_excel(writer, sheet_name=name)
        writer.sheets[name].write("F1", f"Total Members: {members}")

    # Write Exclusions sheet
    ex_pt.to_excel(writer, sheet_name="Exclusions")
    writer.sheets["Exclusions"].write("F1", f"Total Members: {exc_members}")

    # Write Data sheet
    data_sheet_df = df.copy()
    data_sheet_df.to_excel(writer, sheet_name="Data", index=False)

    # Write Network sheet
    if network_pivot is not None:
        network_pivot.to_excel(writer, sheet_name="Network", index=False)

    # Write filtered network data
    selected_columns = [
        "PHARMACYNPI",
        "NABP",
        "MemberID",
        "Pharmacy Name",
        "pharmacy_is_excluded",
        "Unique Identifier",
    ]
    if network_df is not None:
        available_columns = [col for col in selected_columns if col in network_df.columns]
        missing_columns = [col for col in selected_columns if col not in network_df.columns]
        if missing_columns:
            logger.warning(f"Network DataFrame missing columns: {missing_columns}. Only writing available columns: {available_columns}")
        network_df[available_columns].to_excel(writer, sheet_name="Network", index=False)
        logger.info(
            f"Network sheet updated with {network_df.shape[0]} excluded pharmacy records (minus major chains) and columns: {available_columns}"
        )
    write_audit_log(
        "tier_disruption.py", f"Excel report written to: {output_path}", "INFO"
    )


def reorder_excel_sheets(writer):
    """Reorder sheets so Summary follows Data."""
    sheets = writer.sheets  # This is a dict: {sheet_name: worksheet_object}
    names = list(sheets.keys())
    if "Data" in names and "Summary" in names:
        data_idx = names.index("Data")
        summary_idx = names.index("Summary")
        if summary_idx != data_idx + 1:
            # Move "Summary" sheet immediately after "Data"
            items = list(sheets.items())
            summary_item = items.pop(summary_idx)
            items.insert(data_idx + 1, summary_item)
            writer.sheets.clear()
            writer.sheets.update(dict(items))


def show_completion_message(output_path):
    """Show completion message and popup."""
    write_audit_log("tier_disruption.py", "Processing complete.")
    print(f"Processing complete. Output file: {output_path}")
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Processing Complete", "Processing complete")
        root.destroy()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main processing pipeline
# ---------------------------------------------------------------------------
def process_data():
    # Get current username
    username = os.environ.get("USERNAME") or os.environ.get("USER") or "UnknownUser"
    logger.info(f"Session started for user: {username}")
    log_user_session_start("tier_disruption.py")
    write_audit_log(
        "tier_disruption.py", f"Processing started by user: {username}", "INFO"
    )
    logger.info("Loading data files...")

    # Always use 'LBL for Disruption.xlsx' in the current working directory
    output_path = Path.cwd() / "LBL for Disruption.xlsx"
    logger.info(f"Output file will be: {output_path}")

    try:
        # Get the config file path relative to the project root
        from config.config_loader import ConfigManager

        config_manager = ConfigManager()
        file_paths = config_manager.get("../config/file_paths.json")

        logger.info("Loading tier disruption data files...")
        result = load_tier_disruption_data(file_paths)
        if result is None:
            logger.error("Claims loading failed - early exit")
            make_audit_entry(
                "tier_disruption.py", "Claims loading failed - early exit", "DATA_ERROR"
            )
            return  # Early exit if claims loading failed
        claims, medi, u, e, network = result
    except Exception as e:
        logger.error(f"Error loading configuration or data files: {e}")
        make_audit_entry(
            "tier_disruption.py", f"Error loading configuration or data files: {e}", "CONFIG_ERROR"
        )
        return

    logger.info(f"Claims loaded: {claims.shape}")
    logger.info(f"Medi loaded: {medi.shape}")
    logger.info(f"Universal NDC loaded: {u.shape}")
    logger.info(f"Alternatives NDC loaded: {e.shape}")
    logger.info(f"Network loaded: {network.shape}")

    # Log file access
    log_file_access(
        "tier_disruption.py", file_paths.get("reprice", "unknown"), "LOADING"
    )
    write_audit_log(
        "tier_disruption.py",
        f"User {username} loaded file: {file_paths.get('reprice', 'unknown')}",
        "INFO",
    )
    reference_data = (medi, u, e)
    logger.info("Processing tier data pipeline...")
    df = process_tier_data_pipeline(claims, reference_data, network)
    logger.info(f"After processing pipeline: {df.shape}")

    logger.info("Handling pharmacy exclusions...")
    df = handle_tier_pharmacy_exclusions(df, file_paths)
    logger.info(f"After exclusions: {df.shape}")

    # Totals for summary
    total_claims = df["Rxs"].sum()
    total_members = df["MemberID"].nunique()
    logger.info(f"Total claims: {total_claims}, Total members: {total_members}")

    # Log data processing metrics
    make_audit_entry(
        "tier_disruption.py",
        f"Processed {total_claims} claims for {total_members} members by user: {username}",
        "INFO",
    )

    # Excel writer setup
    logger.info("Setting up Excel writer...")
    writer = pd.ExcelWriter(output_path, engine="xlsxwriter")

    # Summary calculations (must be written immediately after Data)
    tiers = create_tier_definitions()
    logger.info("Processing tier pivots...")
    tier_pivots, tab_members, tab_rxs = process_tier_pivots(df, tiers)

    # Exclusions sheet (Nonformulary)
    logger.info("Processing exclusions...")
    ex_pt, exc_rxs, exc_members = process_exclusions(df)
    tab_members["Exclusions"] = exc_members
    tab_rxs["Exclusions"] = exc_rxs

    # Write the 'Data' sheet first
    logger.info("Writing Data sheet...")
    data_sheet_df = df.copy()
    data_sheet_df.to_excel(writer, sheet_name="Data", index=False)

    # Write the 'Summary' sheet second
    logger.info("Writing Summary sheet...")
    summary_df = create_summary_dataframe(
        tab_members, tab_rxs, total_claims, total_members
    )
    summary_df.to_excel(writer, sheet_name="Summary", index=False)

    # Write tier pivots and Exclusions after Summary
    logger.info("Writing tier pivot sheets...")
    for name, pt, members, _ in tier_pivots:
        pt.to_excel(writer, sheet_name=name)
        writer.sheets[name].write("F1", f"Total Members: {members}")

    logger.info("Writing Exclusions sheet...")
    ex_pt.to_excel(writer, sheet_name="Exclusions")
    writer.sheets["Exclusions"].write("F1", f"Total Members: {exc_members}")

    # Network summary for excluded pharmacies (pharmacy_is_excluded="yes")
    logger.info("Processing network analysis...")
    network_df, network_pivot = create_network_analysis(df)
    total_pharmacies = df.shape[0]
    logger.info(f"pharmacy_is_excluded value counts: {df['pharmacy_is_excluded'].value_counts().to_dict()}")
    # Ensure pharmacy_is_excluded is boolean for correct inversion
    excluded_mask = df['pharmacy_is_excluded'].fillna(False).astype(bool)
    excluded_count = excluded_mask.sum()
    non_excluded_count = (~excluded_mask.astype(bool)).sum()
    logger.info(f"Total pharmacies in dataset: {total_pharmacies}")
    logger.info(f"Excluded pharmacies ('yes'): {excluded_count}")
    logger.info(f"Non-excluded pharmacies ('no'): {non_excluded_count}")
    logger.info(f"Sanity check: Excluded + Non-excluded = {excluded_count + non_excluded_count} (should match total)")
    if network_df is not None:
        logger.info(f"Network sheet will show {network_df.shape[0]} excluded pharmacy records (minus major chains)")
    else:
        logger.info("Network sheet will show 0 excluded pharmacy records (minus major chains) because network_df is None")

    # Write Network sheet
    if network_pivot is not None:
        logger.info("Writing Network pivot sheet...")
        network_pivot.to_excel(writer, sheet_name="Network", index=False)

    # Write filtered network data
    logger.info("Writing filtered network data...")
    selected_columns = [
        "PHARMACYNPI",
        "NABP",
        "MemberID",
        "Pharmacy Name",
        "pharmacy_is_excluded",
        "Unique Identifier",
    ]
    if network_df is not None:
        network_df[selected_columns].to_excel(writer, sheet_name="Network", index=False)
        logger.info(
            f"Network sheet updated with {network_df.shape[0]} excluded pharmacy records (minus major chains) and selected columns"
        )
    else:
        logger.info("Network sheet not written because network_df is None")

    writer.close()
    logger.info(f"Excel report written to: {output_path}")

    # Log successful completion
    make_audit_entry(
        "tier_disruption.py",
        f"Successfully generated tier disruption report: {str(output_path)} by user: {username}",
        "INFO",
    )
    log_file_access("tier_disruption.py", str(output_path), "CREATED")
    write_audit_log(
        "tier_disruption.py",
        f"Excel report written to: {str(output_path)} by user: {username}",
        "INFO",
    )
    print(f"Processing complete. Output file: {output_path}")
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Processing Complete", "Processing complete")
        root.destroy()
    except Exception:
        pass
    finally:
        # End audit session
        log_user_session_end("tier_disruption.py")


if __name__ == "__main__":
    process_data()
    # Always show terminal notification at the end
    print("Processing complete.")
