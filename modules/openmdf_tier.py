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
                         merge_with_network, standardize_network_ids,
                         standardize_pharmacy_ids, write_audit_log)

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

# Load NABP/NPI list
included_nabp_npi = {
    "4528874": "1477571404",
    "2365422": "1659313435",
    "3974157": "1972560688",
    "320793": "1164437406",
    "4591055": "1851463087",
    "2348046": "1942303110",
    "4023610": "1407879588",
    "4025385": "1588706212",
    "4025311": "1588705446",
    "4026806": "1285860312",
    "4931350": "1750330775",
    "4024585": "1396768461",
    "4028026": "1497022438",
    "2643749": "1326490376",
}


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
                ["pharmacy_npi", "pharmacy_nabp", "pharmacy_is_excluded"]
            ]
        else:
            network = pd.read_excel(file_paths["n_disrupt"])[
                ["pharmacy_npi", "pharmacy_nabp", "pharmacy_is_excluded"]
            ]
        print(f"network shape: {network.shape}")
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

    df = df.merge(
        exclusive.rename(columns={"Tier": "Exclusive Tier"}), on="NDC", how="left"
    )
    print(f"After merge with exclusive: {df.shape}")

    # Standardize IDs and perform network merge
    df = standardize_pharmacy_ids(df)
    print(f"After standardize_pharmacy_ids: {df.shape}")
    network = standardize_network_ids(network)
    print(f"After standardize_network_ids: {network.shape}")
    df = merge_with_network(df, network)
    print(f"After merge_with_network: {df.shape}")

    if "pharmacy_id" not in df.columns:
        df["pharmacy_id"] = df.apply(
            lambda row: (
                row["PHARMACYNPI"] if pd.notna(row["PHARMACYNPI"]) else row["NABP"]
            ),
            axis=1,
        )

    print("Columns in df before further processing:")
    print(df.columns)

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
        # Only 'yes' and 'no' (case-insensitive) are mapped; blanks/unknowns become NaN for manual review
        df["pharmacy_is_excluded"] = (
            df["pharmacy_is_excluded"]
            .astype(str)
            .str.strip().str.lower()
            .map({"yes": True, "no": False})
        )
        logger.info(
            f"pharmacy_is_excluded value counts: {df['pharmacy_is_excluded'].value_counts().to_dict()}"
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
                    existing_df = pd.read_csv(output_file_path_obj)
                    combined_df = pd.concat(
                        [existing_df, unknown_pharmacies_output], ignore_index=True
                    )
                    combined_df = combined_df.drop_duplicates()
                else:
                    combined_df = unknown_pharmacies_output

                # Write to CSV
                combined_df.to_csv(output_file_path_obj, index=False)
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
    network_df = df[df["pharmacy_is_excluded"].fillna(False)]
    logger.debug(f"Initial network_df shape: {network_df.shape}")
    logger.debug(f"Initial network_df contents: {network_df.head(10).to_dict()}")

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
    regex_pattern = "|".join([f"\\b{p}\\b" for p in filter_phrases_escaped])
    network_df = network_df[
        ~network_df["Pharmacy Name"]
        .str.lower()
        .str.contains(regex_pattern, case=False, regex=True, na=False)
    ]
    logger.debug(f"Filtered network_df shape: {network_df.shape}")
    logger.debug(f"Filtered network_df contents: {network_df.head(10).to_dict()}")

    if {"PHARMACYNPI", "NABP", "Pharmacy Name"}.issubset(network_df.columns):
        network_df["PHARMACYNPI"] = network_df["PHARMACYNPI"].fillna("N/A")
        network_df["NABP"] = network_df["NABP"].fillna("NABP")
        # Create Unique Identifier based on whichever identifier is available (PHARMACYNPI or NABP)
        network_df["Unique Identifier"] = network_df.apply(
            lambda row: (
                row["PHARMACYNPI"] if row["PHARMACYNPI"] != "N/A" else row["NABP"]
            ),
            axis=1,
        )
        network_pivot = pd.pivot_table(
            network_df,
            values=["Rxs", "MemberID"],
            index=["Unique Identifier"],
            aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique},
        )
        network_pivot = network_pivot.rename(
            columns={"Rxs": "Total Rxs", "MemberID": "Unique Members"}
        )
        network_pivot.reset_index(
            inplace=True
        )  # Ensure index columns are included in the output
        logger.debug(f"Network pivot shape: {network_pivot.shape}")
        logger.debug(f"Network pivot contents: {network_pivot.head(10).to_dict()}")

        return network_df, network_pivot

    return network_df, None


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
    network_df[selected_columns].to_excel(writer, sheet_name="Network", index=False)
    logger.info(
        f"Network sheet updated with {network_df.shape[0]} excluded pharmacy records (minus major chains) and selected columns"
    )


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
        logger.info(
            f"Network sheet will show {network_df.shape[0]} excluded pharmacy records (minus major chains)"
        )

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
        network_df[selected_columns].to_excel(writer, sheet_name="Network", index=False)
        logger.info(
            f"Network sheet updated with {network_df.shape[0]} excluded pharmacy records (minus major chains) and selected columns"
        )

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
