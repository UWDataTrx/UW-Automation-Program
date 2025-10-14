import logging
import os  # noqa: E402
import sys
from pathlib import Path

import pandas as pd

# Ensure project root is in sys.path before importing other modules
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

# Logging setup
logging.basicConfig(
    filename="bg_disruption.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
# Prevent double logging
logger.propagate = False
# Add console handler for terminal output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)



def load_data_files(file_paths):
    """Load and return all required data files."""
    logger.info("Loading data files...")

    # Load claims data
    try:
        claims = pd.read_excel(
            file_paths["reprice"],
            sheet_name="Claims Table",
            usecols=[
                "SOURCERECORDID",
                "NDC",
                "MemberID",
                "DATEFILLED",
                "FormularyTier",
                "Rxs",
                "Logic",
                "PHARMACYNPI",
                "NABP",
                "Pharmacy Name",
                "Universal Rebates",
                "Exclusive Rebates",
            ],
        )
    except Exception as e:
        logger.warning(f"Claims Table fallback: {e}")
        make_audit_entry(
            "bg_disruption.py", f"Claims Table fallback error: {e}", "FILE_ERROR"
        )
        write_audit_log(
            "bg_disruption.py", f"Claims Table fallback: {e}", status="WARNING"
        )
        claims = pd.read_excel(file_paths["reprice"], sheet_name=0)

    logger.info(f"claims shape: {claims.shape}")
    claims.info()

    # Load other data files
    medi = pd.read_excel(file_paths["medi_span"])
    logger.info(f"medi shape: {medi.shape}")

    uni = pd.read_excel(file_paths["u_disrupt"], sheet_name="Universal NDC")[
        ["NDC", "Tier"]
    ]
    logger.info(f"uni shape: {uni.shape}")

    exl = pd.read_excel(file_paths["e_disrupt"], sheet_name="Alternatives NDC")[
        ["NDC", "Tier", "Alternative"]
    ]
    logger.info(f"exl shape: {exl.shape}")

    if file_paths["n_disrupt"].lower().endswith(".csv"):
        network = pd.read_csv(file_paths["n_disrupt"])[
            ["pharmacy_nabp", "pharmacy_npi", "pharmacy_is_excluded"]
        ]
    else:
        network = pd.read_excel(file_paths["n_disrupt"])[
            ["pharmacy_nabp", "pharmacy_npi", "pharmacy_is_excluded"]
        ]
    logger.info(f"network shape: {network.shape}")
    logger.info(f"Raw network['pharmacy_nabp'] sample: {network['pharmacy_nabp'].head(10).tolist()}")
    logger.info(f"Raw network['pharmacy_npi'] sample: {network['pharmacy_npi'].head(10).tolist()}")
    logger.info(f"Unique values in raw network['pharmacy_is_excluded']: {network['pharmacy_is_excluded'].unique()}")

    return claims, medi, uni, exl, network


def merge_data_files(claims, reference_data, network):
    """Merge all data files into a single DataFrame."""
    logger.info("Merging data files...")

    medi, uni, exl = reference_data

    df = claims.merge(medi, on="NDC", how="left")
    logger.info(f"After merge with medi: {df.shape}")

    df = df.merge(uni.rename(columns={"Tier": "Universal Tier"}), on="NDC", how="left")
    logger.info(f"After merge with uni: {df.shape}")

    df = df.merge(exl.rename(columns={"Tier": "Exclusive Tier"}), on="NDC", how="left")
    logger.info(f"After merge with exl: {df.shape}")

    # Unified pharmacy_id creation and merging
    df['pharmacy_id'] = df.apply(lambda row: str(row['PHARMACYNPI']) if pd.notna(row['PHARMACYNPI']) else str(row['NABP']), axis=1)
    network['pharmacy_id'] = network.apply(lambda row: str(row['pharmacy_npi']) if pd.notna(row['pharmacy_npi']) else str(row['pharmacy_nabp']), axis=1)
    df = pd.merge(df, network[['pharmacy_id', 'pharmacy_is_excluded']], on='pharmacy_id', how='left')
    logger.info(f"After merge on pharmacy_id: {df.shape}")
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
    df["PHARMACYNPI"] = df["PHARMACYNPI"].replace(['', float('nan')], "N/A").fillna("N/A")
    df["NABP"] = df["NABP"].replace(['', float('nan')], "N/A").fillna("N/A")
    return df


def process_and_filter_data(df):
    """Process and filter the merged data."""
    logger.info("Processing and filtering data...")

    # Date parsing, deduplication, type cleaning, and filters
    df["DATEFILLED"] = pd.to_datetime(df["DATEFILLED"], errors="coerce")
    logger.info(f"After DATEFILLED to_datetime: {df.shape}")

    df = drop_duplicates_df(df)
    logger.info(f"After drop_duplicates_df: {df.shape}")

    df = clean_logic_and_tier(df)
    logger.info(f"After clean_logic_and_tier: {df.shape}")

    df = filter_recent_date(df)
    logger.info(f"After filter_recent_date: {df.shape}")

    df = filter_logic_and_maintenance(df)
    logger.info(f"After filter_logic_and_maintenance: {df.shape}")

    df = filter_products_and_alternative(df)
    logger.info(f"After filter_products_and_alternative: {df.shape}")

    df["FormularyTier"] = df["FormularyTier"].astype(str).str.strip().str.upper()
    df["Alternative"] = df["Alternative"].astype(str)

    return df


def handle_pharmacy_exclusions(df, file_paths):
    """Handle pharmacy exclusions and validation."""
    logger.info("Handling pharmacy exclusions...")

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
            unknown_pharmacies_output = unknown_pharmacies[["PHARMACYNPI", "NABP"]].fillna("N/A")
            unknown_pharmacies_output["Result"] = unknown_pharmacies["pharmacy_is_excluded"].fillna("NA")

            try:
                output_path = Path(output_file_path)
                if output_path.exists():
                    # Handle both CSV and Excel files with proper encoding
                    try:
                        if str(output_path).lower().endswith('.csv'):
                            # Try different encodings for CSV files
                            try:
                                existing_df = pd.read_csv(output_path, encoding='utf-8')
                            except UnicodeDecodeError:
                                logger.warning("UTF-8 failed, trying latin-1 encoding...")
                                existing_df = pd.read_csv(output_path, encoding='latin-1')
                        else:
                            # Handle Excel files
                            existing_df = pd.read_excel(output_path)
                    except Exception as read_error:
                        logger.error(f"Failed to read existing file: {read_error}")
                        logger.info("Creating backup and starting fresh...")
                        backup_path = output_path.with_suffix(f"{output_path.suffix}.backup")
                        output_path.rename(backup_path)
                        existing_df = pd.DataFrame()
                    
                    combined_df = pd.concat(
                        [existing_df, unknown_pharmacies_output], ignore_index=True
                    )
                    combined_df = combined_df.drop_duplicates()
                else:
                    combined_df = unknown_pharmacies_output

                # Save based on file extension
                if str(output_path).lower().endswith('.csv'):
                    combined_df.to_csv(output_path, index=False, encoding='utf-8')
                else:
                    combined_df.to_excel(output_path, index=False)
                logger.info(
                    f"Unknown/NA pharmacies written to '{output_path}' with Result column."
                )

            except Exception as e:
                logger.error(f"Error updating pharmacy validation file: {e}")
                make_audit_entry(
                    "bg_disruption.py",
                    f"Pharmacy validation file update error: {e}",
                    "FILE_ERROR",
                )
                # Fallback - just write the new data
                unknown_pharmacies_output.to_excel(output_file_path, index=False)
                logger.info(
                    f"Unknown/NA pharmacies written to '{output_file_path}' (fallback mode)."
                )

    return df


def create_data_filters(df):
    """Create filtered datasets for different scenarios."""
    logger.info("Creating data filters...")

    uni_pos = df[(df["Universal Tier"] == 1) & df["FormularyTier"].isin(["B", "BRAND"])]
    logger.info(f"uni_pos shape: {uni_pos.shape}")

    uni_neg = df[
        df["Universal Tier"].isin([2, 3]) & df["FormularyTier"].isin(["G", "GENERIC"])
    ]
    logger.info(f"uni_neg shape: {uni_neg.shape}")

    ex_pos = df[(df["Exclusive Tier"] == 1) & df["FormularyTier"].isin(["B", "BRAND"])]
    logger.info(f"ex_pos shape: {ex_pos.shape}")

    ex_neg = df[
        df["Exclusive Tier"].isin([2, 3]) & df["FormularyTier"].isin(["G", "GENERIC"])
    ]
    logger.info(f"ex_neg shape: {ex_neg.shape}")

    ex_ex = df[df["Exclusive Tier"] == "Nonformulary"]
    logger.info(f"ex_ex shape: {ex_ex.shape}")

    return uni_pos, uni_neg, ex_pos, ex_neg, ex_ex


def create_pivot_tables(filtered_data):
    """Create pivot tables and calculate member counts."""
    logger.info("Creating pivot tables...")

    uni_pos, uni_neg, ex_pos, ex_neg, ex_ex = filtered_data

    def pivot(d, include_alternative=False):
        index_cols = ["Product Name"]
        if include_alternative and "Alternative" in d.columns:
            index_cols.append("Alternative")
        pt = pd.pivot_table(
            d,
            values=["Rxs", "MemberID"],
            index=index_cols,
            aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique},
        )
        pt = pt.rename(columns={"Rxs": "Total Rxs", "MemberID": "Unique Members"})
        return pt

    def count(d):
        return 0 if d.empty or d["Rxs"].sum() == 0 else d["MemberID"].nunique()

    tabs = {
        "Universal_Positive": (uni_pos, pivot(uni_pos), count(uni_pos)),
        "Universal_Negative": (uni_neg, pivot(uni_neg), count(uni_neg)),
        "Exclusive_Positive": (ex_pos, pivot(ex_pos), count(ex_pos)),
        "Exclusive_Negative": (ex_neg, pivot(ex_neg), count(ex_neg)),
        "Exclusions": (ex_ex, pivot(ex_ex, include_alternative=True), count(ex_ex)),
    }

    return tabs


