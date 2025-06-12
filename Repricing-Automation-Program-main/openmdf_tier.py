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
    filename='openmdf_tier.log',
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
            usecols=['SOURCERECORDID','NDC', 'MemberID', 'DATEFILLED', 'FormularyTier', 'Rxs', 'Logic',
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

    df['FormularyTier'] = pd.to_numeric(df['FormularyTier'], errors='coerce')
    total_claims = df['Rxs'].sum()
    total_members = df['MemberID'].nunique()

    writer = pd.ExcelWriter('LBL for Disruption.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Data', index=False)

    combos = [
        ('OpenMDF_Positive 2-1', 1, 2),
        ('OpenMDF_Positive 3-1', 1, 3),
        ('OpenMDF_Positive 3-2', 2, 3),
        ('OpenMDF_Negative 1-2', 2, 1),
        ('OpenMDF_Negative 1-3', 3, 1),
        ('OpenMDF_Negative 2-3', 3, 2)
    ]

    summary_data = []

    for name, mdf_tier, form_tier in combos:
        subset = df[(df['Tier'] == mdf_tier) & (df['FormularyTier'] == form_tier)]
        pt = pd.pivot_table(subset, values=['Rxs', 'MemberID'], index='Product Name',
                            aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})
        members = subset['MemberID'].nunique()
        claims = subset['Rxs'].sum()
        pt.to_excel(writer, sheet_name=name)
        writer.sheets[name].write('F1', f'Total Members: {members}')
        summary_data.append((name, members, claims))

    summary_df = pd.DataFrame({
        'Formulary': [x[0] for x in summary_data],
        'Utilizers': [x[1] for x in summary_data],
        'Rxs': [x[2] for x in summary_data],
        '% of claims': [x[2] / total_claims if total_claims else 0 for x in summary_data],
        '': [''] * len(summary_data),
        'Totals': [f'Members: {total_members}', f'Claims: {total_claims}'] + [''] * (len(summary_data) - 2)
    })
    summary_df.to_excel(writer, sheet_name='Summary', index=False)

    network_df = df[df['pharmacy_is_excluded'].isna()]
    exclude_list = ['CVS', 'Walgreens', 'Kroger', 'Walmart', 'Rite Aid', 'Optum', 'Express Scripts', 'DMR', 'Williams Bro', 'Publix']
    pattern = '|'.join([f'\b{x}\b' for x in exclude_list])
    network_df = network_df[~network_df['Pharmacy Name'].str.contains(pattern, case=False, regex=True)]

    if {'pharmacy_id', 'Pharmacy Name'}.issubset(network_df.columns):
        pd.pivot_table(network_df, values=['Rxs', 'MemberID'], index=['pharmacy_id', 'Pharmacy Name'],
                       aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique}).to_excel(writer, sheet_name='Network')

    writer.close()
    logger.info("Open MDF Tier processing completed successfully.")

if __name__ == '__main__':
    process_data()
    print("Processing complete")  # or exit(0)
