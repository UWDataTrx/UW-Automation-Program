import pandas as pd
import logging
from utils import (
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
    filename='openmdf_tier.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def process_data():
    paths = load_file_paths()

    if 'reprice' not in paths or not paths['reprice']:
        logger.warning("No reprice/template file provided.")
        print("No reprice/template file provided.")
        return

    claims = pd.read_excel(paths['reprice'], sheet_name='Claims Table')

    medi = pd.read_excel(paths['medi_span'])[['NDC', 'Maint Drug?', 'Product Name']]
    mdf = pd.read_excel(paths['mdf_disrupt'], sheet_name='Open MDF NDC')[['NDC', 'Tier']]
    exclusive = pd.read_excel(paths['e_disrupt'], sheet_name='Alternatives NDC')[['NDC', 'Tier', 'Alternative']]
    network = pd.read_excel(paths['n_disrupt'])[['pharmacy_npi', 'pharmacy_nabp', 'pharmacy_is_excluded']]

    df = claims.merge(medi, on='NDC', how='left')
    df = df.merge(mdf.rename(columns={'Tier': 'Open MDF Tier'}), on='NDC', how='left')
    df = df.merge(exclusive.rename(columns={'Tier': 'Exclusive Tier'}), on='NDC', how='left')

    df = standardize_pharmacy_ids(df)
    network = standardize_network_ids(network)
    df = merge_with_network(df, network)

    if 'pharmacy_id' not in df.columns:
        df['pharmacy_id'] = df.apply(
            lambda row: row['PHARMACYNPI'] if pd.notna(row['PHARMACYNPI']) else row['NABP'],
            axis=1
        )

    print("Columns in df before merging with network:")
    print(df.columns)

    df = drop_duplicates_df(df)
    df['DATEFILLED'] = pd.to_datetime(df['DATEFILLED'], errors='coerce')
    df = filter_recent_date(df)
    df = clean_logic_and_tier(df)
    df = filter_logic_and_maintenance(df)
    df = filter_products_and_alternative(df)

    df['FormularyTier'] = pd.to_numeric(df['FormularyTier'], errors='coerce')
    total_claims = df['Rxs'].sum()
    total_members = df['MemberID'].nunique()

    writer = pd.ExcelWriter('LBL for Disruption.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Data', index=False)

    # Define combo tiers
    tiers = [
        ('OpenMDF_Positive 2-1', 1, 2),
        ('OpenMDF_Positive 3-1', 1, 3),
        ('OpenMDF_Positive 3-2', 2, 3),
        ('OpenMDF_Negative 1-2', 2, 1),
        ('OpenMDF_Negative 1-3', 3, 1),
        ('OpenMDF_Negative 2-3', 3, 2),
    ]

    pos_keys = []
    neg_keys = []
    tab_members = {}
    tab_rxs = {}

    for name, from_val, to_val in tiers:
        filtered = df[(df['Open MDF Tier'] == from_val) & (df['FormularyTier'] == to_val)]
        pt = pd.pivot_table(
            filtered,
            values=['Rxs', 'MemberID'],
            index='Product Name',
            aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique}
        )
        members = filtered['MemberID'].nunique()
        rxs = filtered['Rxs'].sum()
        pt.to_excel(writer, sheet_name=name)
        writer.sheets[name].write('F1', f'Total Members: {members}')
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

    summary_df = pd.DataFrame({
        'Formulary': ['Open MDF Positive', 'Open MDF Negative'],
        'Utilizers': [pos_total_members, neg_total_members],
        'Rxs': [pos_total_rxs, neg_total_rxs],
        '% of claims': [pos_pct, neg_pct],
        '': ['', ''],
        'Totals': [f'Members: {total_members}', f'Claims: {total_claims}']
    })
    summary_df.to_excel(writer, sheet_name='Summary', index=False)

    # Write Network
    network_df = df[df['pharmacy_is_excluded'] == True]
    exclude_list = ['CVS', 'Walgreens', 'Kroger', 'Walmart', 'Rite Aid', 'Optum',
                    'Express Scripts', 'DMR', 'Williams Bro', 'Publix']
    pattern = '|'.join([f'\\b{x}\\b' for x in exclude_list])
    network_df = network_df[~network_df['Pharmacy Name'].str.contains(pattern, case=False, regex=True)]

    if {'pharmacy_id', 'Pharmacy Name'}.issubset(network_df.columns):
        pd.pivot_table(network_df, values=['Rxs', 'MemberID'],
                       index=['pharmacy_id', 'Pharmacy Name'],
                       aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique}).to_excel(writer, sheet_name='Network')

    # Reorder Summary right after Data
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
    print("Processing complete")

if __name__ == '__main__':
    process_data()
    print("Processing complete")
