import pandas as pd
import logging
import os
import sys
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import (
    load_file_paths,
    filter_logic_and_maintenance,
    filter_products_and_alternative,
    standardize_pharmacy_ids,
    standardize_network_ids,
    merge_with_network,
    drop_duplicates_df,
    clean_logic_and_tier,
    filter_recent_date,
    write_shared_log,
)
from modules.audit_helper import (
    make_audit_entry,
    log_user_session_start,
    log_user_session_end,
    log_file_access,
)

# Logging setup
logging.basicConfig(
    filename="bg_disruption.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


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
        make_audit_entry("bg_disruption.py", f"Claims Table fallback error: {e}", "FILE_ERROR")
        write_shared_log(
            "bg_disruption.py", f"Claims Table fallback: {e}", status="WARNING"
        )
        claims = pd.read_excel(file_paths["reprice"], sheet_name=0)
    
    logger.info(f"claims shape: {claims.shape}")
    claims.info()

    # Load other data files
    medi = pd.read_excel(file_paths["medi_span"])[
        ["NDC", "Maint Drug?", "Product Name"]
    ]
    logger.info(f"medi shape: {medi.shape}")
    
    uni = pd.read_excel(file_paths["u_disrupt"], sheet_name="Universal NDC")[
        ["NDC", "Tier"]
    ]
    logger.info(f"uni shape: {uni.shape}")
    
    exl = pd.read_excel(file_paths["e_disrupt"], sheet_name="Alternatives NDC")[
        ["NDC", "Tier", "Alternative"]
    ]
    logger.info(f"exl shape: {exl.shape}")
    
    network = pd.read_excel(file_paths["n_disrupt"])[
        ["pharmacy_npi", "pharmacy_nabp", "pharmacy_is_excluded"]
    ]
    logger.info(f"network shape: {network.shape}")
    
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

    # Standardize IDs and perform network merge
    df = standardize_pharmacy_ids(df)
    logger.info(f"After standardize_pharmacy_ids: {df.shape}")
    network = standardize_network_ids(network)
    logger.info(f"After standardize_network_ids: {network.shape}")
    df = merge_with_network(df, network)
    logger.info(f"After merge_with_network: {df.shape}")
    
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
        df["pharmacy_is_excluded"] = (
            df["pharmacy_is_excluded"]
            .astype(str)
            .str.lower()
            .map({"true": True, "false": False})
            .fillna(False)
            .infer_objects(copy=False)
        )
        logger.info(
            f"pharmacy_is_excluded value counts: {df['pharmacy_is_excluded'].value_counts().to_dict()}"
        )
        
        # Identify rows where pharmacy_is_excluded is "NA"
        na_pharmacies = df[df["pharmacy_is_excluded"].isna()]
        logger.info(f"NA pharmacies count: {na_pharmacies.shape[0]}")

        if not na_pharmacies.empty:
            # Define the writer before using it
            output_file_path = file_paths["pharmacy_validation"]
            na_pharmacies_output = na_pharmacies[["PHARMACYNPI", "NABP"]].fillna("N/A")
            # Add Result column with "NA" value
            na_pharmacies_output["Result"] = "NA"
            
            # Use pandas to write to Excel, which is simpler and more reliable
            try:
                # Try to append to existing file
                if os.path.exists(output_file_path):
                    # Read existing data
                    existing_df = pd.read_excel(output_file_path)
                    # Concatenate with new data
                    combined_df = pd.concat([existing_df, na_pharmacies_output], ignore_index=True)
                    # Remove duplicates
                    combined_df = combined_df.drop_duplicates()
                else:
                    combined_df = na_pharmacies_output
                
                # Write to Excel
                combined_df.to_excel(output_file_path, index=False)
                logger.info(f"NA pharmacies written to '{output_file_path}' with Result column.")
                
            except Exception as e:
                logger.error(f"Error updating pharmacy validation file: {e}")
                make_audit_entry("bg_disruption.py", f"Pharmacy validation file update error: {e}", "FILE_ERROR")
                # Fallback - just write the new data
                na_pharmacies_output.to_excel(output_file_path, index=False)
                logger.info(f"NA pharmacies written to '{output_file_path}' (fallback mode).")
    
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
    
    # Network summary for excluded pharmacies (pharmacy_is_excluded=True)
    network_df = df[df["pharmacy_is_excluded"]]
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
    
    network_pivot = None
    if {"PHARMACYNPI", "NABP", "Pharmacy Name"}.issubset(network_df.columns):
        network_df["PHARMACYNPI"] = network_df["PHARMACYNPI"].fillna("N/A")
        network_df["NABP"] = network_df["NABP"].fillna("N/A")
        network_pivot = pd.pivot_table(
            network_df,
            values=["Rxs", "MemberID"],
            index=["PHARMACYNPI", "NABP", "Pharmacy Name"],
            aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique},
        )
        network_pivot = network_pivot.rename(
            columns={"Rxs": "Total Rxs", "MemberID": "Unique Members"}
        )
    
    # Log debug info to verify the filtering
    logger.info(f"Total pharmacies in dataset: {df.shape[0]}")
    logger.info(
        f"Excluded pharmacies (pharmacy_is_excluded=True): {df['pharmacy_is_excluded'].sum()}"
    )
    logger.info(
        f"Non-excluded pharmacies (pharmacy_is_excluded=False): {(~df['pharmacy_is_excluded']).sum()}"
    )
    logger.info(
        f"Network sheet will show {network_df.shape[0]} excluded pharmacy records (minus major chains)"
    )
    
    return network_pivot


