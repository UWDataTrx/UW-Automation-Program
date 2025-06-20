import pandas as pd
import logging
from utils import (
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

# Logging setup
logging.basicConfig(
    filename='bg_disruption.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def process_data():
    write_shared_log("bg_disruption.py", "Processing started.")
    file_paths = load_file_paths()
    if 'reprice' not in file_paths or not file_paths['reprice']:
        write_shared_log("bg_disruption.py", "No reprice/template file provided.", status="ERROR")
        print("Error: No reprice/template file provided.")
        return

    try:
        claims = pd.read_excel(
            file_paths['reprice'],
            sheet_name='Claims Table',
            usecols=[
                'SOURCERECORDID', 'NDC', 'MemberID', 'DATEFILLED',
                'FormularyTier', 'Rxs', 'Logic', 'PHARMACYNPI', 'NABP',
                'Pharmacy Name', 'Universal Rebates', 'Exclusive Rebates'
            ]
        )
    except Exception as e:
        logger.warning(f"Claims Table fallback: {e}")
        write_shared_log("bg_disruption.py", f"Claims Table fallback: {e}", status="WARNING")
        claims = pd.read_excel(file_paths['reprice'], sheet_name=0)

    medi = pd.read_excel(file_paths['medi_span'])[['NDC', 'Maint Drug?', 'Product Name']]
    uni = pd.read_excel(file_paths['u_disrupt'], sheet_name='Universal NDC')[['NDC', 'Tier']]
    exl = pd.read_excel(file_paths['e_disrupt'], sheet_name='Alternatives NDC')[['NDC', 'Tier', 'Alternative']]
    network = pd.read_excel(file_paths['n_disrupt'])[['pharmacy_npi', 'pharmacy_nabp', 'pharmacy_is_excluded']]

    df = claims.merge(medi, on='NDC', how='left') \
               .merge(uni.rename(columns={'Tier': 'Universal Tier'}), on='NDC', how='left') \
               .merge(exl.rename(columns={'Tier': 'Exclusive Tier'}), on='NDC', how='left')

    # Standardize IDs and perform network merge
    df = standardize_pharmacy_ids(df)
    network = standardize_network_ids(network)
    df = merge_with_network(df, network)

    # Date parsing, deduplication, type cleaning, and filters
    df['DATEFILLED'] = pd.to_datetime(df['DATEFILLED'], errors='coerce')
    df = drop_duplicates_df(df)
    df = clean_logic_and_tier(df)
    df = filter_recent_date(df)
    df = filter_logic_and_maintenance(df)
    df = filter_products_and_alternative(df)

    df['FormularyTier'] = df['FormularyTier'].astype(str).str.strip().str.upper()
    df['Alternative'] = df['Alternative'].astype(str)

    # Define filters
    uni_pos = df[(df['Universal Tier'] == 1) & df['FormularyTier'].isin(['B', 'BRAND'])]
    uni_neg = df[df['Universal Tier'].isin([2,3]) & df['FormularyTier'].isin(['G', 'GENERIC'])]
    ex_pos = df[(df['Exclusive Tier'] == 1) & df['FormularyTier'].isin(['B', 'BRAND'])]
    ex_neg = df[df['Exclusive Tier'].isin([2,3]) & df['FormularyTier'].isin(['G', 'GENERIC'])]
    ex_ex = df[df['Exclusive Tier'] == 'Nonformulary']

    # Build pivots
    def pivot(d): return pd.pivot_table(d, values=['Rxs', 'MemberID'], index='Product Name',
                                         aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})
    def count(d): return 0 if d.empty or d['Rxs'].sum() == 0 else d['MemberID'].nunique()

    tabs = {
        "Universal_Positive": (uni_pos, pivot(uni_pos), count(uni_pos)),
        "Universal_Negative": (uni_neg, pivot(uni_neg), count(uni_neg)),
        "Exclusive_Positive": (ex_pos, pivot(ex_pos), count(ex_pos)),
        "Exclusive_Negative": (ex_neg, pivot(ex_neg), count(ex_neg)),
        "Exclusions": (ex_ex, pivot(ex_ex), count(ex_ex)),
    }

    total_members = df['MemberID'].nunique()
    total_claims = df['Rxs'].sum()

    summary = pd.DataFrame({
        "Formulary": ["Universal Positive", "Universal Negative", "Exclusive Positive", "Exclusive Negative", "Exclusions"],
        "Utilizers": [v[2] for v in tabs.values()],
        "Rxs": [v[0]['Rxs'].sum() for v in tabs.values()],
        "% of claims": [v[0]['Rxs'].sum() / total_claims if total_claims else 0 for v in tabs.values()],
        "": ["" for _ in tabs],
        "Totals": [f"Members: {total_members}", f"Claims: {total_claims}", "", "", ""]
    })

    writer = pd.ExcelWriter("LBL for Disruption.xlsx", engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Data", index=False)
    summary.to_excel(writer, sheet_name="Summary", index=False)

    for sheet, (_, pt, mems) in tabs.items():
        pt.to_excel(writer, sheet_name=sheet)
        writer.sheets[sheet].write("F1", f"Total Members: {mems}")

     # Network summary for non-excluded pharmacies
    network_df = df[df['pharmacy_is_excluded'] == True]
    filter_phrases = ['CVS', 'Walgreens', 'Kroger', 'Walmart', 'Rite Aid',
                      'Optum', 'Express Scripts', 'DMR', 'Williams Bro', 'Publix']
    regex_pattern = '|'.join([f"\\b{phrase}\\b" for phrase in filter_phrases])
    network_df = network_df[~network_df['Pharmacy Name'].str.contains(regex_pattern, case=False, regex=True)]
    if {'PHARMACYNPI', 'NABP', 'Pharmacy Name'}.issubset(network_df.columns):
        network_pivot = pd.pivot_table(
            network_df,
            values=['Rxs', 'MemberID'],
            index=['PHARMACYNPI', 'NABP', 'Pharmacy Name'],
            aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique}
        )
        network_pivot.to_excel(writer, sheet_name='Network')

    # Reorder Summary after Data
    workbook = writer.book
    sheets = writer.sheets  # This is a dict: {sheet_name: worksheet_object}
    names = list(sheets.keys())
    if "Data" in names and "Summary" in names:
        data_idx, sum_idx = names.index("Data"), names.index("Summary")
        if sum_idx != data_idx + 1:
            # Reorder the sheets dict to move "Summary" after "Data"
            items = list(sheets.items())
            summary_item = items.pop(sum_idx)
            items.insert(data_idx + 1, summary_item)
            writer.sheets.clear()
            writer.sheets.update(dict(items))

    writer.close()
    write_shared_log("bg_disruption.py", "Processing complete.")
    print("Processing complete")

if __name__ == "__main__":
    process_data()
