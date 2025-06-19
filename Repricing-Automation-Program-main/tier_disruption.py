import pandas as pd
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

#---------------------------------------------------------------------------
# Tier summarization helper
#---------------------------------------------------------------------------
def summarize_by_tier(df, col, from_val, to_val):
    filtered = df[(df[col] == from_val) & (df['FormularyTier'] == to_val)]
    pt = pd.pivot_table(
        filtered,
        values=['Rxs', 'MemberID'],
        index=['Product Name'],
        aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique}
    )
    rxs = filtered['Rxs'].sum()
    members = filtered['MemberID'].nunique()
    return pt, rxs, members

#---------------------------------------------------------------------------
# Main processing pipeline
#---------------------------------------------------------------------------
def process_data():
    file_paths = load_file_paths('file_paths.json')

    # Load claims with fallback
    if not file_paths.get('reprice'):
        print("No reprice/template file provided. Skipping claims loading.")
        return
    try:
        claims = pd.read_excel(file_paths['reprice'], sheet_name='Claims Table')
    except Exception:
        claims = pd.read_excel(file_paths['reprice'], sheet_name=0)

    # Load reference tables
    medi = pd.read_excel(file_paths['medi_span'], usecols=['NDC', 'Maint Drug?', 'Product Name'])
    u = pd.read_excel(file_paths['u_disrupt'], sheet_name='Universal NDC', usecols=['NDC', 'Tier'])
    e = pd.read_excel(file_paths['e_disrupt'], sheet_name='Alternatives NDC', usecols=['NDC', 'Tier', 'Alternative'])
    network = pd.read_excel(file_paths['n_disrupt'], usecols=['pharmacy_npi', 'pharmacy_nabp', 'pharmacy_is_excluded'])

    # Merge reference data
    df = claims.merge(medi, on='NDC', how='left')
    df = df.merge(u.rename(columns={'Tier': 'Universal Tier'}), on='NDC', how='left')
    df = df.merge(e.rename(columns={'Tier': 'Exclusive Tier'}), on='NDC', how='left')

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

    # Totals for summary
    total_claims = df['Rxs'].sum()
    total_members = df['MemberID'].nunique()

    # Excel writer setup
    writer = pd.ExcelWriter('LBL for Disruption.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Data', index=False)

    # Define tier sheets with filters matching the copy logic
    tiers = [
        ('Universal_Positive 2-1', 'Universal Tier', 1, 2),
        ('Universal_Positive 3-1', 'Universal Tier', 1, 3),
        ('Universal_Positive 3-2', 'Universal Tier', 2, 3),
        ('Universal_Negative 1-2', 'Universal Tier', 2, 1),
        ('Universal_Negative 1-3', 'Universal Tier', 3, 1),
        ('Universal_Negative 2-3', 'Universal Tier', 3, 2),
        ('Exclusive_Positive 2-1', 'Exclusive Tier', 1, 2),
        ('Exclusive_Positive 3-1', 'Exclusive Tier', 1, 3),
        ('Exclusive_Positive 3-2', 'Exclusive Tier', 2, 3),
        ('Exclusive_Negative 1-2', 'Exclusive Tier', 2, 1),
        ('Exclusive_Negative 1-3', 'Exclusive Tier', 3, 1),
        ('Exclusive_Negative 2-3', 'Exclusive Tier', 3, 2),
    ]

    tab_members = {}
    tab_rxs = {}

    # Generate tier pivot sheets
    for name, col, from_val, to_val in tiers:
        pt, rxs, members = summarize_by_tier(df, col, from_val, to_val)
        pt.to_excel(writer, sheet_name=name)
        tab_members[name] = members
        tab_rxs[name] = rxs

    # Exclusions sheet (Nonformulary)
    exclusions = df[df['Exclusive Tier'] == 'Nonformulary']
    ex_pt = exclusions.pivot_table(
        values=['Rxs', 'MemberID'],
        index=['Product Name', 'Alternative'],
        aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique}
    )
    ex_pt.to_excel(writer, sheet_name='Exclusions')
    exc_rxs = exclusions['Rxs'].sum()
    exc_members = exclusions['MemberID'].nunique()
    tab_members['Exclusions'] = exc_members
    tab_rxs['Exclusions'] = exc_rxs

    # Summary calculations
    uni_pos_keys = ['Universal_Positive 2-1', 'Universal_Positive 3-1', 'Universal_Positive 3-2']
    uni_neg_keys = ['Universal_Negative 1-2', 'Universal_Negative 1-3', 'Universal_Negative 2-3']
    ex_pos_keys = ['Exclusive_Positive 2-1', 'Exclusive_Positive 3-1', 'Exclusive_Positive 3-2']
    ex_neg_keys = ['Exclusive_Negative 1-2', 'Exclusive_Negative 1-3', 'Exclusive_Negative 2-3']

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

    exc_utilizers = tab_members['Exclusions']
    exc_claims = tab_rxs['Exclusions']
    exc_pct = exc_claims / total_claims if total_claims else 0

    summary_df = pd.DataFrame({
        'Formulary': [
            'Universal Positive',
            'Universal Negative',
            'Exclusive Positive',
            'Exclusive Negative',
            'Exclusions'
        ],
        'Utilizers': [
            uni_pos_utilizers,
            uni_neg_utilizers,
            ex_pos_utilizers,
            ex_neg_utilizers,
            exc_utilizers
        ],
        'Rxs': [
            uni_pos_claims,
            uni_neg_claims,
            ex_pos_claims,
            ex_neg_claims,
            exc_claims
        ],
        '% of claims': [
            uni_pos_pct,
            uni_neg_pct,
            ex_pos_pct,
            ex_neg_pct,
            exc_pct
        ],
        '': ['', '', '', '', ''],
        'Totals': [
            f'Members: {total_members}',
            f'Claims: {total_claims}',
            '',
            '',
            ''
        ]
    })
    summary_df.to_excel(writer, sheet_name='Summary', index=False)

    # Annotate total members on each sheet
    for sheet_name, members in tab_members.items():
        writer.sheets[sheet_name].write('F1', f'Total Members: {members}')

    # Network summary for non-excluded pharmacies
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

    # Reorder sheets so Summary follows Data
    wworkbook = writer.book
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

    writer.close()

if __name__ == '__main__':
    process_data()
    print("Data processing complete")
