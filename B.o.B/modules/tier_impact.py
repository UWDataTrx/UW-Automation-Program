import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
import pandas as pd
import os

# sys.stderr = open(os.devnull, 'w')

notes_window = None
root = ctk.CTk()
root.withdraw()

def choose_file():
    file_path = filedialog.askopenfilename()
    return file_path

def display_notes():
    global notes_window

    if notes_window is None or not notes_window.winfo_exists():
        notes_window = ctk.CTkToplevel()
        notes_window.title("Notes")
        notes_window.configure(fg_color='#333F48')

        notes_text = """
        There will be 4 filedialog windows that will show up in sequence.


        First window:
            Select the file with the necessary information used to start the disruption.
            This can be the repricing or a seperate file.

        Second Window:
            Select the Medi-Span file located in the Data Analyst folder.

        Third Window:
            Select the Universal Formulary file located in the Repricing Templates/Disruption folder

        Fourth Window:
            Select the Exclusive Formulary file located in the Repricing Templates/Disruption folder

        The output file will be located in the same directory as the program file.
        """

        notes_label = ctk.CTkLabel(notes_window, text=notes_text, justify=tk.LEFT, font=('Oswald', 16, 'bold'),
                                   fg_color="#333F48")
        notes_label.pack(padx=10, pady=10)

