import pandas as pd
import json
import os

# Standardize IDs

def standardize_pharmacy_ids(df):
    if 'PHARMACYNPI' in df.columns:
        df['PHARMACYNPI'] = df['PHARMACYNPI'].astype(str).str.zfill(10)
    if 'NABP' in df.columns:
        df['NABP'] = df['NABP'].astype(str).str.zfill(7)
    return df

def standardize_network_ids(network):
    if 'pharmacy_npi' in network.columns:
        network['pharmacy_npi'] = network['pharmacy_npi'].astype(str).str.zfill(10)
    if 'pharmacy_nabp' in network.columns:
        network['pharmacy_nabp'] = network['pharmacy_nabp'].astype(str).str.zfill(7)
    return network

def merge_with_network(df, network):
    return df.merge(network, left_on=['PHARMACYNPI', 'NABP'], right_on=['pharmacy_npi', 'pharmacy_nabp'], how='left')

def load_file_paths(json_file):
    with open(json_file, 'r') as f:
        file_paths = json.load(f)
    return file_paths

def summarize_by_tier(df, col, from_val, to_val):
    filtered = df[(df[col] == from_val) & (df['FormularyTier'] == to_val)]
    pt = pd.pivot_table(filtered, values=['Rxs', 'MemberID'], index=['Product Name'],
                        aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})
    rxs = filtered['Rxs'].sum()
    members = filtered['MemberID'].nunique()
    return pt, rxs, members