def create_summary_data(df, tabs):
    """Create summary data for the report."""
    logger.info("Creating summary data...")

    total_members = df["MemberID"].nunique()
    total_claims = df["Rxs"].sum()

    summary = pd.DataFrame(
        {
            "Formulary": [
                "Universal Positive",
                "Universal Negative",
                "Exclusive Positive",
                "Exclusive Negative",
                "Exclusions",
            ],
            "Utilizers": [v[2] for v in tabs.values()],
            "Rxs": [v[0]["Rxs"].sum() for v in tabs.values()],
            "% of claims": [
                v[0]["Rxs"].sum() / total_claims if total_claims else 0
                for v in tabs.values()
            ],
            "": ["" for _ in tabs],
            "Totals": [
                f"Members: {total_members}",
                f"Claims: {total_claims}",
                "",
                "",
                "",
            ],
        }
    )

    return summary


def create_network_data(df):
    """Create network data for excluded pharmacies."""
    logger.info("Creating network data...")

    import re

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
        return network_sheet
    else:
        return None


def write_excel_report(report_data, output_filename):
    """Write the final Excel report."""
    logger.info("Writing Excel report...")
    from utils.utils import write_audit_log

    # Validate output filename
    if not output_filename or not str(output_filename).strip():
        output_filename = "Unknown_Disruption_Report.xlsx"
        logger.warning(
            "Output filename was empty or invalid. Defaulting to 'Unknown_Disruption_Report.xlsx'."
        )
        write_audit_log(
            "bg_disruption.py",
            "Output filename was empty or invalid. Defaulting to 'Unknown_Disruption_Report.xlsx'.",
            "WARNING",
        )

    df, summary, tabs, network_pivot = report_data

    output_path = Path(output_filename)
    writer = pd.ExcelWriter(output_path, engine="xlsxwriter")
    # Write the full filtered DataFrame to the Data tab (no deduplication)
    df.to_excel(writer, sheet_name="Data", index=False)
    summary.to_excel(writer, sheet_name="Summary", index=False)

    for sheet, (_, pt, mems) in tabs.items():
        pt.to_excel(writer, sheet_name=sheet)
        writer.sheets[sheet].write("F1", f"Total Members: {mems}")

    # Write network sheet with dynamic column selection
    if network_pivot is not None:
        selected_columns = [
            "PHARMACYNPI",
            "NABP",
            "MemberID",
            "Pharmacy Name",
            "pharmacy_is_excluded",
            "Unique Identifier",
        ]
        available_columns = [col for col in selected_columns if col in network_pivot.columns]
        missing_columns = [col for col in selected_columns if col not in network_pivot.columns]
        if missing_columns:
            logger.warning(f"Network DataFrame missing columns: {missing_columns}. Only writing available columns: {available_columns}")
            network_pivot[available_columns].to_excel(writer, sheet_name="Network", index=False)
        
        # Log a warning if any expected columns are missing
        if missing_columns:
            logger.warning(f"Network DataFrame missing columns: {missing_columns}. Only writing available columns: {available_columns}")

    # Reorder sheets so Summary follows Data
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

    writer.close()
    logger.info(f"Excel report written to: {output_path}")
    write_audit_log(
        "bg_disruption.py", f"Excel report written to: {output_path}", "INFO"
    )


