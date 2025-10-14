import logging
import sys
from pathlib import Path

import pandas as pd

# Ensure project root is in sys.path before importing project_settings
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    from project_settings import PROJECT_ROOT

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))
from modules.audit_helper import (log_file_access,  # noqa: E402
                                  log_user_session_end, log_user_session_start,
                                  make_audit_entry)
from utils.utils import (clean_logic_and_tier,  # noqa: E402
                         drop_duplicates_df, filter_logic_and_maintenance,
                         filter_products_and_alternative, filter_recent_date,
                         write_audit_log)

# Logging setup
logging.basicConfig(
    filename="openmdf_tier.log",
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



# ---------------------------------------------------------------------------
# Open MDF Tier processing functions
# ---------------------------------------------------------------------------
def load_openmdf_tier_data(file_paths):
    """Load all required data files for Open MDF tier disruption processing."""
    # Load claims with fallback
    if not file_paths.get("reprice"):
        write_audit_log(
            "openmdf_tier.py",
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
            "openmdf_tier.py", f"Claims Table fallback error: {e}", "FILE_ERROR"
        )
        claims = pd.read_excel(file_paths["reprice"], sheet_name=0)

    print(f"claims shape: {claims.shape}")
    claims.info()

    # Load reference tables
    try:
        medi = pd.read_excel(file_paths["medi_span"])[
            ["NDC", "Maint Drug?", "Product Name"]
        ]
        print(f"medi shape: {medi.shape}")
    except Exception as e:
        logger.error(f"Failed to read medi_span file: {file_paths['medi_span']} | {e}")
        write_audit_log(
            "openmdf_tier.py",
            f"Failed to read medi_span file: {file_paths['medi_span']} | {e}",
            status="ERROR",
        )
        return None

    try:
        mdf = pd.read_excel(file_paths["mdf_disrupt"], sheet_name="Open MDF NDC")[
            ["NDC", "Tier"]
        ]
        print(f"mdf shape: {mdf.shape}")
    except Exception as e:
        logger.error(
            f"Failed to read mdf_disrupt file: {file_paths['mdf_disrupt']} | {e}"
        )
        write_audit_log(
            "openmdf_tier.py",
            f"Failed to read mdf_disrupt file: {file_paths['mdf_disrupt']} | {e}",
            status="ERROR",
        )
        return None

    try:
        exclusive = pd.read_excel(
            file_paths["e_disrupt"], sheet_name="Alternatives NDC"
        )[["NDC", "Tier", "Alternative"]]
    except Exception as e:
        logger.error(f"Failed to read e_disrupt file: {file_paths['e_disrupt']} | {e}")
        write_audit_log(
            "openmdf_tier.py",
            f"Failed to read e_disrupt file: {file_paths['e_disrupt']} | {e}",
            status="ERROR",
        )
        return None

    try:
        if file_paths["n_disrupt"].lower().endswith(".csv"):
            network = pd.read_csv(file_paths["n_disrupt"])[
                ["pharmacy_nabp", "pharmacy_npi", "pharmacy_is_excluded"]
            ]
        else:
            network = pd.read_excel(file_paths["n_disrupt"])[
                ["pharmacy_nabp", "pharmacy_npi", "pharmacy_is_excluded"]
            ]
        print(f"network shape: {network.shape}")
        print(f"Raw network['pharmacy_nabp'] sample: {network['pharmacy_nabp'].head(10).tolist()}")
        print(f"Raw network['pharmacy_npi'] sample: {network['pharmacy_npi'].head(10).tolist()}")
        print(f"Unique values in raw network['pharmacy_is_excluded']: {network['pharmacy_is_excluded'].unique()}")
    except Exception as e:
        logger.error(f"Failed to read n_disrupt file: {file_paths['n_disrupt']} | {e}")
        write_audit_log(
            "openmdf_tier.py",
            f"Failed to read n_disrupt file: {file_paths['n_disrupt']} | {e}",
            status="ERROR",
        )
        return None

    return claims, medi, mdf, exclusive, network


def process_openmdf_data_pipeline(claims, reference_data, network):
    """Process the data pipeline for Open MDF tier disruption."""
    medi, mdf, exclusive = reference_data

    # Merge reference data
    df = claims.merge(medi, on="NDC", how="left")
    print(f"After merge with medi: {df.shape}")
    df = df.merge(mdf.rename(columns={"Tier": "Open MDF Tier"}), on="NDC", how="left")
    print(f"After merge with mdf: {df.shape}")
    df = df.merge(exclusive.rename(columns={"Tier": "Exclusive Tier"}), on="NDC", how="left")
    print(f"After merge with exclusive: {df.shape}")
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
    df["PHARMACYNPI"] = df["PHARMACYNPI"].replace([np.nan, '', float('nan')], "N/A").fillna("N/A")
    df["NABP"] = df["NABP"].replace(['', float('nan')], "N/A").fillna("N/A")

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


def handle_openmdf_pharmacy_exclusions(df, file_paths):
    """Handle pharmacy exclusions for Open MDF tier disruption."""
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
                output_file_path_obj = Path(output_file_path)
                if output_file_path_obj.exists():
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
                    
                    combined_df = pd.concat(
                        [existing_df, unknown_pharmacies_output], ignore_index=True
                    )
                    combined_df = combined_df.drop_duplicates()
                else:
                    combined_df = unknown_pharmacies_output

                # Save based on file extension
                if str(output_file_path_obj).lower().endswith('.csv'):
                    combined_df.to_csv(output_file_path_obj, index=False, encoding='utf-8')
                else:
                    combined_df.to_excel(output_file_path_obj, index=False)
                logger.info(
                    f"Unknown/NA pharmacies written to '{output_file_path_obj}' with Result column."
                )

            except Exception as e:
                logger.error(f"Error updating pharmacy validation file: {e}")
                # Fallback - just write the new data
                unknown_pharmacies_output.to_excel(output_file_path, index=False)
                logger.info(
                    f"Unknown/NA pharmacies written to '{output_file_path}' (fallback mode)."
                )
                # Fallback to original method
                writer = pd.ExcelWriter(output_file_path, engine="openpyxl")
                unknown_pharmacies_output.to_excel(
                    writer, sheet_name="Validations", index=False, engine="openpyxl"
                )
                writer.close()
                logger.info(
                    f"NA pharmacies written to '{output_file_path}' sheet (fallback)."
                )

    return df


def create_openmdf_tier_definitions():
    """Create the Open MDF tier definitions for analysis."""
    return [
        ("OpenMDF_Positive 2-1", "Open MDF Tier", 1, 2),
        ("OpenMDF_Positive 3-1", "Open MDF Tier", 1, 3),
        ("OpenMDF_Positive 3-2", "Open MDF Tier", 2, 3),
        ("OpenMDF_Negative 1-2", "Open MDF Tier", 2, 1),
        ("OpenMDF_Negative 1-3", "Open MDF Tier", 3, 1),
        ("OpenMDF_Negative 2-3", "Open MDF Tier", 3, 2),
    ]


def summarize_by_openmdf_tier(df, col, from_val, to_val):
    """Summarize Open MDF tier data."""
    
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


def process_openmdf_tier_pivots(df, tiers):
    """Process Open MDF tier pivot tables and collect statistics."""
    tab_members = {}
    tab_rxs = {}
    tier_pivots = []

    for name, col, from_val, to_val in tiers:
        pt, rxs, members = summarize_by_openmdf_tier(df, col, from_val, to_val)
        tier_pivots.append((name, pt, members, rxs))
        tab_members[name] = members
        tab_rxs[name] = rxs

    return tier_pivots, tab_members, tab_rxs


def create_openmdf_summary_dataframe(tab_members, tab_rxs, total_claims, total_members):
    """Create the Open MDF summary DataFrame with calculated statistics."""
    pos_keys = [
        "OpenMDF_Positive 2-1",
        "OpenMDF_Positive 3-1",
        "OpenMDF_Positive 3-2",
    ]
    neg_keys = [
        "OpenMDF_Negative 1-2",
        "OpenMDF_Negative 1-3",
        "OpenMDF_Negative 2-3",
    ]

    pos_utilizers = sum(tab_members[k] for k in pos_keys)
    pos_claims = sum(tab_rxs[k] for k in pos_keys)
    pos_pct = pos_claims / total_claims if total_claims else 0

    neg_utilizers = sum(tab_members[k] for k in neg_keys)
    neg_claims = sum(tab_rxs[k] for k in neg_keys)
    neg_pct = neg_claims / total_claims if total_claims else 0

    return pd.DataFrame(
        {
            "Formulary": [
                "Open MDF Positive",
                "Open MDF Negative",
            ],
            "Utilizers": [
                pos_utilizers,
                neg_utilizers,
            ],
            "Rxs": [
                pos_claims,
                neg_claims,
            ],
            "% of claims": [
                pos_pct,
                neg_pct,
            ],
            "": ["", ""],
            "Totals": [
                f"Members: {total_members}",
                f"Claims: {total_claims}",
            ],
        }
    )


def create_openmdf_network_analysis(df):
    """Create network analysis for excluded pharmacies."""
    # Ensure any blanks in pharmacy_is_excluded are marked as 'REVIEW' before filtering
    df["pharmacy_is_excluded"] = df["pharmacy_is_excluded"].replace([None, '', pd.NA], "REVIEW")
    # Only include rows where pharmacy_is_excluded is True or REVIEW
    network_df = df[df["pharmacy_is_excluded"].isin([True, "REVIEW"])]
    import re
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


def write_openmdf_excel_sheets(
    writer, df, summary_df, tier_pivots, network_df, network_pivot
):
    """Write all sheets to the Excel file."""
    # Write Summary sheet
    summary_df.to_excel(writer, sheet_name="Summary", index=False)

    # Write tier pivots
    for name, pt, members, _ in tier_pivots:
        pt.to_excel(writer, sheet_name=name)
        writer.sheets[name].write("F1", f"Total Members: {members}")

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
    else:
        logger.info("Network sheet not written because network_df is None")
def reorder_openmdf_excel_sheets(writer):
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


def show_openmdf_completion_message(output_path):
    """Show completion message and popup."""
    write_audit_log("openmdf_tier.py", "Processing complete.")
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
    # Start audit session
    log_user_session_start("openmdf_tier.py")
    write_audit_log("openmdf_tier.py", "Processing started.")

    # Always use 'LBL for Disruption.xlsx' in the current working directory
    output_path = Path.cwd() / "LBL for Disruption.xlsx"

    try:
        # Get the config file path relative to the project root
        from config.config_loader import ConfigManager

        config_manager = ConfigManager()
        file_paths = config_manager.get("file_paths.json")

        result = load_openmdf_tier_data(file_paths)
        if result is None:
            make_audit_entry(
                "openmdf_tier.py", "Claims loading failed - early exit", "DATA_ERROR"
            )
            return  # Early exit if claims loading failed
        claims, medi, mdf, exclusive, network = result

        # Log file access
        log_file_access(
            "openmdf_tier.py", file_paths.get("reprice", "unknown"), "LOADING"
        )

        reference_data = (medi, mdf, exclusive)
        df = process_openmdf_data_pipeline(claims, reference_data, network)

        # Also call handle_tier_pharmacy_exclusions to ensure pharmacy validation log is written
        from modules.tier_disruption import handle_tier_pharmacy_exclusions

        handle_tier_pharmacy_exclusions(df, file_paths)

        # Convert FormularyTier to numeric for proper filtering
        df["FormularyTier"] = pd.to_numeric(df["FormularyTier"], errors="coerce")

        # Totals for summary
        total_claims = df["Rxs"].sum()
        total_members = df["MemberID"].nunique()

        # Log data processing metrics
        make_audit_entry(
            "openmdf_tier.py",
            f"Processed {total_claims} claims for {total_members} members",
            "INFO",
        )

        # Excel writer setup
        writer = pd.ExcelWriter(output_path, engine="xlsxwriter")

        # Summary calculations (must be written immediately after Data)
        tiers = create_openmdf_tier_definitions()

        tier_pivots, tab_members, tab_rxs = process_openmdf_tier_pivots(df, tiers)

        # Summary calculations
        summary_df = create_openmdf_summary_dataframe(
            tab_members, tab_rxs, total_claims, total_members
        )
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        # Write tier pivots after Summary
        for name, pt, members, _ in tier_pivots:
            pt.to_excel(writer, sheet_name=name)
            writer.sheets[name].write("F1", f"Total Members: {members}")

        # Write the 'Data Sheet' with excluded and non-excluded pharmacies
        data_sheet_df = df.copy()
        data_sheet_df.to_excel(writer, sheet_name="Data", index=False)

        # Network summary for excluded pharmacies (pharmacy_is_excluded="yes")
        logger.info("Processing network analysis...")
        network_df, network_pivot = create_openmdf_network_analysis(df)
        total_pharmacies = df.shape[0]
        logger.info(f"pharmacy_is_excluded value counts: {df['pharmacy_is_excluded'].value_counts().to_dict()}")
        excluded_count = df['pharmacy_is_excluded'].sum()
        non_excluded_count = (~df['pharmacy_is_excluded'].astype(bool)).sum()
        logger.info(f"Total pharmacies in dataset: {total_pharmacies}")
        logger.info(f"Excluded pharmacies ('yes'): {excluded_count}")
        logger.info(f"Non-excluded pharmacies ('no'): {non_excluded_count}")
        logger.info(f"Sanity check: Excluded + Non-excluded = {excluded_count + non_excluded_count} (should match total)")
        if network_df is not None:
            logger.info(
                f"Network sheet will show {network_df.shape[0]} excluded pharmacy records (minus major chains)"
            )
        else:
            logger.info("Network sheet will show 0 excluded pharmacy records (minus major chains)")

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
            network_df[selected_columns].to_excel(writer, sheet_name="Network", index=False)
            logger.info(
                f"Network sheet updated with {network_df.shape[0]} excluded pharmacy records (minus major chains) and selected columns"
            )
        else:
            logger.info("Network sheet not written: network_df is None.")

        # Reorder sheets so Summary follows Data
        reorder_openmdf_excel_sheets(writer)

        writer.close()
        # Log successful completion
        make_audit_entry(
            "openmdf_tier.py",
            f"Successfully generated Open MDF Tier report: {str(output_path)}",
            "INFO",
        )
        log_file_access("openmdf_tier.py", str(output_path), "CREATED")

        show_openmdf_completion_message(output_path)

    except Exception as e:
        # Log detailed error information
        make_audit_entry(
            "openmdf_tier.py", f"Processing failed with error: {str(e)}", "SYSTEM_ERROR"
        )
        write_audit_log("openmdf_tier.py", f"Processing failed: {e}", status="ERROR")
        raise
    finally:
        # End audit session
        log_user_session_end("openmdf_tier.py")


if __name__ == "__main__":
    process_data()
    print("Data processing complete")