def process_data():
    display_notes()

    claims_file_path = choose_file()
    medi_file_path = choose_file()
    u_file_path = choose_file()
    e_file_path = choose_file()
    n_file_path = "C:\\Users\\MitchellFrederick\\OneDrive - True Rx Health Strategists\\TrueRx Health Strategists\\True Rx Management Services\\Data Analyst\\Repricing Templates\\Disruption\\Pharmacy Disruption\\Network List 23.xlsx"

    notes_window.destroy()

    try:
        claims_data = pd.read_excel(claims_file_path,
                                    sheet_name='Claims Table',
                                    usecols=['NDC', 'MemberID', 'DATEFILLED', 'FormularyTier', 'Rxs', 'Logic', 'PHARMACYNPI', 'NABP', 'Pharmacy Name'])
    except ValueError as e:
        print("Error:", e)
        print("Trying alternative sheet name...")
        try:
            claims_data = pd.read_excel(claims_file_path, sheet_name='Sheet1',
                                        usecols=['NDC', 'MemberID', 'DATEFILLED', 'FormularyTier', 'Rxs', 'Logic', 'PHARMACYNPI', 'NABP', 'Pharmacy Name'])
        except FileNotFoundError:
            print("Error: Claims file not found.")
            return
        except KeyError:
            print("Error: Required columns not found in the claims file.")
            return

    medi_data = pd.read_excel(medi_file_path)[['NDC', 'Maint Drug?', 'Product Name']]
    u_data = pd.read_excel(u_file_path, sheet_name='Universal NDC')[['NDC', 'Tier']]
    e_data = pd.read_excel(e_file_path, sheet_name='Alternatives NDC')[['NDC', 'Tier', 'Alternative']]
    
    merged_data = pd.merge(claims_data, medi_data, left_on='NDC', right_on='NDC', how='left')
    merged1_data = pd.merge(merged_data, u_data,  left_on='NDC', right_on='NDC', how='left')
    merged2_data = pd.merge(merged1_data, e_data,  left_on='NDC', right_on='NDC', how='left')
    
    # Load the network file
    network = pd.read_excel(n_file_path)[['pharmacy_npi', 'pharmacy_nabp', 'pharmacy_is_excluded']]

    # Ensure that pharmacy IDs are strings for consistent merging
    merged2_data['PHARMACYNPI'] = merged2_data['PHARMACYNPI'].astype(str).str.strip().replace('nan', None)
    merged2_data['NABP'] = merged2_data['NABP'].astype(str).str.strip().replace('nan', None)
    network['pharmacy_npi'] = network['pharmacy_npi'].astype(str).str.strip()
    network['pharmacy_nabp'] = network['pharmacy_nabp'].astype(str).str.strip()

    # Display columns for debugging
    print("Claims data columns after merging:", merged2_data.columns)
    print("Network data columns:", network.columns)

    if merged2_data['PHARMACYNPI'].notna().any():
        merged2_data = pd.merge(merged2_data, network, left_on='PHARMACYNPI', right_on='pharmacy_npi', how='left')
    else:
        merged2_data = pd.merge(merged2_data, network, left_on='NABP', right_on='pharmacy_nabp', how='left')

    column_mapping = {
        'Tier_y': 'Exclusive Tier',
        'Tier_x': 'Universal Tier'
    }

    merged2_data.rename(columns=column_mapping, inplace=True)
    merged2_data['DATEFILLED'] = pd.to_datetime(merged2_data['DATEFILLED'], errors='coerce')
    merged2_data = merged2_data.drop_duplicates()
    merged2_data.to_excel('Full Claims.xlsx')

    # Debugging information to verify merge
    print("Merged data columns:", merged2_data.columns)
    print("Sample merged data (first 5 rows):")
    print(merged2_data.head())

    latest_date = merged2_data['DATEFILLED'].max()

    starting_point = latest_date - pd.DateOffset(months=6) + pd.DateOffset(days=1)
    recent_data = merged2_data.loc[
        (merged2_data['DATEFILLED'] >= starting_point) & (merged2_data['DATEFILLED'] <= latest_date)]

    recent_data = recent_data.copy()
    recent_data['Logic'] = pd.to_numeric(recent_data['Logic'], errors='coerce')


    filtered_data = recent_data.loc[
        (recent_data['Logic'] >= 5) & (recent_data['Logic'] <= 10) & (recent_data['Maint Drug?'] == 'Y')]

    filtered2_data = filtered_data.loc[~filtered_data['Product Name'].str.contains(r'\balbuterol\b', case=False)]
    filtered3_data = filtered2_data.loc[~filtered2_data['Product Name'].str.contains(r'\bventolin\b', case=False)]
    filtered1_data = filtered3_data.loc[~filtered3_data['Product Name'].str.contains(r'\bepinephrine\b', case=False)]
    filtered1_data['Alternative'] = filtered1_data['Alternative'].astype(str)

    data = filtered1_data[
        ~filtered1_data['Alternative'].str.contains('Covered|Use different NDC', case=False, regex=True)]

    if 'pharmacy_id' not in data.columns:
        data['pharmacy_id'] = data.apply(lambda row: row['PHARMACYNPI'] if row['PHARMACYNPI'] != '' else row['NABP'], axis=1)

    uni_21_data = data[(data['Universal Tier'] == 1) & (data['FormularyTier'] == 2)]

    if uni_21_data.empty:
        uni_21_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    uni_21_pt = pd.pivot_table(uni_21_data,
                               values=['Rxs', 'MemberID'],
                               index=['Product Name'],
                               aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(uni_21_data) == 1 and uni_21_data['Rxs'].sum() == 0:
        uni_21_total_members = 0
    else:
        uni_21_total_members = uni_21_data['MemberID'].nunique()

    uni_31_data = data[(data['Universal Tier'] == 1) & (data['FormularyTier'] == 3)]
    if uni_31_data.empty:
        uni_31_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    uni_31_pt = pd.pivot_table(uni_31_data,
                               values=['Rxs', 'MemberID'],
                               index=['Product Name'],
                               aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(uni_31_data) == 1 and uni_31_data['Rxs'].sum() == 0:
        uni_31_total_members = 0
    else:
        uni_31_total_members = uni_31_data['MemberID'].nunique()

    uni_32_data = data[(data['Universal Tier'] == 2) & (data['FormularyTier'] == 3)]
    if uni_32_data.empty:
        uni_32_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    uni_32_pt = pd.pivot_table(uni_32_data,
                               values=['Rxs', 'MemberID'],
                               index=['Product Name'],
                               aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(uni_32_data) == 1 and uni_32_data['Rxs'].sum() == 0:
        uni_32_total_members = 0
    else:
        uni_32_total_members = uni_32_data['MemberID'].nunique()

    uni_12_data = data[(data['Universal Tier'] == 2) & (data['FormularyTier'] == 1)]
    if uni_12_data.empty:
        uni_12_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    uni_12_pt = pd.pivot_table(uni_12_data,
                               values=['Rxs', 'MemberID'],
                               index=['Product Name'],
                               aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})
    if len(uni_12_data) == 1 and uni_12_data['Rxs'].sum() == 0:
        uni_12_total_members = 0
    else:
        uni_12_total_members = uni_12_data['MemberID'].nunique()

    uni_13_data = data[(data['Universal Tier'] == 3) & (data['FormularyTier'] == 1)]
    if uni_13_data.empty:
        uni_13_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    uni_13_pt = pd.pivot_table(uni_13_data,
                               values=['Rxs', 'MemberID'],
                               index=['Product Name'],
                               aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(uni_13_data) == 1 and uni_13_data['Rxs'].sum() == 0:
        uni_13_total_members = 0
    else:
        uni_13_total_members = uni_13_data['MemberID'].nunique()

    uni_23_data = data[(data['Universal Tier'] == 3) & (data['FormularyTier'] == 2)]
    if uni_23_data.empty:
        uni_23_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    uni_23_pt = pd.pivot_table(uni_23_data,
                               values=['Rxs', 'MemberID'],
                               index=['Product Name'],
                               aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(uni_23_data) == 1 and uni_23_data['Rxs'].sum() == 0:
        uni_23_total_members = 0
    else:
        uni_23_total_members = uni_23_data['MemberID'].nunique()

    ex_21_data = data[(data['Exclusive Tier'] == 1) & (data['FormularyTier'] == 2)]
    if ex_21_data.empty:
        ex_21_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    ex_21_pt = pd.pivot_table(ex_21_data,
                              values=['Rxs', 'MemberID'],
                              index=['Product Name'],
                              aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(ex_21_data) == 1 and ex_21_data['Rxs'].sum() == 0:
        ex_21_total_members = 0
    else:
        ex_21_total_members = ex_21_data['MemberID'].nunique()

    ex_31_data = data[(data['Exclusive Tier'] == 1) & (data['FormularyTier'] == 3)]
    if ex_31_data.empty:
        ex_31_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    ex_31_pt = pd.pivot_table(ex_31_data,
                              values=['Rxs', 'MemberID'],
                              index=['Product Name'],
                              aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(ex_31_data) == 1 and ex_31_data['Rxs'].sum() == 0:
        ex_31_total_members = 0
    else:
        ex_31_total_members = ex_31_data['MemberID'].nunique()

    ex_32_data = data[(data['Exclusive Tier'] == 2) & (data['FormularyTier'] == 3)]
    if ex_32_data.empty:
        ex_32_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    ex_32_pt = pd.pivot_table(ex_32_data,
                              values=['Rxs', 'MemberID'],
                              index=['Product Name'],
                              aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(ex_32_data) == 1 and ex_32_data['Rxs'].sum() == 0:
        ex_32_total_members = 0
    else:
        ex_32_total_members = ex_32_data['MemberID'].nunique()

    ex_12_data = data[(data['Exclusive Tier'] == 2) & (data['FormularyTier'] == 1)]
    if ex_12_data.empty:
        ex_12_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    ex_12_pt = pd.pivot_table(ex_12_data,
                              values=['Rxs', 'MemberID'],
                              index=['Product Name'],
                              aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(ex_12_data) == 1 and ex_12_data['Rxs'].sum() == 0:
        ex_12_total_members = 0
    else:
        ex_12_total_members = ex_12_data['MemberID'].nunique()

    ex_13_data = data[(data['Exclusive Tier'] == 3) & (data['FormularyTier'] == 1)]
    if ex_13_data.empty:
        ex_13_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    ex_13_pt = pd.pivot_table(ex_13_data,
                              values=['Rxs', 'MemberID'],
                              index=['Product Name'],
                              aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(ex_13_data) == 1 and ex_13_data['Rxs'].sum() == 0:
        ex_13_total_members = 0
    else:
        ex_13_total_members = ex_13_data['MemberID'].nunique()

    ex_23_data = data[(data['Exclusive Tier'] == 3) & (data['FormularyTier'] == 2)]
    if ex_23_data.empty:
        ex_23_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    ex_23_pt = pd.pivot_table(ex_23_data,
                              values=['Rxs', 'MemberID'],
                              index=['Product Name'],
                              aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(ex_23_data) == 1 and ex_23_data['Rxs'].sum() == 0:
        ex_23_total_members = 0
    else:
        ex_23_total_members = ex_23_data['MemberID'].nunique()

    ex_ex_data = data[(data['Exclusive Tier'] == 'Nonformulary')]
    if ex_ex_data.empty:
        ex_ex_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    ex_ex_pt = pd.pivot_table(ex_ex_data,
                              values=['Rxs', 'MemberID'],
                              index=['Product Name','Alternative'],
                              aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(ex_ex_data) == 1 and ex_ex_data['Rxs'].sum() == 0:
        ex_ex_total_members = 0
    else:
        ex_ex_total_members = ex_ex_data['MemberID'].nunique()

    total_members = data['MemberID'].nunique()
    total_claims = data['Rxs'].sum()
    uni_pos_utilizers = uni_31_total_members + uni_21_total_members + uni_32_total_members
    uni_pos_claims = uni_21_data['Rxs'].sum() + uni_31_data['Rxs'].sum() + uni_32_data['Rxs'].sum()
    uni_pos_pct = uni_pos_claims / total_claims

    uni_neg_utilizers = uni_13_total_members + uni_12_total_members + uni_23_total_members
    uni_neg_claims = uni_12_data['Rxs'].sum() + uni_13_data['Rxs'].sum() + uni_23_data['Rxs'].sum()
    uni_neg_pct = uni_neg_claims / total_claims

    ex_pos_utilizers = ex_31_total_members + ex_21_total_members + ex_32_total_members
    ex_pos_claims = ex_21_data['Rxs'].sum() + ex_31_data['Rxs'].sum() + ex_32_data['Rxs'].sum()
    ex_pos_pct = ex_pos_claims / total_claims

    ex_neg_utilizers = ex_13_total_members + ex_12_total_members + ex_23_total_members
    ex_neg_claims = ex_12_data['Rxs'].sum() + ex_13_data['Rxs'].sum() + ex_23_data['Rxs'].sum()
    ex_neg_pct = ex_neg_claims / total_claims

    exc_utilizers = ex_ex_total_members
    exc_claims = ex_ex_data['Rxs'].sum()
    exc_pct = exc_claims / total_claims


    output_file_path = 'output_data.xlsx'
    writer = pd.ExcelWriter(output_file_path, engine='xlsxwriter')

    data.to_excel(writer, sheet_name='Data', index=False)

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

    uni_21_pt.to_excel(writer, sheet_name='Universal_Positive 2-1')
    uni_31_pt.to_excel(writer, sheet_name='Universal_Positive 3-1')
    uni_32_pt.to_excel(writer, sheet_name='Universal_Positive 3-2')
    uni_12_pt.to_excel(writer, sheet_name='Universal_Negative 1-2')
    uni_13_pt.to_excel(writer, sheet_name='Universal_Negative 1-3')
    uni_23_pt.to_excel(writer, sheet_name='Universal_Negative 2-3')
    ex_21_pt.to_excel(writer, sheet_name='Exclusive_Positive 2-1')
    ex_31_pt.to_excel(writer, sheet_name='Exclusive_Positive 3-1')
    ex_32_pt.to_excel(writer, sheet_name='Exclusive_Positive 3-2')
    ex_12_pt.to_excel(writer, sheet_name='Exclusive_Negative 1-2')
    ex_13_pt.to_excel(writer, sheet_name='Exclusive_Negative 1-3')
    ex_23_pt.to_excel(writer, sheet_name='Exclusive_Negative 2-3')
    ex_ex_pt.to_excel(writer, sheet_name='Exclusions')

    tabs_values = {
        'Universal_Positive 2-1': f'Total Members: {uni_21_total_members}',
        'Universal_Positive 3-1': f'Total Members: {uni_31_total_members}',
        'Universal_Positive 3-2': f'Total Members: {uni_32_total_members}',
        'Universal_Negative 1-2': f'Total Members: {uni_12_total_members}',
        'Universal_Negative 1-3': f'Total Members: {uni_13_total_members}',
        'Universal_Negative 2-3': f'Total Members: {uni_23_total_members}',
        'Exclusive_Positive 2-1': f'Total Members: {ex_21_total_members}',
        'Exclusive_Positive 3-1': f'Total Members: {ex_31_total_members}',
        'Exclusive_Positive 3-2': f'Total Members: {ex_32_total_members}',
        'Exclusive_Negative 1-2': f'Total Members: {ex_12_total_members}',
        'Exclusive_Negative 1-3': f'Total Members: {ex_13_total_members}',
        'Exclusive_Negative 2-3': f'Total Members: {ex_23_total_members}',
        'Exclusions': f'Total Members: {ex_ex_total_members}'
    }

    for sheet_name, value in tabs_values.items():
        worksheet = writer.sheets[sheet_name]
        worksheet.write('F1', value)

    network_df = data[data['pharmacy_is_excluded'].isna()]
    filter_phrases = ['CVS', 'Walgreens', 'Kroger', 'Walmart', 'Rite Aid', 'Optum', 'Express Scripts', 'DMR', 'Williams Bro', 'Publix']
    regex_pattern = '|'.join([f'\\b{phrase}\\b' for phrase in filter_phrases])
    network_df = network_df[~network_df['Pharmacy Name'].str.contains(regex_pattern, case=False, regex=True)]

    if 'pharmacy_id' in network_df.columns and 'Pharmacy Name' in network_df.columns:
        network_pivot = pd.pivot_table(network_df,
                                    values=['Rxs', 'MemberID'],
                                    index=['pharmacy_id', 'Pharmacy Name'],
                                    aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})
        network_pivot.to_excel(writer, sheet_name='Network')
    else:
        print("pharmacy_id or Pharmacy Name column missing in the data dataframe.")

    writer._save()

if __name__ == "__main__":
    process_data()