def show_completion_notification():
    """Show completion notification popup."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()  # Hide the main window
        messagebox.showinfo("Notification", "Processing complete")
        root.destroy()
    except Exception as e:
        logger.warning(f"Popup notification failed: {e}")


def process_data():
    """Main processing function - coordinates all data processing steps."""
    # Get current username
    try:
        username = os.getlogin()
    except Exception:
        username = os.environ.get("USERNAME") or os.environ.get("USER") or "UnknownUser"

    # Start audit session
    log_user_session_start("bg_disruption.py")
    write_audit_log(
        "bg_disruption.py", f"Processing started by user: {username}", "INFO"
    )

    try:
        # Always use 'LBL for Disruption.xlsx' in the current working directory
        output_filename = str(Path.cwd() / "LBL for Disruption.xlsx")

        from config.config_loader import ConfigManager

        config_manager = ConfigManager()
        file_paths = config_manager.get("file_paths.json")
        if "reprice" not in file_paths or not file_paths["reprice"]:
            make_audit_entry(
                "bg_disruption.py", "No reprice/template file provided.", "FILE_ERROR"
            )
            write_audit_log(
                "bg_disruption.py", "No reprice/template file provided.", status="ERROR"
            )
            print("Error: No reprice/template file provided.")
            return

        # Log file access
        log_file_access("bg_disruption.py", file_paths["reprice"], "LOADING")
        write_audit_log(
            "bg_disruption.py",
            f"User {username} loaded file: {file_paths['reprice']}",
            "INFO",
        )

        # Load all data files
        claims, medi, uni, exl, network = load_data_files(file_paths)

        # Merge all data files
        reference_data = (medi, uni, exl)
        df = merge_data_files(claims, reference_data, network)

        # Process and filter data
        df = process_and_filter_data(df)

        # Handle pharmacy exclusions
        df = handle_pharmacy_exclusions(df, file_paths)

        # Also call handle_tier_pharmacy_exclusions to ensure pharmacy validation log is written
        from modules.tier_disruption import handle_tier_pharmacy_exclusions

        handle_tier_pharmacy_exclusions(df, file_paths)

        # Create filtered datasets
        uni_pos, uni_neg, ex_pos, ex_neg, ex_ex = create_data_filters(df)

        # Create pivot tables
        filtered_data = (uni_pos, uni_neg, ex_pos, ex_neg, ex_ex)
        tabs = create_pivot_tables(filtered_data)

        # Create summary data
        summary = create_summary_data(df, tabs)

        # Create network data
        network_pivot = create_network_data(df)

        # Write Excel report
        report_data = (df, summary, tabs, network_pivot)
        write_excel_report(report_data, output_filename)
        # Explicitly confirm creation of LBL for Disruption.xlsx
        if Path(output_filename).name == "LBL for Disruption.xlsx":
            write_audit_log(
                "bg_disruption.py",
                f"LBL for Disruption.xlsx created successfully by user: {username}",
                "INFO",
            )

        # Log successful completion
        make_audit_entry(
            "bg_disruption.py",
            f"Successfully generated report: {output_filename} by user: {username}",
            "INFO",
        )
        log_file_access("bg_disruption.py", output_filename, "CREATED")
        write_audit_log(
            "bg_disruption.py", f"Processing complete for user: {username}", "INFO"
        )
        print("Processing complete")

    except Exception as e:
        # Log any uncaught errors
        make_audit_entry(
            "bg_disruption.py",
            f"Processing failed with error: {str(e)}",
            "SYSTEM_ERROR",
        )
        logger.error(f"Processing failed: {e}")
        raise
    finally:
        # End audit session
        log_user_session_end("bg_disruption.py")

    # Show completion notification
    show_completion_notification()


if __name__ == "__main__":
    process_data()
