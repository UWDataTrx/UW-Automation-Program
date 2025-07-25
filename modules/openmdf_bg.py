import pandas as pd
import logging
import sys
from pathlib import Path
# Ensure project root is in sys.path before importing project_settings
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from project_settings import PROJECT_ROOT  # noqa: E402
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
from config.config_loader import ConfigManager  # noqa: E402
from utils.excel_utils import safe_excel_write, check_disk_space  # noqa: E402
from modules.audit_helper import (  # noqa: E402
    make_audit_entry,
    log_user_session_start,
    log_user_session_end,
    log_file_access,
)

# Import required utility functions for overwrite protection
# from utils.utils import load_file_paths

# Overwrite protection: prevent output file from matching any input file

# Always use 'LBL for Disruption.xlsx' in the current working directory
output_path = Path.cwd() / "LBL for Disruption.xlsx"


# Add the project root directory to the Python path using PROJECT_ROOT
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    filename="openmdf_bg.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

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


def process_data():
    # Start audit session

    logger.info(f"Session started for user: {Path.home().name}")
    log_user_session_start("openmdf_bg.py")
    write_audit_log("openmdf_bg.py", "Processing started.")
    logger.info("Loading data files...")

    try:

        # Get the config file path relative to the project root
        config_manager = ConfigManager()
        paths = config_manager.get("file_paths.json")

        if "reprice" not in paths or not paths["reprice"]:
            logger.warning("No reprice/template file provided.")
            make_audit_entry(
                "openmdf_bg.py", "No reprice/template file provided.", "FILE_ERROR"
            )
            write_audit_log(
                "openmdf_bg.py", "No reprice/template file provided.", status="ERROR"
            )
            print("No reprice/template file provided.")
            log_user_session_end("openmdf_bg.py")
            return False

        # Log file access

        logger.info(f"File access by user: {Path.home().name} | {paths['reprice']} | LOADING")
        log_file_access("openmdf_bg.py", paths["reprice"], "LOADING")

        # Check for required sheet name in reprice file
        try:
            xl = pd.ExcelFile(paths["reprice"])
            if "Claims Table" not in xl.sheet_names:
                logger.error(
                    f"Sheet 'Claims Table' not found in {paths['reprice']}. Sheets: {xl.sheet_names}"
                )
                make_audit_entry(
                    "openmdf_bg.py",
                    f"Sheet 'Claims Table' not found. Available sheets: {xl.sheet_names}",
                    "DATA_ERROR",
                )
                write_audit_log(
                    "openmdf_bg.py",
                    f"Sheet 'Claims Table' not found in {paths['reprice']}. Sheets: {xl.sheet_names}",
                    status="ERROR",
                )
                log_user_session_end("openmdf_bg.py")
                return False
            claims = xl.parse(
                "Claims Table",
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
            logger.info(f"claims shape: {claims.shape}")
        except Exception as e:
            logger.error(f"Failed to read Claims Table: {e}")
            make_audit_entry(
                "openmdf_bg.py", f"Failed to read Claims Table: {e}", "FILE_ERROR"
            )
            write_audit_log(
                "openmdf_bg.py", f"Failed to read Claims Table: {e}", status="ERROR"
            )
            log_user_session_end("openmdf_bg.py")
            return False
    except Exception as e:
        logger.error(f"Failed to load configuration or reprice file: {e}")
        make_audit_entry(
            "openmdf_bg.py",
            f"Failed to load configuration or reprice file: {e}",
            "FILE_ERROR",
        )
        write_audit_log(
            "openmdf_bg.py",
            f"Failed to load configuration or reprice file: {e}",
            status="ERROR",
        )
        log_user_session_end("openmdf_bg.py")
        return False

    # Log claim count before any filtering
    logger.info(f"Initial claims count: {claims.shape[0]}")
    write_audit_log("openmdf_bg.py", f"Initial claims count: {claims.shape[0]}")

    try:
        medi = pd.read_excel(paths["medi_span"])[["NDC", "Maint Drug?", "Product Name"]]
        logger.info(f"medi shape: {medi.shape}")
        log_file_access("openmdf_bg.py", paths["medi_span"], "LOADED")
    except Exception as e:
        logger.error(f"Failed to read medi_span file: {paths['medi_span']} | {e}")
        make_audit_entry(
            "openmdf_bg.py", f"Failed to read medi_span file: {e}", "FILE_ERROR"
        )
        write_audit_log(
            "openmdf_bg.py",
            f"Failed to read medi_span file: {paths['medi_span']} | {e}",
            status="ERROR",
        )
        log_user_session_end("openmdf_bg.py")
        return False
    try:
        mdf = pd.read_excel(paths["mdf_disrupt"], sheet_name="Open MDF NDC")[
            ["NDC", "Tier"]
        ]
        logger.info(f"mdf shape: {mdf.shape}")
        log_file_access("openmdf_bg.py", paths["mdf_disrupt"], "LOADED")
    except Exception as e:
        logger.error(f"Failed to read mdf_disrupt file: {paths['mdf_disrupt']} | {e}")
        make_audit_entry(
            "openmdf_bg.py", f"Failed to read mdf_disrupt file: {e}", "FILE_ERROR"
        )
        write_audit_log(
            "openmdf_bg.py",
            f"Failed to read mdf_disrupt file: {paths['mdf_disrupt']} | {e}",
            status="ERROR",
        )
        log_user_session_end("openmdf_bg.py")
        return False
    try:
        network = pd.read_excel(paths["n_disrupt"])[
            ["pharmacy_npi", "pharmacy_nabp", "pharmacy_is_excluded"]
        ]
        logger.info(f"network shape: {network.shape}")
        log_file_access("openmdf_bg.py", paths["n_disrupt"], "LOADED")
    except Exception as e:
        logger.error(f"Failed to read n_disrupt file: {paths['n_disrupt']} | {e}")
        make_audit_entry(
            "openmdf_bg.py", f"Failed to read n_disrupt file: {e}", "FILE_ERROR"
        )
        write_audit_log(
            "openmdf_bg.py",
            f"Failed to read n_disrupt file: {paths['n_disrupt']} | {e}",
            status="ERROR",
        )
        log_user_session_end("openmdf_bg.py")
        return False
        # Read Alternatives NDC for 'Alternative' column
    try:
        exclusive = pd.read_excel(paths["e_disrupt"], sheet_name="Alternatives NDC")[
            ["NDC", "Tier", "Alternative"]
        ]
        logger.info(f"exclusive shape: {exclusive.shape}")
        log_file_access("openmdf_bg.py", paths["e_disrupt"], "LOADED")
    except Exception as e:
        logger.error(f"Failed to read e_disrupt file: {paths['e_disrupt']} | {e}")
        make_audit_entry(
            "openmdf_bg.py", f"Failed to read e_disrupt file: {e}", "FILE_ERROR"
        )
        write_audit_log(
            "openmdf_bg.py",
            f"Failed to read e_disrupt file: {paths['e_disrupt']} | {e}",
            status="ERROR",
        )
        log_user_session_end("openmdf_bg.py")
        return False

    logger.info("Merging data files...")
    df = claims.merge(medi, on="NDC", how="left")
    logger.info(f"After merge with medi: {df.shape}")
    df = df.merge(mdf, on="NDC", how="left")
    logger.info(f"After merge with mdf: {df.shape}")
    # Merge in Alternatives for 'Alternative' column
    df = df.merge(
        exclusive.rename(columns={"Tier": "Exclusive Tier"}), on="NDC", how="left"
    )
    logger.info(f"After merge with exclusive: {df.shape}")
    df = standardize_pharmacy_ids(df)
    logger.info(f"After standardize_pharmacy_ids: {df.shape}")
    network = standardize_network_ids(network)
    logger.info(f"After standardize_network_ids: {network.shape}")

    # Ensure pharmacy_id exists
    if "pharmacy_id" not in df.columns:
        df["pharmacy_id"] = df.apply(
            lambda row: row["PHARMACYNPI"]
            if pd.notna(row["PHARMACYNPI"])
            else row["NABP"],
            axis=1,
        )

    logger.info(f"Columns in df before merging: {df.columns.tolist()}")

    logger.info(f"Claims after merge: {df.shape}")
    write_audit_log("openmdf_bg.py", f"Claims after merge: {df.shape[0]}")

    df = merge_with_network(df, network)
    logger.info(f"After merge_with_network: {df.shape}")
    write_audit_log("openmdf_bg.py", f"Claims after merge_with_network: {df.shape[0]}")

    logger.info("Processing and filtering data...")
    df = drop_duplicates_df(df)
    logger.info(f"After drop_duplicates_df: {df.shape}")
    write_audit_log("openmdf_bg.py", f"Claims after drop_duplicates_df: {df.shape[0]}")

    df = clean_logic_and_tier(df)
    logger.info(f"After clean_logic_and_tier: {df.shape}")
    write_audit_log(
        "openmdf_bg.py", f"Claims after clean_logic_and_tier: {df.shape[0]}"
    )

    df = filter_products_and_alternative(df)
    logger.info(f"After filter_products_and_alternative: {df.shape}")
    write_audit_log(
        "openmdf_bg.py", f"Claims after filter_products_and_alternative: {df.shape[0]}"
    )

    df["DATEFILLED"] = pd.to_datetime(df["DATEFILLED"], errors="coerce")
    logger.info(f"After DATEFILLED to_datetime: {df.shape}")
    df = filter_recent_date(df)
    logger.info(f"After filter_recent_date: {df.shape}")
    write_audit_log("openmdf_bg.py", f"Claims after filter_recent_date: {df.shape[0]}")

    df["Logic"] = pd.to_numeric(df["Logic"], errors="coerce")
    df = filter_logic_and_maintenance(df)
    logger.info(f"After filter_logic_and_maintenance: {df.shape}")
    write_audit_log(
        "openmdf_bg.py", f"Claims after filter_logic_and_maintenance: {df.shape[0]}"
    )

    df = df[
        ~df["Product Name"].str.contains(
            r"albuterol|ventolin|epinephrine", case=False, regex=True
        )
    ]
    logger.info(f"After final product exclusion: {df.shape}")
    write_audit_log(
        "openmdf_bg.py", f"Claims after final product exclusion: {df.shape[0]}"
    )

    df["FormularyTier"] = df["FormularyTier"].astype(str).str.strip().str.upper()
    total_members = df["MemberID"].nunique()
    total_claims = df["Rxs"].sum()
    logger.info("Creating data filters...")

    uni_pos = df[(df["Tier"] == 1) & (df["FormularyTier"].isin(["B", "BRAND"]))]
    uni_neg = df[
        (df["Tier"].isin([2, 3])) & (df["FormularyTier"].isin(["G", "GENERIC"]))
    ]

    def pivot_and_count(data):
        if data.empty:
            return pd.DataFrame([[0] * len(df.columns)], columns=df.columns), 0
        return data, data["MemberID"].nunique()

    uni_pos, uni_pos_members = pivot_and_count(uni_pos)
    logger.info(f"uni_pos shape: {uni_pos.shape}")
    uni_neg, uni_neg_members = pivot_and_count(uni_neg)
    logger.info(f"uni_neg shape: {uni_neg.shape}")


    # Output file is always 'LBL for Disruption.xlsx' in the current working directory
    import re

    # Check disk space before attempting to write
    if not check_disk_space(".", 500):  # Require 500MB free space
        logger.error("Insufficient disk space for Excel operations")
        make_audit_entry(
            "openmdf_bg.py",
            "Insufficient disk space for Excel operations",
            "SYSTEM_ERROR",
        )
        write_audit_log(
            "openmdf_bg.py",
            "Insufficient disk space for Excel operations",
            status="ERROR",
        )
        log_user_session_end("openmdf_bg.py")
        return False

    try:
        logger.info("Writing Excel report...")
        writer = pd.ExcelWriter(output_path, engine="xlsxwriter")
    except Exception as e:
        logger.error(f"Failed to create Excel writer for {output_path}: {e}")
        make_audit_entry(
            "openmdf_bg.py", f"Failed to create Excel writer: {e}", "FILE_ERROR"
        )
        write_audit_log(
            "openmdf_bg.py", f"Failed to create Excel writer: {e}", status="ERROR"
        )
        log_user_session_end("openmdf_bg.py")
        return False

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
            output_file_path = paths["pharmacy_validation"]
            na_pharmacies_output = na_pharmacies[["PHARMACYNPI", "NABP"]].fillna("N/A")
            # Add Result column with "NA" value
            na_pharmacies_output["Result"] = "NA"

            # Use pandas to write to Excel, which is simpler and more reliable

            try:
                # Try to append to existing file
                output_file_path_obj = Path(output_file_path)
                if output_file_path_obj.exists():
                    # Read existing data
                    existing_df = pd.read_excel(output_file_path_obj)
                    # Concatenate with new data
                    combined_df = pd.concat(
                        [existing_df, na_pharmacies_output], ignore_index=True
                    )
                    # Remove duplicates
                    combined_df = combined_df.drop_duplicates()
                else:
                    combined_df = na_pharmacies_output

                # Write to Excel using safe method
                if not safe_excel_write(
                    combined_df, str(output_file_path_obj), index=False
                ):
                    logger.error(
                        f"Safe write failed for {output_file_path_obj}, trying fallback"
                    )
                    # Fallback to direct pandas write
                    combined_df.to_excel(output_file_path_obj, index=False)
                logger.info(
                    f"NA pharmacies written to '{output_file_path_obj}' with Result column."
                )

            except Exception as e:
                logger.error(f"Error updating pharmacy validation file: {e}")
                # Fallback - just write the new data
                na_pharmacies_output.to_excel(output_file_path, index=False)
                logger.info(
                    f"NA pharmacies written to '{output_file_path}' (fallback mode)."
                )

    # Write main data to 'Claims Data' sheet
    df.to_excel(writer, sheet_name="Claims Data", index=False)

    summary = pd.DataFrame(
        {
            "Formulary": ["Open MDF Positive", "Open MDF Negative"],
            "Utilizers": [uni_pos_members, uni_neg_members],
            "Rxs": [uni_pos["Rxs"].sum(), uni_neg["Rxs"].sum()],
            "% of claims": [
                uni_pos["Rxs"].sum() / total_claims,
                uni_neg["Rxs"].sum() / total_claims,
            ],
            "": ["", ""],
            "Totals": [f"Members: {total_members}", f"Claims: {total_claims}"],
        }
    )
    summary.to_excel(writer, sheet_name="Summary", index=False)

    pt_pos = pd.pivot_table(
        uni_pos,
        values=["Rxs", "MemberID"],
        index="Product Name",
        aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique},
    )
    pt_pos = pt_pos.rename(columns={"Rxs": "Total Rxs", "MemberID": "Unique Members"})
    pt_pos.to_excel(writer, sheet_name="OpenMDF_Positive")

    pt_neg = pd.pivot_table(
        uni_neg,
        values=["Rxs", "MemberID"],
        index="Product Name",
        aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique},
    )
    pt_neg = pt_neg.rename(columns={"Rxs": "Total Rxs", "MemberID": "Unique Members"})
    pt_neg.to_excel(writer, sheet_name="OpenMDF_Negative")

    writer.sheets["OpenMDF_Positive"].write("F1", f"Total Members: {uni_pos_members}")
    writer.sheets["OpenMDF_Negative"].write("F1", f"Total Members: {uni_neg_members}")

    # Network summary for excluded pharmacies (pharmacy_is_excluded=True)
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
        network_pivot.to_excel(writer, sheet_name="Network", index=False)

    # Write the filtered network_df directly to the 'Network Sheet' with selected columns
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

    # Close writer with error handling
    try:
        writer.close()
        logger.info(f"Excel report written to: {output_path}")

        # Validate the output file was created correctly

        output_path_obj = Path(output_path)
        if not output_path_obj.exists():
            raise FileNotFoundError(f"Output file was not created: {output_path}")

        # Quick validation of the Excel file
        try:
            pd.read_excel(output_path, nrows=1)
            logger.info(f"Output file validation successful: {output_path}")
        except Exception as validation_error:
            logger.error(f"Output file validation failed: {validation_error}")
            make_audit_entry(
                "openmdf_bg.py",
                f"Output file validation failed: {validation_error}",
                "FILE_ERROR",
            )
            write_audit_log(
                "openmdf_bg.py",
                f"Output file validation failed: {validation_error}",
                status="ERROR",
            )
            # Don't return False here as the file might still be usable

    except Exception as e:
        logger.error(f"Failed to close Excel writer: {e}")
        make_audit_entry(
            "openmdf_bg.py", f"Failed to close Excel writer: {e}", "FILE_ERROR"
        )
        write_audit_log(
            "openmdf_bg.py", f"Failed to close Excel writer: {e}", status="ERROR"
        )
        log_user_session_end("openmdf_bg.py")
        return False

    # Log successful completion
    logger.info(f"Session ended for user: {Path.home().name}")
    logger.info(f"Open MDF BG processing completed. Output file: {output_path}")
    make_audit_entry(
        "openmdf_bg.py",
        f"Successfully generated Open MDF BG report: {output_path}",
        "INFO",
    )
    log_file_access("openmdf_bg.py", str(output_path), "CREATED")
    write_audit_log("openmdf_bg.py", "Processing complete.")
    log_user_session_end("openmdf_bg.py")

    # Final cleanup and completion message
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

    return True


if __name__ == "__main__":
    process_data()
