import pandas as pd
import logging
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

# Logging setup
logging.basicConfig(
    filename="openmdf_tier.log",
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
    write_shared_log("openmdf_tier.py", "Processing started.")
    try:
        paths = load_file_paths()

        if "reprice" not in paths or not paths["reprice"]:
            logger.warning("No reprice/template file provided.")
            write_shared_log(
                "openmdf_tier.py", "No reprice/template file provided.", status="ERROR"
            )
            print("No reprice/template file provided.")
            return
    except Exception as e:
        logger.error(f"Failed to load file paths: {e}")
        write_shared_log(
            "openmdf_tier.py", f"Failed to load file paths: {e}", status="ERROR"
        )
        return

    # Granular file read error logging
    try:
        claims = pd.read_excel(paths["reprice"], sheet_name="Claims Table")
    except Exception as e:
        logger.error(f"Failed to read claims file: {paths['reprice']} | {e}")
        write_shared_log(
            "openmdf_tier.py",
            f"Failed to read claims file: {paths['reprice']} | {e}",
            status="ERROR",
        )
        return
    try:
        medi = pd.read_excel(paths["medi_span"])[["NDC", "Maint Drug?", "Product Name"]]
    except Exception as e:
        logger.error(f"Failed to read medi_span file: {paths['medi_span']} | {e}")
        write_shared_log(
            "openmdf_tier.py",
            f"Failed to read medi_span file: {paths['medi_span']} | {e}",
            status="ERROR",
        )
        return
    try:
        mdf = pd.read_excel(paths["mdf_disrupt"], sheet_name="Open MDF NDC")[
            ["NDC", "Tier"]
        ]
    except Exception as e:
        logger.error(f"Failed to read mdf_disrupt file: {paths['mdf_disrupt']} | {e}")
        write_shared_log(
            "openmdf_tier.py",
            f"Failed to read mdf_disrupt file: {paths['mdf_disrupt']} | {e}",
            status="ERROR",
        )
        return
    try:
        exclusive = pd.read_excel(paths["e_disrupt"], sheet_name="Alternatives NDC")[
            ["NDC", "Tier", "Alternative"]
        ]
    except Exception as e:
        logger.error(f"Failed to read e_disrupt file: {paths['e_disrupt']} | {e}")
        write_shared_log(
            "openmdf_tier.py",
            f"Failed to read e_disrupt file: {paths['e_disrupt']} | {e}",
            status="ERROR",
        )
        return
    try:
        network = pd.read_excel(paths["n_disrupt"])[
            ["pharmacy_npi", "pharmacy_nabp", "pharmacy_is_excluded"]
        ]
    except Exception as e:
        logger.error(f"Failed to read n_disrupt file: {paths['n_disrupt']} | {e}")
        write_shared_log(
            "openmdf_tier.py",
            f"Failed to read n_disrupt file: {paths['n_disrupt']} | {e}",
            status="ERROR",
        )
        return

    df = claims.merge(medi, on="NDC", how="left")
    print(f"After merge with medi: {df.shape}")
    df = df.merge(mdf.rename(columns={"Tier": "Open MDF Tier"}), on="NDC", how="left")
    print(f"After merge with mdf: {df.shape}")
    df = df.merge(
        exclusive.rename(columns={"Tier": "Exclusive Tier"}), on="NDC", how="left"
    )
    print(f"After merge with exclusive: {df.shape}")

    df = standardize_pharmacy_ids(df)
    print(f"After standardize_pharmacy_ids: {df.shape}")
    network = standardize_network_ids(network)
    print(f"After standardize_network_ids: {network.shape}")
    df = merge_with_network(df, network)
    print(f"After merge_with_network: {df.shape}")

    if "pharmacy_id" not in df.columns:
        df["pharmacy_id"] = df.apply(
            lambda row: row["PHARMACYNPI"]
            if pd.notna(row["PHARMACYNPI"])
            else row["NABP"],
            axis=1,
        )

    print("Columns in df before merging with network:")
    print(df.columns)

    df = drop_duplicates_df(df)
    print(f"After drop_duplicates_df: {df.shape}")
    df["DATEFILLED"] = pd.to_datetime(df["DATEFILLED"], errors="coerce")
    print(f"After DATEFILLED to_datetime: {df.shape}")
    df = filter_recent_date(df)
    print(f"After filter_recent_date: {df.shape}")
    df = clean_logic_and_tier(df)
    print(f"After clean_logic_and_tier: {df.shape}")
    df = filter_logic_and_maintenance(df)
    print(f"After filter_logic_and_maintenance: {df.shape}")
    df = filter_products_and_alternative(df)
    print(f"After filter_products_and_alternative: {df.shape}")

    df["FormularyTier"] = pd.to_numeric(df["FormularyTier"], errors="coerce")
    total_claims = df["Rxs"].sum()
    total_members = df["MemberID"].nunique()

    # Output filename from CLI arg or default
    import sys
    import re

    output_filename = "LBL for Disruption.xlsx"
    for i, arg in enumerate(sys.argv):
        if arg in ("--output", "-o") and i + 1 < len(sys.argv):
            output_filename = sys.argv[i + 1]
    writer = pd.ExcelWriter(output_filename, engine="xlsxwriter")

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
            writer = pd.ExcelWriter(output_file_path, engine="openpyxl")

            na_pharmacies_output = na_pharmacies[["PHARMACYNPI", "NABP"]].fillna("N/A")
            na_pharmacies_output.to_excel(
                writer, sheet_name="Validations", index=False, engine="openpyxl"
            )
            writer.close()
            logger.info(f"NA pharmacies written to '{output_file_path}' sheet.")

    # Build tier pivots but do not write yet
    tiers = [
        ("OpenMDF_Positive 2-1", 1, 2),
        ("OpenMDF_Positive 3-1", 1, 3),
        ("OpenMDF_Positive 3-2", 2, 3),
        ("OpenMDF_Negative 1-2", 2, 1),
        ("OpenMDF_Negative 1-3", 3, 1),
        ("OpenMDF_Negative 2-3", 3, 2),
    ]
    pos_keys = []
    neg_keys = []
    tab_members = {}
    tab_rxs = {}
    tier_pivots = []

    for name, from_val, to_val in tiers:
        filtered = df[
            (df["Open MDF Tier"] == from_val) & (df["FormularyTier"] == to_val)
        ]
        pt = pd.pivot_table(
            filtered,
            values=["Rxs", "MemberID"],
            index="Product Name",
            aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique},
        )
        pt = pt.rename(columns={"Rxs": "Total Rxs", "MemberID": "Unique Members"})
        members = filtered["MemberID"].nunique()
        rxs = filtered["Rxs"].sum()
        tier_pivots.append((name, pt, members, rxs))
        tab_members[name] = members
        tab_rxs[name] = rxs

        if "Positive" in name:
            pos_keys.append(name)
        elif "Negative" in name:
            neg_keys.append(name)

    # Build 2-row Summary
    pos_total_members = sum(tab_members[k] for k in pos_keys)
    pos_total_rxs = sum(tab_rxs[k] for k in pos_keys)
    pos_pct = pos_total_rxs / total_claims if total_claims else 0

    neg_total_members = sum(tab_members[k] for k in neg_keys)
    neg_total_rxs = sum(tab_rxs[k] for k in neg_keys)
    neg_pct = neg_total_rxs / total_claims if total_claims else 0

    summary_df = pd.DataFrame(
        {
            "Formulary": ["Open MDF Positive", "Open MDF Negative"],
            "Utilizers": [pos_total_members, neg_total_members],
            "Rxs": [pos_total_rxs, neg_total_rxs],
            "% of claims": [pos_pct, neg_pct],
            "": ["", ""],
            "Totals": [f"Members: {total_members}", f"Claims: {total_claims}"],
        }
    )
    summary_df.to_excel(writer, sheet_name="Summary", index=False)

    # Write tier pivots after Summary
    for name, pt, members, _ in tier_pivots:
        pt.to_excel(writer, sheet_name=name)
        writer.sheets[name].write("F1", f"Total Members: {members}")

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

    # Filter logic to include pharmacies based on NABP/NPI
    network_df = df[
        df["NABP"].isin(included_nabp_npi.keys())
        & df["PHARMACYNPI"].isin(included_nabp_npi.values())
    ]
    network_pivot = pd.pivot_table(
        network_df,
        values=["Rxs", "MemberID"],
        index=["PHARMACYNPI", "NABP", "Pharmacy Name"],
        aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique},
    )
    network_pivot = network_pivot.rename(
        columns={"Rxs": "Total Rxs", "MemberID": "Unique Members"}
    )
    network_pivot.to_excel(writer, sheet_name="Network")

    # Log the inclusion of pharmacies based on NABP/NPI
    logger.info(f"Included {network_df.shape[0]} pharmacies based on NABP/NPI list")

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
    write_shared_log("openmdf_tier.py", "Processing complete.")
    print("Processing complete")
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Processing Complete", "Processing complete")
        root.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    process_data()