def process_data():
    file_paths = load_file_paths('file_paths.json')

    # Only load claims if the path is present and not empty
    claims = None
    if 'reprice' in file_paths and file_paths['reprice']:
        claims = pd.read_excel(file_paths['reprice'], sheet_name='Claims Table')
    else:
        print("No reprice/template file provided. Skipping claims loading.")
        # You can decide to return, raise, or continue with alternate logic here
        return

    medi = pd.read_excel(file_paths['medi_span'])[['NDC', 'Maint Drug?', 'Product Name']]
    u = pd.read_excel(file_paths['u_disrupt'], sheet_name='Universal NDC')[['NDC', 'Tier']]
    e = pd.read_excel(file_paths['e_disrupt'], sheet_name='Alternatives NDC')[['NDC', 'Tier', 'Alternative']]
    network = pd.read_excel(file_paths['n_disrupt'])[['pharmacy_npi', 'pharmacy_nabp', 'pharmacy_is_excluded']]

    df = claims.merge(medi, on='NDC', how='left')
    df = df.merge(u.rename(columns={'Tier': 'Universal Tier'}), on='NDC', how='left')
    df = df.merge(e.rename(columns={'Tier': 'Exclusive Tier'}), on='NDC', how='left')

    df = standardize_pharmacy_ids(df)
    network = standardize_network_ids(network)
    df = merge_with_network(df, network)

    df['DATEFILLED'] = pd.to_datetime(df['DATEFILLED'], errors='coerce')
    df = df.drop_duplicates()
    df['Logic'] = pd.to_numeric(df['Logic'], errors='coerce')
    df['FormularyTier'] = pd.to_numeric(df['FormularyTier'], errors='coerce')

    latest_date = df['DATEFILLED'].max()
    starting_point = latest_date - pd.DateOffset(months=6) + pd.DateOffset(days=1)
    df = df[(df['DATEFILLED'] >= starting_point) & (df['DATEFILLED'] <= latest_date)]
    df = df[(df['Logic'] >= 5) & (df['Logic'] <= 10) & (df['Maint Drug?'] == 'Y')]
    df = df[~df['Product Name'].str.contains(r'\balbuterol\b', case=False)]
    df = df[~df['Product Name'].str.contains(r'\bventolin\b', case=False)]
    df = df[~df['Product Name'].str.contains(r'\bepinephrine\b', case=False)]
    df = df[~df['Alternative'].astype(str).str.contains('Covered|Use different NDC', case=False, regex=True)]

    total_claims = df['Rxs'].sum()
    total_members = df['MemberID'].nunique()

    writer = pd.ExcelWriter('LBL for Disruption.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Data', index=False)

    tiers = [
        ('Universal_Positive 2-1', 'Universal Tier', 2, 1),
        ('Universal_Positive 3-1', 'Universal Tier', 3, 1),
        ('Universal_Positive 3-2', 'Universal Tier', 3, 2),
        ('Universal_Negative 1-2', 'Universal Tier', 1, 2),
        ('Universal_Negative 1-3', 'Universal Tier', 1, 3),
        ('Universal_Negative 2-3', 'Universal Tier', 2, 3),
        ('Exclusive_Positive 2-1', 'Exclusive Tier', 2, 1),
        ('Exclusive_Positive 3-1', 'Exclusive Tier', 3, 1),
        ('Exclusive_Positive 3-2', 'Exclusive Tier', 3, 2),
        ('Exclusive_Negative 1-2', 'Exclusive Tier', 1, 2),
        ('Exclusive_Negative 1-3', 'Exclusive Tier', 1, 3),
        ('Exclusive_Negative 2-3', 'Exclusive Tier', 2, 3),
    ]

    summary_rows = []
    tab_members = {}

    for name, col, from_val, to_val in tiers:
        pt, rxs, members = summarize_by_tier(df, col, from_val, to_val)
        pt.to_excel(writer, sheet_name=name)
        summary_rows.append((name.replace('_', ' '), members, rxs))
        tab_members[name] = members

    exclusions = df[df['pharmacy_is_excluded'] == True]
    ex_pt = exclusions.pivot_table(values=['Rxs', 'MemberID'], index=['Product Name'],
                                   aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})
    exc_rxs = exclusions['Rxs'].sum()
    exc_members = exclusions['MemberID'].nunique()
    ex_pt.to_excel(writer, sheet_name='Exclusions')

    summary_rows.append(('Exclusions', exc_members, exc_rxs))
    tab_members['Exclusions'] = exc_members

    # Aggregate utilizer and claims counts for summary
    uni_pos_utilizers = tab_members.get('Universal_Positive 2-1', 0) + tab_members.get('Universal_Positive 3-1', 0) + tab_members.get('Universal_Positive 3-2', 0)
    uni_neg_utilizers = tab_members.get('Universal_Negative 1-2', 0) + tab_members.get('Universal_Negative 1-3', 0) + tab_members.get('Universal_Negative 2-3', 0)
    ex_pos_utilizers = tab_members.get('Exclusive_Positive 2-1', 0) + tab_members.get('Exclusive_Positive 3-1', 0) + tab_members.get('Exclusive_Positive 3-2', 0)
    ex_neg_utilizers = tab_members.get('Exclusive_Negative 1-2', 0) + tab_members.get('Exclusive_Negative 1-3', 0) + tab_members.get('Exclusive_Negative 2-3', 0)
    exc_utilizers = tab_members.get('Exclusions', 0)

    # Similarly, aggregate claims for each group
    uni_pos_claims = 0
    uni_neg_claims = 0
    ex_pos_claims = 0
    ex_neg_claims = 0
    exc_claims = exc_rxs

    for name, _, _, _ in tiers:
        if name.startswith('Universal_Positive'):
            uni_pos_claims += df[(df['Universal Tier'] == int(name.split()[1][0])) & (df['FormularyTier'] == int(name.split()[1][2]))]['Rxs'].sum()
        elif name.startswith('Universal_Negative'):
            uni_neg_claims += df[(df['Universal Tier'] == int(name.split()[1][0])) & (df['FormularyTier'] == int(name.split()[1][2]))]['Rxs'].sum()
        elif name.startswith('Exclusive_Positive'):
            ex_pos_claims += df[(df['Exclusive Tier'] == int(name.split()[1][0])) & (df['FormularyTier'] == int(name.split()[1][2]))]['Rxs'].sum()
        elif name.startswith('Exclusive_Negative'):
            ex_neg_claims += df[(df['Exclusive Tier'] == int(name.split()[1][0])) & (df['FormularyTier'] == int(name.split()[1][2]))]['Rxs'].sum()

    # Calculate percentages
    uni_pos_pct = uni_pos_claims / total_claims if total_claims else 0
    uni_neg_pct = uni_neg_claims / total_claims if total_claims else 0
    ex_pos_pct = ex_pos_claims / total_claims if total_claims else 0
    ex_neg_pct = ex_neg_claims / total_claims if total_claims else 0
    exc_pct = exc_claims / total_claims if total_claims else 0

    summary_df = pd.DataFrame({
        'Formulary': ['Universal Positive',
                      'Universal Negative',
                      'Exclusive Positive',
                      'Exclusive Negative',
                      'Exclusions'],

        'Utilizers': [uni_pos_utilizers,
                      uni_neg_utilizers,
                      ex_pos_utilizers,
                      ex_neg_utilizers,
                      exc_utilizers],

        'Rxs': [uni_pos_claims,
                uni_neg_claims,
                ex_pos_claims,
                ex_neg_claims,
                exc_claims],

        '% of claims': [uni_pos_pct,
                        uni_neg_pct,
                        ex_pos_pct,
                        ex_neg_pct,
                        exc_pct],

        '': ['',
             '',
             '',
             '',
             ''],
        'Totals': [f'Members: {total_members}',
                   f'Claims: {total_claims}',
                   '',
                   '',
                   '']
    })

    summary_df.to_excel(writer, sheet_name='Summary', index=False)

    for sheet_name, value in tab_members.items():
        worksheet = writer.sheets[sheet_name]
        worksheet.write('F1', f'Total Members: {value}')

    # Network summary for non-excluded pharmacies
    network_df = df[df['pharmacy_is_excluded'].isna()]
    filter_phrases = ['CVS', 'Walgreens', 'Kroger', 'Walmart', 'Rite Aid', 'Optum', 'Express Scripts', 'DMR', 'Williams Bro', 'Publix']
    regex_pattern = '|'.join([f'\b{phrase}\b' for phrase in filter_phrases])
    network_df = network_df[~network_df['Pharmacy Name'].str.contains(regex_pattern, case=False, regex=True)]

    if 'PHARMACYNPI' in network_df.columns and 'NABP' in network_df.columns and 'Pharmacy Name' in network_df.columns:
        network_pivot = pd.pivot_table(
            network_df,
            values=['Rxs', 'MemberID'],
            index=['PHARMACYNPI', 'NABP', 'Pharmacy Name'],
            aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique}
        )
        network_pivot.to_excel(writer, sheet_name='Network')
    else:
        print("PHARMACYNPI, NABP, or Pharmacy Name column missing in the data dataframe.")

    # Reorder sheets so 'Summary' is right after 'Data'
    workbook = writer.book
    sheets = workbook.worksheets()
    sheet_names = [ws.get_name() for ws in sheets]

    # Move 'Summary' after 'Data'
    if 'Data' in sheet_names and 'Summary' in sheet_names:
        data_idx = sheet_names.index('Data')
        summary_idx = sheet_names.index('Summary')
        if summary_idx != data_idx + 1:
            summary_ws = sheets[summary_idx]
            sheets.pop(summary_idx)
            sheets.insert(data_idx + 1, summary_ws)

    # Save once at the end
    writer._save()

if __name__ == "__main__":
    process_data()
    print("Data processing complete")