def write_excel_report(report_data, output_filename):
    """Write the final Excel report."""
    logger.info("Writing Excel report...")
    
    df, summary, tabs, network_pivot = report_data
    
    writer = pd.ExcelWriter(output_filename, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Data", index=False)
    summary.to_excel(writer, sheet_name="Summary", index=False)

    for sheet, (_, pt, mems) in tabs.items():
        pt.to_excel(writer, sheet_name=sheet)
        writer.sheets[sheet].write("F1", f"Total Members: {mems}")

    if network_pivot is not None:
        network_pivot.to_excel(writer, sheet_name="Network")

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
    # Start audit session
    log_user_session_start("bg_disruption.py")
    write_shared_log("bg_disruption.py", "Processing started.")
    
    try:
        import sys

        output_filename = "LBL for Disruption.xlsx"
        if len(sys.argv) > 1:
            output_filename = sys.argv[1]
        
        # Get the config file path relative to the project root
        config_path = Path(__file__).parent.parent / "config" / "file_paths.json"
        file_paths = load_file_paths(str(config_path))
        if "reprice" not in file_paths or not file_paths["reprice"]:
            make_audit_entry("bg_disruption.py", "No reprice/template file provided.", "FILE_ERROR")
            write_shared_log(
                "bg_disruption.py", "No reprice/template file provided.", status="ERROR"
            )
            print("Error: No reprice/template file provided.")
            return

        # Log file access
        log_file_access("bg_disruption.py", file_paths["reprice"], "LOADING")
        
        # Load all data files
        claims, medi, uni, exl, network = load_data_files(file_paths)
        
        # Merge all data files
        reference_data = (medi, uni, exl)
        df = merge_data_files(claims, reference_data, network)
        
        # Process and filter data
        df = process_and_filter_data(df)
        
        # Handle pharmacy exclusions
        df = handle_pharmacy_exclusions(df, file_paths)
        
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
        
        # Log successful completion
        make_audit_entry("bg_disruption.py", f"Successfully generated report: {output_filename}", "INFO")
        log_file_access("bg_disruption.py", output_filename, "CREATED")
        
        write_shared_log("bg_disruption.py", "Processing complete.")
        print("Processing complete")
        
    except Exception as e:
        # Log any uncaught errors
        make_audit_entry("bg_disruption.py", f"Processing failed with error: {str(e)}", "SYSTEM_ERROR")
        logger.error(f"Processing failed: {e}")
        raise
    finally:
        # End audit session
        log_user_session_end("bg_disruption.py")
    
    # Show completion notification
    show_completion_notification()


if __name__ == "__main__":
    process_data()
