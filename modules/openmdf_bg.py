import logging
import pandas as pd
import os  # noqa: E402
import sys
from pathlib import Path
# Ensure project root is in sys.path before importing other modules
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.utils import (  # noqa: E402
    clean_logic_and_tier,
    drop_duplicates_df,
    filter_logic_and_maintenance,
    filter_products_and_alternative,
    filter_recent_date,
    write_audit_log,
)
from modules.audit_helper import (log_file_access,  # noqa: E402
                                  log_user_session_end, log_user_session_start,
                                  make_audit_entry)


# Logging setup
logging.basicConfig(
    filename="openmdf_bg2.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
logger.propagate = False
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

def load_data_files(file_paths):
    logger.info("Loading data files...")

    try:
        claims = pd.read_excel(
            file_paths["reprice"],
            sheet_name="Claims Table",
            usecols=[
                "SOURCERECORDID", "NDC", "MemberID", "DATEFILLED", "FormularyTier",
                "Rxs", "Logic", "PHARMACYNPI", "NABP", "Pharmacy Name",
                "Universal Rebates", "Exclusive Rebates"
            ],
            engine="openpyxl"
        )
    except Exception as e:
        logger.warning(f"Claims Table fallback: {e}")
        make_audit_entry("openmdf_bg2.py", f"Claims Table fallback error: {e}", "FILE_ERROR")
        write_audit_log("openmdf_bg2.py", f"Claims Table fallback: {e}", status="WARNING")
        claims = pd.read_excel(file_paths["reprice"], sheet_name=0, engine="openpyxl")

    logger.info(f"claims shape: {claims.shape}")
    claims.info()

    # Convert ID columns to string for matching
    for col in ["PHARMACYNPI", "NABP"]:
        if col in claims.columns:
            claims[col] = claims[col].astype(str).str.strip()
    # ...existing code...
    claims = clean_logic_and_tier(claims)
    logger.info(f"After clean_logic_and_tier: {claims.shape}")

    # Additional data cleaning steps using utils
    claims = drop_duplicates_df(claims)
    logger.info(f"After drop_duplicates_df: {claims.shape}")

    claims = filter_recent_date(claims)
    logger.info(f"After filter_recent_date: {claims.shape}")

    medi = pd.read_excel(file_paths["medi_span"], engine="openpyxl")
    logger.info(f"medi shape: {medi.shape}")

    mdf = pd.read_excel(file_paths["mdf_disrupt"], sheet_name="Open MDF NDC", engine="openpyxl")[["NDC", "Tier"]]
    logger.info(f"mdf shape: {mdf.shape}")

    exclusive = pd.read_excel(file_paths["e_disrupt"], sheet_name="Alternatives NDC", engine="openpyxl")[["NDC", "Tier", "Alternative"]]
    logger.info(f"exclusive shape: {exclusive.shape}")

    if file_paths["n_disrupt"].lower().endswith(".csv"):
        network = pd.read_csv(
            file_paths["n_disrupt"],
            dtype={"pharmacy_nabp": str, "pharmacy_npi": str, "pharmacy_is_excluded": str}
        )[["pharmacy_nabp", "pharmacy_npi", "pharmacy_is_excluded"]]
    else:
        network = pd.read_excel(file_paths["n_disrupt"], engine="openpyxl")[["pharmacy_nabp", "pharmacy_npi", "pharmacy_is_excluded"]]
    # Convert scientific notation to integer then string, and strip whitespace
    for col in ["pharmacy_npi", "pharmacy_nabp"]:
        if col in network.columns:
            # Remove whitespace
            network[col] = network[col].astype(str).str.strip()
            # Convert scientific notation to integer then string (if possible)
            def sci_to_str(val):
                try:
                    # Remove any decimal, convert to int, then to string
                    return str(int(float(val)))
                except Exception:
                    return str(val)
            network[col] = network[col].apply(sci_to_str)

    # Diagnostics: log value counts and join key samples after network is loaded and cleaned
    logger.info(f"network['pharmacy_is_excluded'] value counts before merge: {network['pharmacy_is_excluded'].value_counts(dropna=False).to_dict()}")
    logger.info(f"Sample network['pharmacy_npi']: {network['pharmacy_npi'].head(10).tolist()}")
    logger.info(f"Sample network['pharmacy_nabp']: {network['pharmacy_nabp'].head(10).tolist()}")
    logger.info(f"network shape: {network.shape}")
    logger.info(f"Raw network['pharmacy_nabp'] sample: {network['pharmacy_nabp'].head(10).tolist()}")
    logger.info(f"Raw network['pharmacy_npi'] sample: {network['pharmacy_npi'].head(10).tolist()}")
    logger.info(f"Unique values in raw network['pharmacy_is_excluded']: {network['pharmacy_is_excluded'].unique()}")

    return claims, medi, mdf, exclusive, network

def merge_data_files(claims, reference_data, network):
    logger.info("Merging data files...")

    medi, mdf, exclusive = reference_data

    df = claims.merge(medi, on="NDC", how="left")
    logger.info(f"After merge with medi: {df.shape}")

    df = df.merge(mdf.rename(columns={"Tier": "Open MDF Tier"}), on="NDC", how="left")
    logger.info(f"After merge with Open MDF: {df.shape}")

    df = df.merge(exclusive.rename(columns={"Tier": "Exclusive Tier"}), on="NDC", how="left")
    logger.info(f"After merge with exclusive: {df.shape}")

    # Create pharmacy_id in both claims and network as in original script
    df['pharmacy_id'] = df.apply(lambda row: str(row['PHARMACYNPI']) if pd.notna(row['PHARMACYNPI']) else str(row['NABP']), axis=1)
    network['pharmacy_id'] = network.apply(lambda row: str(row['pharmacy_npi']) if pd.notna(row['pharmacy_npi']) else str(row['pharmacy_nabp']), axis=1)
    # Merge on pharmacy_id
    df = pd.merge(df, network[['pharmacy_id', 'pharmacy_is_excluded']], on='pharmacy_id', how='left')
    logger.info(f"After merge on pharmacy_id: {df.shape}")
    logger.info(f"Columns after merge: {df.columns.tolist()}")
    if "pharmacy_is_excluded" in df.columns:
        logger.info(f"Sample pharmacy_is_excluded values after merge: {df['pharmacy_is_excluded'].head(10).tolist()}")
        logger.info(f"pharmacy_is_excluded value counts after merge: {df['pharmacy_is_excluded'].value_counts(dropna=False).to_dict()}")

    return df

def handle_pharmacy_exclusions(df, file_paths):
    logger.info("Handling pharmacy exclusions...")

    if "pharmacy_is_excluded" in df.columns:
        logger.info(f"Unique values in pharmacy_is_excluded before mapping: {df['pharmacy_is_excluded'].unique()}")

        def map_excluded(val):
            if pd.isna(val) or str(val).strip() == "":
                return "REVIEW"
            v = str(val).strip().lower()
            if v in {"yes", "y", "true", "1"}:
                return True
            elif v in {"no", "n", "false", "0"}:
                return False
            # Unexpected values map to REVIEW
            logger.warning(f"Unexpected pharmacy_is_excluded value encountered: {val}")
            return "REVIEW"

        df["pharmacy_is_excluded"] = df["pharmacy_is_excluded"].apply(map_excluded)
        logger.info(f"pharmacy_is_excluded value counts: {df['pharmacy_is_excluded'].value_counts(dropna=False).to_dict()}")

        unknown_mask = df["pharmacy_is_excluded"].isna()
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
                    
                    combined_df = pd.concat([existing_df, unknown_pharmacies_output], ignore_index=True)
                    combined_df = combined_df.drop_duplicates()
                else:
                    combined_df = unknown_pharmacies_output

                # Save based on file extension
                if str(output_path).lower().endswith('.csv'):
                    combined_df.to_csv(output_path, index=False, encoding='utf-8')
                else:
                    combined_df.to_excel(output_path, index=False)
                logger.info(f"Unknown/NA pharmacies written to '{output_path}' with Result column.")

            except Exception as e:
                logger.error(f"Error updating pharmacy validation file: {e}")
                make_audit_entry("openmdf_bg2.py", f"Pharmacy validation file update error: {e}", "FILE_ERROR")
                unknown_pharmacies_output.to_excel(output_file_path, index=False)
                logger.info(f"Unknown/NA pharmacies written to '{output_file_path}' (fallback mode).")

    return df


def create_data_filters(df):
    """Create filtered datasets for different scenarios."""
    logger.info("Creating data filters...")

    # For Open MDF, use 'Open MDF Tier' instead of 'Universal Tier'
    uni_pos = df[(df["Open MDF Tier"] == 1) & df["FormularyTier"].isin(["B", "BRAND"])]
    logger.info(f"uni_pos shape: {uni_pos.shape}")

    uni_neg = df[
        df["Open MDF Tier"].isin([2, 3]) & df["FormularyTier"].isin(["G", "GENERIC"])
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

    # Network summary for excluded pharmacies (pharmacy_is_excluded==True)
    if "pharmacy_is_excluded" not in df.columns:
        logger.warning("pharmacy_is_excluded column missing from DataFrame. Network sheet will be empty.")
        return None
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

    # Regex safety: escape and lower-case all phrases and names
    filter_phrases_escaped = [re.escape(phrase.lower()) for phrase in filter_phrases]
    regex_pattern = "|".join([f"\\b{p}\\b" for p in filter_phrases_escaped])
    network_df = network_df[
        ~network_df["Pharmacy Name"]
        .str.lower()
        .str.contains(regex_pattern, case=False, regex=True, na=False)
    ]
    logger.info(f"network_df shape after exclusion: {network_df.shape}")

    # Build network sheet as a DataFrame with required columns
    if {"PHARMACYNPI", "NABP", "Pharmacy Name", "MemberID", "Rxs", "pharmacy_is_excluded"}.issubset(network_df.columns):
        # Fill missing IDs with 'N/A' for both columns
        network_df["PHARMACYNPI"] = network_df["PHARMACYNPI"].replace([None, '', pd.NA, float('nan')], "N/A")
        network_df["NABP"] = network_df["NABP"].replace([None, '', pd.NA, float('nan')], "N/A")
        # Build the network sheet row-by-row, no grouping
        network_sheet = network_df[["PHARMACYNPI", "NABP", "Pharmacy Name", "MemberID", "Rxs", "pharmacy_is_excluded"]].copy()
        network_sheet = network_sheet.rename(columns={"MemberID": "Unique Members", "Rxs": "Total Rxs"})
        # Drop duplicates so each pharmacy only appears once
        network_sheet = network_sheet.drop_duplicates(subset=["PHARMACYNPI", "NABP", "Pharmacy Name"])
    else:
        network_sheet = None

    # Log debug info to verify the filtering
    total_pharmacies = df.shape[0]
    logger.info(f"pharmacy_is_excluded value counts: {df['pharmacy_is_excluded'].value_counts().to_dict()}")
    excluded_count = df['pharmacy_is_excluded'].apply(lambda x: x is True).sum()
    review_count = (df['pharmacy_is_excluded'] == "REVIEW").sum()
    non_excluded_count = df['pharmacy_is_excluded'].apply(lambda x: x is False).sum()
    logger.info(f"Total pharmacies in dataset: {total_pharmacies}")
    logger.info(f"Excluded pharmacies ('yes'): {excluded_count}")
    logger.info(f"Review pharmacies ('REVIEW'): {review_count}")
    logger.info(f"Non-excluded pharmacies ('no'): {non_excluded_count}")
    logger.info(f"Sanity check: Excluded + Review + Non-excluded = {excluded_count + review_count + non_excluded_count} (should match total)")
    logger.info(
        f"Network sheet will show {network_df.shape[0]} excluded pharmacy records (minus major chains)"
    )

    return network_sheet


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
            "openmdf_bg2.py",
            "Output filename was empty or invalid. Defaulting to 'Unknown_Disruption_Report.xlsx'.",
            "WARNING",
        )

    df, summary, tabs, network_pivot = report_data

    output_path = Path(output_filename)
    writer = pd.ExcelWriter(output_path, engine="xlsxwriter")
    # Match openmdf_bg.py sheet names
    # Write the full DataFrame to the Claims Data sheet (no deduplication)
    df.to_excel(writer, sheet_name="Claims Data", index=False)
    summary.to_excel(writer, sheet_name="Summary", index=False)

    # Write positive/negative sheets with matching names
    if "Universal_Positive" in tabs:
        tabs["Universal_Positive"][1].to_excel(writer, sheet_name="OpenMDF_Positive")
        writer.sheets["OpenMDF_Positive"].write("F1", f"Total Members: {tabs['Universal_Positive'][2]}")
    if "Universal_Negative" in tabs:
        tabs["Universal_Negative"][1].to_excel(writer, sheet_name="OpenMDF_Negative")
        writer.sheets["OpenMDF_Negative"].write("F1", f"Total Members: {tabs['Universal_Negative'][2]}")

    # Write other tabs as additional sheets (optional)
    for sheet in [k for k in tabs if k not in ["Universal_Positive", "Universal_Negative"]]:
        tabs[sheet][1].to_excel(writer, sheet_name=sheet)
        writer.sheets[sheet].write("F1", f"Total Members: {tabs[sheet][2]}")

    # Write network sheet with matching columns
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

    # Reorder sheets so Summary follows Claims Data
    sheets = writer.sheets  # This is a dict: {sheet_name: worksheet_object}
    names = list(sheets.keys())
    if "Claims Data" in names and "Summary" in names:
        data_idx = names.index("Claims Data")
        summary_idx = names.index("Summary")
        if summary_idx != data_idx + 1:
            # Move "Summary" sheet immediately after "Claims Data"
            items = list(sheets.items())
            summary_item = items.pop(summary_idx)
            items.insert(data_idx + 1, summary_item)
            writer.sheets.clear()
            writer.sheets.update(dict(items))

    writer.close()
    logger.info(f"Excel report written to: {output_path}")
    write_audit_log(
        "openmdf_bg2.py", f"Excel report written to: {output_path}", "INFO"
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
    log_user_session_start("openmdf_bg2.py")
    write_audit_log(
    "openmdf_bg2.py", f"Processing started by user: {username}", "INFO"
    )

    try:
        # Always use 'LBL for Disruption.xlsx' in the current working directory
        output_filename = str(Path.cwd() / "LBL for Disruption.xlsx")

        from config.config_loader import ConfigManager

        config_manager = ConfigManager()
        file_paths = config_manager.get("file_paths.json")
        if "reprice" not in file_paths or not file_paths["reprice"]:
            make_audit_entry(
                "openmdf_bg2.py", "No reprice/template file provided.", "FILE_ERROR"
            )
            write_audit_log(
                "openmdf_bg2.py", "No reprice/template file provided.", status="ERROR"
            )
            print("Error: No reprice/template file provided.")
            return

        # Log file access
        log_file_access("openmdf_bg2.py", file_paths["reprice"], "LOADING")
        write_audit_log(
            "openmdf_bg2.py",
            f"User {username} loaded file: {file_paths['reprice']}",
            "INFO",
        )

        # Load all data files
        claims, medi, mdf, exclusive, network = load_data_files(file_paths)

        # Merge all data files
        reference_data = (medi, mdf, exclusive)
        df = merge_data_files(claims, reference_data, network)

    # Process and filter data
    # If you need to process and filter, use your own logic or call a defined function here
    # Example: df = handle_pharmacy_exclusions(df, file_paths)

        # Handle pharmacy exclusions
        df = handle_pharmacy_exclusions(df, file_paths)

        # Also call handle_tier_pharmacy_exclusions to ensure pharmacy validation log is written
        from modules.tier_disruption import handle_tier_pharmacy_exclusions

        handle_tier_pharmacy_exclusions(df, file_paths)

        # Create filtered datasets
            # Apply additional filters as in bg_disruption.py
        df = filter_logic_and_maintenance(df)
        df = filter_products_and_alternative(df)
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
                "openmdf_bg2.py",
                f"LBL for Disruption.xlsx created successfully by user: {username}",
                "INFO",
            )

        # Log successful completion
        make_audit_entry(
            "openmdf_bg2.py",
            f"Successfully generated report: {output_filename} by user: {username}",
            "INFO",
        )
        log_file_access("openmdf_bg2.py", output_filename, "CREATED")
        write_audit_log(
            "openmdf_bg2.py", f"Processing complete for user: {username}", "INFO"
        )
        print("Processing complete")

    except Exception as e:
        # Log any uncaught errors
        make_audit_entry(
            "openmdf_bg2.py",
            f"Processing failed with error: {str(e)}",
            "SYSTEM_ERROR",
        )
        logger.error(f"Processing failed: {e}")
        raise
    finally:
        # End audit session
        log_user_session_end("openmdf_bg2.py")

    # Show completion notification
    show_completion_notification()


if __name__ == "__main__":
    process_data()