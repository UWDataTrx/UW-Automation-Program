import pandas as pd
import logging
import os
import sys
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import (
    load_file_paths,
    standardize_pharmacy_ids,
    standardize_network_ids,
    merge_with_network,
    drop_duplicates_df,
    clean_logic_and_tier,
    filter_recent_date,
    filter_logic_and_maintenance,
    filter_products_and_alternative,
    write_shared_log,
)

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
    write_shared_log("openmdf_bg.py", "Processing started.")

    import sys

    # Get the config file path relative to the project root
    config_path = Path(__file__).parent.parent / "config" / "file_paths.json"
    paths = load_file_paths(str(config_path))

    if "reprice" not in paths or not paths["reprice"]:
        logger.warning("No reprice/template file provided.")
        write_shared_log(
            "openmdf_bg.py", "No reprice/template file provided.", status="ERROR"
        )
        print("No reprice/template file provided.")
        return False

    # Check for required sheet name in reprice file
    try:
        xl = pd.ExcelFile(paths["reprice"])
        if "Claims Table" not in xl.sheet_names:
            logger.error(
                f"Sheet 'Claims Table' not found in {paths['reprice']}. Sheets: {xl.sheet_names}"
            )
            write_shared_log(
                "openmdf_bg.py",
                f"Sheet 'Claims Table' not found in {paths['reprice']}. Sheets: {xl.sheet_names}",
                status="ERROR",
            )
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
    except Exception as e:
        logger.error(f"Failed to read Claims Table: {e}")
        write_shared_log(
            "openmdf_bg.py", f"Failed to read Claims Table: {e}", status="ERROR"
        )
        return False

    # Log claim count before any filtering
    logger.info(f"Initial claims count: {claims.shape[0]}")
    write_shared_log("openmdf_bg.py", f"Initial claims count: {claims.shape[0]}")

    try:
        medi = pd.read_excel(paths["medi_span"])[["NDC", "Maint Drug?", "Product Name"]]
    except Exception as e:
        logger.error(f"Failed to read medi_span file: {paths['medi_span']} | {e}")
        write_shared_log(
            "openmdf_bg.py",
            f"Failed to read medi_span file: {paths['medi_span']} | {e}",
            status="ERROR",
        )
        return False
    try:
        mdf = pd.read_excel(paths["mdf_disrupt"], sheet_name="Open MDF NDC")[
            ["NDC", "Tier"]
        ]
    except Exception as e:
        logger.error(f"Failed to read mdf_disrupt file: {paths['mdf_disrupt']} | {e}")
        write_shared_log(
            "openmdf_bg.py",
            f"Failed to read mdf_disrupt file: {paths['mdf_disrupt']} | {e}",
            status="ERROR",
        )
        return False
    try:
        network = pd.read_excel(paths["n_disrupt"])[
            ["pharmacy_npi", "pharmacy_nabp", "pharmacy_is_excluded"]
        ]
    except Exception as e:
        logger.error(f"Failed to read n_disrupt file: {paths['n_disrupt']} | {e}")
        write_shared_log(
            "openmdf_bg.py",
            f"Failed to read n_disrupt file: {paths['n_disrupt']} | {e}",
            status="ERROR",
        )
        return False
        # Read Alternatives NDC for 'Alternative' column
    try:
        exclusive = pd.read_excel(paths["e_disrupt"], sheet_name="Alternatives NDC")[
            ["NDC", "Tier", "Alternative"]
        ]
    except Exception as e:
        logger.error(f"Failed to read e_disrupt file: {paths['e_disrupt']} | {e}")
        write_shared_log(
            "openmdf_bg.py",
            f"Failed to read e_disrupt file: {paths['e_disrupt']} | {e}",
            status="ERROR",
        )
        return False

    df = claims.merge(medi, on="NDC", how="left")
    print(f"After merge with medi: {df.shape}")
    logger.info(f"After merge with medi: {df.shape}")
    df = df.merge(mdf, on="NDC", how="left")
    print(f"After merge with mdf: {df.shape}")
    logger.info(f"After merge with mdf: {df.shape}")
    # Merge in Alternatives for 'Alternative' column
    df = df.merge(
        exclusive.rename(columns={"Tier": "Exclusive Tier"}), on="NDC", how="left"
    )
    print(f"After merge with exclusive: {df.shape}")
    logger.info(f"After merge with exclusive: {df.shape}")
    df = standardize_pharmacy_ids(df)
    print(f"After standardize_pharmacy_ids: {df.shape}")
    logger.info(f"After standardize_pharmacy_ids: {df.shape}")
    network = standardize_network_ids(network)
    print(f"After standardize_network_ids: {network.shape}")
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
    print(f"Columns in df before merging: {df.columns.tolist()}")

    # Log claim count after merge
    print(f"Claims after merge: {df.shape}")
    logger.info(f"Claims after merge: {df.shape}")
    write_shared_log("openmdf_bg.py", f"Claims after merge: {df.shape[0]}")

    df = merge_with_network(df, network)
    print(f"After merge_with_network: {df.shape}")
    logger.info(f"After merge_with_network: {df.shape}")
    write_shared_log("openmdf_bg.py", f"Claims after merge_with_network: {df.shape[0]}")

    df = drop_duplicates_df(df)
    print(f"After drop_duplicates_df: {df.shape}")
    logger.info(f"After drop_duplicates_df: {df.shape}")
    write_shared_log("openmdf_bg.py", f"Claims after drop_duplicates_df: {df.shape[0]}")

    df = clean_logic_and_tier(df)
    print(f"After clean_logic_and_tier: {df.shape}")
    logger.info(f"After clean_logic_and_tier: {df.shape}")
    write_shared_log(
        "openmdf_bg.py", f"Claims after clean_logic_and_tier: {df.shape[0]}"
    )

    df = filter_products_and_alternative(df)
    print(f"After filter_products_and_alternative: {df.shape}")
    logger.info(f"After filter_products_and_alternative: {df.shape}")
    write_shared_log(
        "openmdf_bg.py", f"Claims after filter_products_and_alternative: {df.shape[0]}"
    )

    df["DATEFILLED"] = pd.to_datetime(df["DATEFILLED"], errors="coerce")
    print(f"After DATEFILLED to_datetime: {df.shape}")
    df = filter_recent_date(df)
    print(f"After filter_recent_date: {df.shape}")
    logger.info(f"After filter_recent_date: {df.shape}")
    write_shared_log("openmdf_bg.py", f"Claims after filter_recent_date: {df.shape[0]}")

    df["Logic"] = pd.to_numeric(df["Logic"], errors="coerce")
    df = filter_logic_and_maintenance(df)
    print(f"After filter_logic_and_maintenance: {df.shape}")
    logger.info(f"After filter_logic_and_maintenance: {df.shape}")
    write_shared_log(
        "openmdf_bg.py", f"Claims after filter_logic_and_maintenance: {df.shape[0]}"
    )

    df = df[
        ~df["Product Name"].str.contains(
            r"albuterol|ventolin|epinephrine", case=False, regex=True
        )
    ]
    print(f"After final product exclusion: {df.shape}")
    logger.info(f"After final product exclusion: {df.shape}")
    write_shared_log(
        "openmdf_bg.py", f"Claims after final product exclusion: {df.shape[0]}"
    )

    df["FormularyTier"] = df["FormularyTier"].astype(str).str.strip().str.upper()
    total_members = df["MemberID"].nunique()
    total_claims = df["Rxs"].sum()

    uni_pos = df[(df["Tier"] == 1) & (df["FormularyTier"].isin(["B", "BRAND"]))]
    uni_neg = df[
        (df["Tier"].isin([2, 3])) & (df["FormularyTier"].isin(["G", "GENERIC"]))
    ]

    def pivot_and_count(data):
        if data.empty:
            return pd.DataFrame([[0] * len(df.columns)], columns=df.columns), 0
        return data, data["MemberID"].nunique()

    uni_pos, uni_pos_members = pivot_and_count(uni_pos)
    uni_neg, uni_neg_members = pivot_and_count(uni_neg)

    # Output filename from CLI arg or default
    import re

    output_filename = "LBL for Disruption.xlsx"
    output_path = output_filename  # Default assignment
    for i, arg in enumerate(sys.argv):
        if arg in ("--output", "-o") and i + 1 < len(sys.argv):
            output_filename = sys.argv[i + 1]
            output_path = output_filename

    # Write LBL output unconditionally (no --output-lbl flag required)
    writer = pd.ExcelWriter(output_path, engine="xlsxwriter")

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
                # Fallback - just write the new data
                na_pharmacies_output.to_excel(output_file_path, index=False)
                logger.info(f"NA pharmacies written to '{output_file_path}' (fallback mode).")

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
    logger.info(f"Open MDF BG processing completed. Output file: {output_path}")
    write_shared_log("openmdf_bg.py", "Processing complete.")
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
