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

# Setup logging
logging.basicConfig(
    filename='openmdf_bg.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def process_data():
    paths = load_file_paths()

    claims = None
    if 'reprice' in paths and paths['reprice']:
        claims = safe_read_excel(
            paths['reprice'],
            sheet_name='Claims Table',
            usecols=['SOURCERECORDID', 'NDC', 'MemberID', 'DATEFILLED', 'FormularyTier', 'Rxs', 'Logic',
                     'PHARMACYNPI', 'NABP', 'Pharmacy Name', 'Universal Rebates', 'Exclusive Rebates']
        )
    else:
        logger.warning("No reprice/template file provided. Skipping claims loading.")
        print("No reprice/template file provided. Skipping claims loading.")
        return  # or continue with alternate logic

    medi = pd.read_excel(paths['medi_span'])[['NDC', 'Maint Drug?', 'Product Name']]
    mdf = pd.read_excel(paths['mdf_disrupt'], sheet_name='Open MDF NDC')[['NDC', 'Tier']]
    network = pd.read_excel(paths['n_disrupt'])[['pharmacy_npi', 'pharmacy_nabp', 'pharmacy_is_excluded']]

    df = claims.merge(medi, on='NDC', how='left').merge(mdf, on='NDC', how='left')
    df = standardize_pharmacy_ids(df)

    # Debug print and log
    print("Columns in df before merging with network:")
    print(df.columns)
    logger.info(f"Columns in df before merging: {df.columns.tolist()}")

    df = merge_with_network(df, network)
    df.drop_duplicates(inplace=True)

    df = filter_recent_data(df, date_column='DATEFILLED', months=6)
    df = clean_logic_column(df)

    df = df[(df['Logic'].between(5, 10)) & (df['Maint Drug?'] == 'Y')]
    df = df[~df['Product Name'].str.contains(r'albuterol|ventolin|epinephrine', case=False, regex=True)]

    df['FormularyTier'] = df['FormularyTier'].astype(str).str.strip().str.upper()
    total_members = df['MemberID'].nunique()
    total_claims = df['Rxs'].sum()

    uni_pos = df[(df['Tier'] == 1) & (df['FormularyTier'].isin(['B', 'BRAND']))]
    uni_neg = df[(df['Tier'].isin([2, 3])) & (df['FormularyTier'].isin(['G', 'GENERIC']))]

    def pivot_and_count(data):
        if data.empty:
            return pd.DataFrame([[0] * len(df.columns)], columns=df.columns), 0
        return data, data['MemberID'].nunique()

    uni_pos, uni_pos_members = pivot_and_count(uni_pos)
    uni_neg, uni_neg_members = pivot_and_count(uni_neg)

    writer = pd.ExcelWriter('LBL for Disruption.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Data', index=False)

    summary = pd.DataFrame({
        'Formulary': ['Open MDF Positive', 'Open MDF Negative'],
        'Utilizers': [uni_pos_members, uni_neg_members],
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

    writer.sheets['OpenMDF_Positive'].write('F1', f'Total Members: {uni_pos_members}')
    writer.sheets['OpenMDF_Negative'].write('F1', f'Total Members: {uni_neg_members}')

    network_df = df[df['pharmacy_is_excluded'].isna()]
    exclude = ['CVS', 'Walgreens', 'Kroger', 'Walmart', 'Rite Aid', 'Optum',
               'Express Scripts', 'DMR', 'Williams Bro', 'Publix']
    regex = '|'.join([f'\b{x}\b' for x in exclude])
    network_df = network_df[~network_df['Pharmacy Name'].str.contains(regex, case=False, regex=True)]

    if {'pharmacy_id', 'Pharmacy Name'}.issubset(network_df.columns):
        pd.pivot_table(network_df, values=['Rxs', 'MemberID'],
                       index=['pharmacy_id', 'Pharmacy Name'],
                       aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique}) \
            .to_excel(writer, sheet_name='Network')

    writer.close()
    logger.info("Open MDF BG processing completed.")

if __name__ == '__main__':
    process_data()
    print("Processing complete") # or exit(0)
