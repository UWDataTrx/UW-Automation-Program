import pandas as pd
import re
import logging
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path before importing project_settings
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


from utils.utils import (  # noqa: E402
    standardize_pharmacy_ids,
    standardize_network_ids,
    merge_with_network,
    drop_duplicates_df,
    clean_logic_and_tier,
    filter_recent_date,
    filter_logic_and_maintenance,
    filter_products_and_alternative,
    write_audit_log,
)
from modules.audit_helper import (  # noqa: E402
    make_audit_entry,
    log_user_session_start,
    log_user_session_end,
    log_file_access,
)


# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
# Tier summarization helper
# ---------------------------------------------------------------------------
def summarize_by_tier(df, col, from_val, to_val):
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

    network = pd.read_excel(
        file_paths["n_disrupt"],
        usecols=["pharmacy_npi", "pharmacy_nabp", "pharmacy_is_excluded"],
    )
    print(f"network shape: {network.shape}")

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

    # Standardize IDs and perform network merge
    df = standardize_pharmacy_ids(df)
    print(f"After standardize_pharmacy_ids: {df.shape}")
    network = standardize_network_ids(network)
    print(f"After standardize_network_ids: {network.shape}")
    df = merge_with_network(df, network)
    print(f"After merge_with_network: {df.shape}")

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
            output_file_path = Path(file_paths["pharmacy_validation"]).resolve()
            na_pharmacies_output = na_pharmacies[["PHARMACYNPI", "NABP"]].fillna("N/A")
            # Add Result column with "NA" value
            na_pharmacies_output["Result"] = "NA"

            # Use pandas to write to Excel, which is simpler and more reliable
            try:
                # Try to append to existing file
                if output_file_path.exists():
                    # Read existing data
                    existing_df = pd.read_excel(output_file_path)
                    # Concatenate with new data
                    combined_df = pd.concat(
                        [existing_df, na_pharmacies_output], ignore_index=True
                    )
                    # Remove duplicates
                    combined_df = combined_df.drop_duplicates()
                else:
                    combined_df = na_pharmacies_output

                # Write to Excel
                combined_df.to_excel(output_file_path, index=False)
                logger.info(
                    f"NA pharmacies written to '{output_file_path}' with Result column."
                )

            except Exception as e:
                logger.error(f"Error updating pharmacy validation file: {e}")
                make_audit_entry(
                    "tier_disruption.py",
                    f"Pharmacy validation file update error: {e}",
                    "FILE_ERROR",
                )
                # Fallback - just write the new data
                na_pharmacies_output.to_excel(output_file_path, index=False)
                logger.info(
                    f"NA pharmacies written to '{output_file_path}' (fallback mode)."
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
    network_df = df[df["pharmacy_is_excluded"]]
    logger.debug(f"Initial network_df shape: {network_df.shape}")
    logger.debug(f"Initial network_df contents: {network_df.head(10).to_dict()}")

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
            lambda row: row["PHARMACYNPI"]
            if row["PHARMACYNPI"] != "N/A"
            else row["NABP"],
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


def write_excel_sheets(
    writer, df, summary_df, tier_pivots, ex_pt, exc_members, network_df, network_pivot
):
    """Write all sheets to the Excel file."""

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
    network_df[selected_columns].to_excel(writer, sheet_name="Network", index=False)
    logger.info(
        f"Network sheet updated with {network_df.shape[0]} excluded pharmacy records (minus major chains) and selected columns"
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
        file_paths = config_manager.get("file_paths.json")

        logger.info("Loading tier disruption data files...")
        result = load_tier_disruption_data(file_paths)
        if result is None:
            logger.error("Claims loading failed - early exit")
            make_audit_entry(
                "tier_disruption.py", "Claims loading failed - early exit", "DATA_ERROR"
            )
            return  # Early exit if claims loading failed
        claims, medi, u, e, network = result

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

        # Network summary for excluded pharmacies (pharmacy_is_excluded=True)
        logger.info("Processing network analysis...")
        network_df, network_pivot = create_network_analysis(df)
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
        network_df[selected_columns].to_excel(writer, sheet_name="Network", index=False)
        logger.info(
            f"Network sheet updated with {network_df.shape[0]} excluded pharmacy records (minus major chains) and selected columns"
        )

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
    except Exception as e:
        # Log detailed error information
        make_audit_entry(
            "tier_disruption.py",
            f"Processing failed with error: {str(e)}",
            "SYSTEM_ERROR",
        )
        write_audit_log(
            "tier_disruption.py",
            f"Processing failed for user: {username}: {e}",
            status="ERROR",
        )
        raise
    finally:
        # End audit session
        log_user_session_end("tier_disruption.py")


if __name__ == "__main__":
    process_data()
    # Always show terminal notification at the end
    print("Processing complete.")
