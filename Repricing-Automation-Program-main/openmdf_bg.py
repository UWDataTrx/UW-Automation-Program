import pandas as pd
import logging
from utils import (
    load_file_paths,
    standardize_pharmacy_ids,
    standardize_network_ids,
    merge_with_network,
    drop_duplicates_df,
    filter_recent_date,
    clean_logic_and_tier,
    filter_logic_and_maintenance
)

logging.basicConfig(
    filename='openmdf_bg.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def process_data():
    paths = load_file_paths()

    claims = pd.read_excel(paths['reprice'], sheet_name='Claims Table')
    medi = pd.read_excel(paths['medi_span'])[['NDC', 'Maint Drug?', 'Product Name']]
    mdf = pd.read_excel(paths['mdf_disrupt'], sheet_name='Open MDF NDC')[['NDC', 'Tier']]
    network = pd.read_excel(paths['n_disrupt'])[['pharmacy_npi', 'pharmacy_nabp', 'pharmacy_is_excluded']]

    df = claims.merge(medi, on='NDC', how='left').merge(mdf, on='NDC', how='left')
    df = standardize_pharmacy_ids(df)
    network = standardize_network_ids(network)

    print("Columns in df before merging with network:")
    print(df.columns)
    logger.info(f"Columns in df before merging: {df.columns.tolist()}")

    df = merge_with_network(df, network)
    df = drop_duplicates_df(df)
    df = filter_recent_date(df)
    df = clean_logic_and_tier(df)
    df = filter_logic_and_maintenance(df)

    df = df[(df['Logic'].between(5, 10)) & (df['Maint Drug?'] == 'Y')]
    df = df[~df['Product Name'].str.contains(r'albuterol|ventolin|epinephrine', case=False, regex=True)]

    df['FormularyTier'] = df['FormularyTier'].astype(str).str.strip().str.upper()
    total_members = df['MemberID'].nunique()
    total_claims = df['Rxs'].sum()

    uni_pos = df[(df['Tier'] == 1) & (df['FormularyTier'].isin(['B', 'BRAND']))]
    uni_neg = df[(df['Tier'].isin([2, 3])) & (df['FormularyTier'].isin(['G', 'GENERIC']))]

    writer = pd.ExcelWriter('LBL for Disruption.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Data', index=False)

    summary = pd.DataFrame({
        'Formulary': ['Open MDF Positive', 'Open MDF Negative'],
        'Utilizers': [uni_pos['MemberID'].nunique(), uni_neg['MemberID'].nunique()],
        'Rxs': [uni_pos['Rxs'].sum(), uni_neg['Rxs'].sum()],
        '% of claims': [uni_pos['Rxs'].sum() / total_claims, uni_neg['Rxs'].sum() / total_claims],
        '': ['', ''],
        'Totals': [f'Members: {total_members}', f'Claims: {total_claims}']
    })
    summary.to_excel(writer, sheet_name='Summary', index=False)

    pd.pivot_table(uni_pos, values=['Rxs', 'MemberID'], index='Product Name',
                   aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique}).to_excel(writer, sheet_name='OpenMDF_Positive')
    pd.pivot_table(uni_neg, values=['Rxs', 'MemberID'], index='Product Name',
                   aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique}).to_excel(writer, sheet_name='OpenMDF_Negative')

    writer.sheets['OpenMDF_Positive'].write('F1', f'Total Members: {uni_pos["MemberID"].nunique()}')
    writer.sheets['OpenMDF_Negative'].write('F1', f'Total Members: {uni_neg["MemberID"].nunique()}')

    network_df = df[df['pharmacy_is_excluded'] == True]
    exclude = ['CVS', 'Walgreens', 'Kroger', 'Walmart', 'Rite Aid', 'Optum',
               'Express Scripts', 'DMR', 'Williams Bro', 'Publix']
    regex = '|'.join([f'\\b{x}\\b' for x in exclude])
    network_df = network_df[~network_df['Pharmacy Name'].str.contains(regex, case=False, regex=True)]

    if {'pharmacy_id', 'Pharmacy Name'}.issubset(network_df.columns):
        pd.pivot_table(network_df, values=['Rxs', 'MemberID'],
                       index=['pharmacy_id', 'Pharmacy Name'],
                       aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique}).to_excel(writer, sheet_name='Network')

    # Reorder summary after data
    workbook = writer.book
    sheets = workbook.worksheets()
    names = [ws.get_name() for ws in sheets]
    if 'Data' in names and 'Summary' in names:
        d_idx = names.index('Data')
        s_idx = names.index('Summary')
        if s_idx != d_idx + 1:
            ws = sheets.pop(s_idx)
            sheets.insert(d_idx + 1, ws)

    writer.close()
    logger.info("Open MDF BG processing completed.")
    print("Processing complete")

if __name__ == '__main__':
    process_data()