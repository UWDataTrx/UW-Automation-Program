import pandas as pd
import logging
from utils import (
    load_file_paths,
    safe_read_excel,
    standardize_pharmacy_ids,
    merge_with_network,
    filter_recent_data,
    clean_logic_column
)

# ------------------------------------------------------------
# Logging setup (writes to bg_disruption.log)
# ------------------------------------------------------------
logging.basicConfig(
    filename='bg_disruption.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def process_data():
    # 1. Load all file paths from file_paths.json
    file_paths = load_file_paths()

    # 2. Read claims data (reprice/template file) safely
    if 'reprice' not in file_paths or not file_paths['reprice']:
        logger.error("No 'reprice' entry found in file_paths.json")
        print("Error: No reprice/template file provided.")
        return

    try:
        claims_data = safe_read_excel(
            file_paths['reprice'],
            sheet_name='Claims Table',
            usecols=[
                'SOURCERECORDID', 'NDC', 'MemberID', 'DATEFILLED',
                'FormularyTier', 'Rxs', 'Logic', 'PHARMACYNPI', 'NABP',
                'Pharmacy Name', 'Universal Rebates', 'Exclusive Rebates'
            ]
        )
    except ValueError as e:
        # Fallback to "Sheet1" if "Claims Table" not present
        logger.warning(f"Could not load 'Claims Table': {e}. Trying 'Sheet1'.")
        try:
            claims_data = safe_read_excel(
                file_paths['reprice'],
                sheet_name='Sheet1',
                usecols=[
                    'SOURCERECORDID', 'NDC', 'MemberID', 'DATEFILLED',
                    'FormularyTier', 'Rxs', 'Logic', 'PHARMACYNPI', 'NABP',
                    'Pharmacy Name', 'Universal Rebates', 'Exclusive Rebates'
                ]
            )
        except Exception as ex:
            logger.error(f"Failed to load claims file on fallback: {ex}")
            print("Error: Required columns not found in the claims file.")
            return

    medi_data = pd.read_excel(file_paths['medi_span'])[['NDC', 'Maint Drug?', 'Product Name']]
    u_data = pd.read_excel(file_paths['u_disrupt'], sheet_name='Universal NDC')[['NDC', 'Tier']]
    e_data = pd.read_excel(file_paths['e_disrupt'], sheet_name='Alternatives NDC')[['NDC', 'Tier', 'Alternative']]
    network = pd.read_excel(file_paths['n_disrupt'])[['pharmacy_npi', 'pharmacy_nabp', 'pharmacy_is_excluded']]

    df = claims_data.merge(medi_data, on='NDC', how='left') \
                    .merge(u_data, on='NDC', how='left') \
                    .merge(e_data, on='NDC', how='left')
                    
    
    df.rename(columns={"Tier_x": "Universal Tier", "Tier_y": "Exclusive Tier"}, inplace=True)

    # 6. Use utils to standardize pharmacy IDs, then merge with network
    df = standardize_pharmacy_ids(df)  # adds 'pharmacy_id'
    logger.info(f"Columns before merging with network: {df.columns.tolist()}")
    df = merge_with_network(df, network)  # brings in 'pharmacy_is_excluded'
    df.drop_duplicates(inplace=True)

    # 7. Filter to last 6 months and clean Logic exactly like File 0
    df = filter_recent_data(df, date_column="DATEFILLED", months=6)
    df = clean_logic_column(df)

    # 8. Apply same filtering criteria from File 0:
    #    Logic between 5 and 10, Maint Drug? == 'Y', and remove certain Product Names
    df = df[(df["Logic"].between(5, 10)) & (df["Maint Drug?"] == "Y")]

    #    Remove Product Names containing albuterol, ventolin, epinephrine (case‐insensitive),
    #    each as a separate step for clarity (File 0 used three separate loc filters).
    df = df[~df["Product Name"].str.contains(r"\balbuterol\b", case=False, regex=True)]
    df = df[~df["Product Name"].str.contains(r"\bventolin\b", case=False, regex=True)]
    df = df[~df["Product Name"].str.contains(r"\bepinephrine\b", case=False, regex=True)]

    # 9. Ensure 'Alternative' is a string, then drop rows whose Alternative contains
    #    "Covered" or "Use different NDC" (case‐insensitive)
    df["Alternative"] = df["Alternative"].astype(str)
    df = df[~df["Alternative"].str.contains(r"Covered|Use different NDC", case=False, regex=True)]

    # 10. Strip whitespace from FormularyTier (File 0 did .str.strip()), preserve upper/lower as File 0:
    #     File 0 only did .str.strip(); it later upper‐cases when comparing.
    df["FormularyTier"] = df["FormularyTier"].astype(str).str.strip()

    # 11. If for some reason 'pharmacy_id' is missing (it shouldn't be), re‐compute it exactly like File 0:
    if "pharmacy_id" not in df.columns:
        df["pharmacy_id"] = df.apply(
            lambda row: str(row["PHARMACYNPI"]) if pd.notna(row["PHARMACYNPI"]) else str(row["NABP"]),
            axis=1
        )

    # 12. Now reproduce File 0's "Universal Positive", "Universal Negative", etc. logic exactly

    # Convert 'FormularyTier' to uppercase for the comparisons below
    df["FormularyTier"] = df["FormularyTier"].str.upper()

    # (a) Universal Positive: Universal Tier == 1 AND FormularyTier in ['B','BRAND']
    uni_pos_data = df[(df["Universal Tier"] == 1) & (df["FormularyTier"].isin(["B", "BRAND"]))]
    if uni_pos_data.empty:
        # If empty, create a one‐row all‐zeros DataFrame (matching File 0 approach)
        uni_pos_data = pd.DataFrame([[0] * len(df.columns)], columns=df.columns)

    uni_pos_pt = pd.pivot_table(
        uni_pos_data,
        values=["Rxs", "MemberID"],
        index="Product Name",
        aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique}
    )
    # Determine total members in Universal Positive
    if len(uni_pos_data) == 1 and uni_pos_data["Rxs"].sum() == 0:
        uni_pos_total_members = 0
    else:
        uni_pos_total_members = uni_pos_data["MemberID"].nunique()

    # (b) Universal Negative: Universal Tier in [2,3] AND FormularyTier in ['G','GENERIC']
    uni_neg_data = df[
        ((df["Universal Tier"] == 2) | (df["Universal Tier"] == 3))
        & (df["FormularyTier"].isin(["G", "GENERIC"]))
    ]
    if uni_neg_data.empty:
        uni_neg_data = pd.DataFrame([[0] * len(df.columns)], columns=df.columns)

    uni_neg_pt = pd.pivot_table(
        uni_neg_data,
        values=["Rxs", "MemberID"],
        index="Product Name",
        aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique}
    )
    if len(uni_neg_data) == 1 and uni_neg_data["Rxs"].sum() == 0:
        uni_neg_total_members = 0
    else:
        uni_neg_total_members = uni_neg_data["MemberID"].nunique()

    # (c) Exclusive Positive: Exclusive Tier == 1 AND FormularyTier in ['B','BRAND']
    ex_pos_data = df[(df["Exclusive Tier"] == 1) & (df["FormularyTier"].isin(["B", "BRAND"]))]
    if ex_pos_data.empty:
        ex_pos_data = pd.DataFrame([[0] * len(df.columns)], columns=df.columns)

    ex_pos_pt = pd.pivot_table(
        ex_pos_data,
        values=["Rxs", "MemberID"],
        index="Product Name",
        aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique}
    )
    if len(ex_pos_data) == 1 and ex_pos_data["Rxs"].sum() == 0:
        ex_pos_total_members = 0
    else:
        ex_pos_total_members = ex_pos_data["MemberID"].nunique()

    # (d) Exclusive Negative: Exclusive Tier in [2,3] AND FormularyTier in ['G','GENERIC']
    ex_neg_data = df[
        ((df["Exclusive Tier"] == 2) | (df["Exclusive Tier"] == 3))
        & (df["FormularyTier"].isin(["G", "GENERIC"]))
    ]
    if ex_neg_data.empty:
        ex_neg_data = pd.DataFrame([[0] * len(df.columns)], columns=df.columns)

    ex_neg_pt = pd.pivot_table(
        ex_neg_data,
        values=["Rxs", "MemberID"],
        index="Product Name",
        aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique}
    )
    if len(ex_neg_data) == 1 and ex_neg_data["Rxs"].sum() == 0:
        ex_neg_total_members = 0
    else:
        ex_neg_total_members = ex_neg_data["MemberID"].nunique()

    # (e) Exclusions: Exclusive Tier == 'Nonformulary' (string), regardless of FormularyTier
    #     In File 0, this was: df['Exclusive Tier'] == 'Nonformulary'
    ex_ex_data = df[df["Exclusive Tier"] == "Nonformulary"]
    if ex_ex_data.empty:
        ex_ex_data = pd.DataFrame([[0] * len(df.columns)], columns=df.columns)

    ex_ex_pt = pd.pivot_table(
        ex_ex_data,
        values=["Rxs", "MemberID"],
        index="Product Name",
        aggfunc={"Rxs": "sum", "MemberID": pd.Series.nunique}
    )
    if len(ex_ex_data) == 1 and ex_ex_data["Rxs"].sum() == 0:
        ex_ex_total_members = 0
    else:
        ex_ex_total_members = ex_ex_data["MemberID"].nunique()

    # 13. Compute grand totals of members and claims
    total_members = df["MemberID"].nunique()
    total_claims = df["Rxs"].sum()

    # 14. Build the "Summary" sheet exactly as File 0 did
    summary_df = pd.DataFrame({
        "Formulary": [
            "Universal Positive",
            "Universal Negative",
            "Exclusive Positive",
            "Exclusive Negative",
            "Exclusions"
        ],
        "Utilizers": [
            uni_pos_total_members,
            uni_neg_total_members,
            ex_pos_total_members,
            ex_neg_total_members,
            ex_ex_total_members
        ],
        "Rxs": [
            uni_pos_data["Rxs"].sum(),
            uni_neg_data["Rxs"].sum(),
            ex_pos_data["Rxs"].sum(),
            ex_neg_data["Rxs"].sum(),
            ex_ex_data["Rxs"].sum()
        ],
        "% of claims": [
            uni_pos_data["Rxs"].sum() / total_claims if total_claims else 0,
            uni_neg_data["Rxs"].sum() / total_claims if total_claims else 0,
            ex_pos_data["Rxs"].sum() / total_claims if total_claims else 0,
            ex_neg_data["Rxs"].sum() / total_claims if total_claims else 0,
            ex_ex_data["Rxs"].sum() / total_claims if total_claims else 0
        ],
        "": [""] * 5,
        "Totals": [
            f"Members: {total_members}",
            f"Claims: {total_claims}",
            "",
            "",
            ""
        ]
    })

    # 15. Write everything to "LBL for Disruption.xlsx" with the same sheet names and structure
    output_file = "LBL for Disruption.xlsx"
    writer = pd.ExcelWriter(output_file, engine="xlsxwriter")

    # (i) Data sheet
    df.to_excel(writer, sheet_name="Data", index=False)

    # (ii) Summary sheet
    summary_df.to_excel(writer, sheet_name="Summary", index=False)

    # (iii) Pivot sheets for each category
    #      Use sheet names: Universal_Positive, Universal_Negative, Exclusive_Positive, Exclusive_Negative, Exclusions
    pivots = {
        "Universal_Positive": (uni_pos_pt, uni_pos_total_members),
        "Universal_Negative": (uni_neg_pt, uni_neg_total_members),
        "Exclusive_Positive": (ex_pos_pt, ex_pos_total_members),
        "Exclusive_Negative": (ex_neg_pt, ex_neg_total_members),
        "Exclusions": (ex_ex_pt, ex_ex_total_members)
    }
    for sheet_name, (pivot_df, total_mems) in pivots.items():
        pivot_df.to_excel(writer, sheet_name=sheet_name)
        # Write “Total Members: X” into cell F1 exactly as File 0 did
        worksheet = writer.sheets[sheet_name]
        worksheet.write("F1", f"Total Members: {total_mems}")

    # 16. Build the "Network" sheet exactly as File 0 did:
    #     Filter out rows where 'pharmacy_is_excluded' is NaN, then remove pharmacies matching certain phrases
        network_df = df[df['pharmacy_is_excluded'] == True]
        filter_phrases = ['CVS', 'Walgreens', 'Kroger', 'Walmart', 'Rite Aid',
                      'Optum', 'Express Scripts', 'DMR', 'Williams Bro', 'Publix']
    regex_pattern = '|'.join([f"\\b{phrase}\\b" for phrase in filter_phrases])
    network_df = network_df[~network_df['Pharmacy Name'].str.contains(regex_pattern, case=False, regex=True)]
    if {'PHARMACYNPI', 'NABP', 'Pharmacy Name'}.issubset(network_df.columns):
        pivot = pd.pivot_table(
            network_df,
            values=['Rxs', 'MemberID'],
            index=['PHARMACYNPI', 'NABP', 'Pharmacy Name'],
            aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique}
        )
        pivot.to_excel(writer, sheet_name='Network')

    # 17. Finalize and save
    writer.close()
    logger.info("Disruption processing completed successfully.")
    print("Processing complete: wrote 'LBL for Disruption.xlsx'.")


if __name__ == "__main__":
    process_data()
    print("Processing complete") # or exit(0)


