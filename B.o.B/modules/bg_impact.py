import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
import pandas as pd
import sys
import os

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
            This can be the repricing or a separate file.

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
        notes_label.pack(padx=50, pady=50)


def process_data():
    display_notes()

claims_file_path = choose_file()
medi_file_path = choose_file()
u_file_path = choose_file()
e_file_path = choose_file()
n_file_path = "%OneDrive%/True Community - Data Analyst/Repricing Templates/Disruption/Pharmacy Disruption/Rx Sense Pharmacy Network 7.25.xlsx"
if notes_window is not None and notes_window.winfo_exists():
    notes_window.destroy()

try:
    claims_data = pd.read_excel(claims_file_path,
                                sheet_name='Claims Table',
                                usecols=['SOURCERECORDID', 'NDC', 'MemberID', 'DATEFILLED', 'FormularyTier', 'Rxs', 'Logic', 'PHARMACYNPI', 'NABP', 'Pharmacy Name'])
except ValueError as e:
    print("Error:", e)
    print("Trying Sheet1")
    try:
        claims_data = pd.read_excel(claims_file_path, sheet_name='Sheet1',
                                    usecols=['SOURCERECORDID', 'NDC', 'MemberID', 'PHARMACYNPI', 'NABP', 'DATEFILLED', 'FormularyTier', 'Rxs', 'Logic', 'PHARMACYNPI', 'NABP', 'Pharmacy Name'])
    except FileNotFoundError:
        print("Error: Claims file not found.")
        sys.exit()
    except KeyError:
        print("Error: Required columns not found in the claims file.")
        sys.exit()

medi_data = pd.read_excel(medi_file_path)[['NDC', 'Maint Drug?', 'Product Name']]
u_data = pd.read_excel(u_file_path, sheet_name='Universal NDC')[['NDC', 'Tier']]
e_data = pd.read_excel(e_file_path, sheet_name='Alternatives NDC')[['NDC', 'Tier', 'Alternative']]
network = pd.read_excel(n_file_path)[['pharmacy_npi', 'pharmacy_nabp', 'pharmacy_is_excluded']]

    merged_data = pd.merge(claims_data, medi_data, left_on='NDC', right_on='NDC', how='left')
    merged1_data = pd.merge(merged_data, u_data, left_on='NDC', right_on='NDC', how='left')
    merged2_data = pd.merge(merged1_data, e_data, left_on='NDC', right_on='NDC', how='left')

    def custom_merge(left, right):
        left = left.copy()
        left['pharmacy_id'] = left.apply(lambda row: str(row['PHARMACYNPI']) if pd.notna(row['PHARMACYNPI']) else str(row['NABP']), axis=1)
        right['pharmacy_id'] = right.apply(lambda row: str(row['pharmacy_npi']) if pd.notna(row['pharmacy_npi']) else str(row['pharmacy_nabp']), axis=1)
        merged = pd.merge(left, right[['pharmacy_id', 'pharmacy_is_excluded']], on='pharmacy_id', how='left')
        return merged

    try:
        merged2_data = custom_merge(merged2_data, network)
    except Exception as e:
        print("Error during merging:", e)

    column_mapping = {
        'Tier_y': 'Exclusive Tier',
        'Tier_x': 'Universal Tier'
    }

    merged2_data.rename(columns=column_mapping, inplace=True)

    merged2_data['DATEFILLED'] = pd.to_datetime(merged2_data['DATEFILLED'], errors='coerce')
    merged2_data = merged2_data.drop_duplicates()
    merged2_data.to_excel('Full Claims.xlsx')

    latest_date = merged2_data['DATEFILLED'].max()

    starting_point = latest_date - pd.DateOffset(months=6) + pd.DateOffset(days=1)
    recent_data = merged2_data.loc[
        (merged2_data['DATEFILLED'] >= starting_point) & (merged2_data['DATEFILLED'] <= latest_date)]

    recent_data['Logic'] = pd.to_numeric(recent_data['Logic'], errors='coerce')

    filtered_data = recent_data.loc[
        (recent_data['Logic'] >= 5) & (recent_data['Logic'] <= 10) & (recent_data['Maint Drug?'] == 'Y')]

    filtered2_data = filtered_data.loc[~filtered_data['Product Name'].str.contains(r'\balbuterol\b', case=False)]
    filtered3_data = filtered2_data.loc[~filtered2_data['Product Name'].str.contains(r'\bventolin\b', case=False)]
    filtered1_data = filtered3_data.loc[~filtered3_data['Product Name'].str.contains(r'\bepinephrine\b', case=False)]
    filtered1_data['Alternative'] = filtered1_data['Alternative'].astype(str)

    data = filtered1_data[
        ~filtered1_data['Alternative'].str.contains('Covered|Use different NDC', case=False, regex=True)]
    data['FormularyTier'] = data['FormularyTier'].str.strip()

    if 'pharmacy_id' not in data.columns:
        data['pharmacy_id'] = data.apply(lambda row: str(row['PHARMACYNPI']) if pd.notna(row['PHARMACYNPI']) else str(row['NABP']), axis=1)

    uni_pos_data = data[(data['Universal Tier'] == 1) & (data['FormularyTier'].str.upper().isin(['B', 'BRAND']))]
    if uni_pos_data.empty:
        uni_pos_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    uni_pos_pt = pd.pivot_table(uni_pos_data,
                                values=['Rxs', 'MemberID'],
                                index='Product Name',
                                aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})
    if len(uni_pos_data) == 1 and uni_pos_data['Rxs'].sum() == 0:
        uni_pos_total_members = 0
    else:
        uni_pos_total_members = uni_pos_data['MemberID'].nunique()

    uni_neg_data = data[((data['Universal Tier'] == 2) | (data['Universal Tier'] == 3)) & (data['FormularyTier'].str.upper().isin(['G', "GENERIC"]))]
    if uni_neg_data.empty:
        uni_neg_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    uni_neg_pt = pd.pivot_table(uni_neg_data,
                                values=['Rxs', 'MemberID'],
                                index='Product Name',
                                aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(uni_neg_data) == 1 and uni_neg_data['Rxs'].sum() == 0:
        uni_neg_total_members = 0
    else:
        uni_neg_total_members = uni_neg_data['MemberID'].nunique()

    ex_pos_data = data[(data['Exclusive Tier'] == 1) & (data['FormularyTier'].str.upper().isin(['B', 'BRAND']))]
    if ex_pos_data.empty:
        ex_pos_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    ex_pos_pt = pd.pivot_table(ex_pos_data,
                               values=['Rxs', 'MemberID'],
                               index='Product Name',
                               aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(ex_pos_data) == 1 and ex_pos_data['Rxs'].sum() == 0:
        ex_pos_total_members = 0
    else:
        ex_pos_total_members = ex_pos_data['MemberID'].nunique()

    ex_neg_data = data[((data['Exclusive Tier'] == 2) | (data['Exclusive Tier'] == 3)) & (
        data['FormularyTier'].str.upper().isin(['G', "GENERIC"]))]
    if ex_neg_data.empty:
        ex_neg_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    ex_neg_pt = pd.pivot_table(ex_neg_data,
                               values=['Rxs', 'MemberID'],
                               index='Product Name',
                               aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(ex_neg_data) == 1 and ex_neg_data['Rxs'].sum() == 0:
        ex_neg_total_members = 0
    else:
        ex_neg_total_members = ex_neg_data['MemberID'].nunique()

    ex_ex_data = data[(data['Exclusive Tier'] == 'Nonformulary')]
    if ex_ex_data.empty:
        ex_ex_data = pd.DataFrame([[0] * len(data.columns)], columns=data.columns)

    ex_ex_pt = pd.pivot_table(ex_ex_data,
                              values=['Rxs', 'MemberID'],
                              index=['Product Name', 'Alternative'],
                              aggfunc={'Rxs': 'sum', 'MemberID': pd.Series.nunique})

    if len(ex_ex_data) == 1 and ex_ex_data['Rxs'].sum() == 0:
        ex_ex_total_members = 0
    else:
        ex_ex_total_members = ex_ex_data['MemberID'].nunique()

    total_members = data['MemberID'].nunique()
    total_claims = data['Rxs'].sum()
    uni_pos_pct = uni_pos_pt['Rxs'].sum() / total_claims
    uni_neg_pct = uni_neg_pt['Rxs'].sum() / total_claims
    ex_pos_pct = ex_pos_pt['Rxs'].sum() / total_claims
    ex_neg_pct = ex_neg_pt['Rxs'].sum() / total_claims
    ex_ex_pct = ex_ex_pt['Rxs'].sum() / total_claims

    output_file_path = 'output1_data.xlsx'

    writer = pd.ExcelWriter(output_file_path, engine='xlsxwriter')

    data.to_excel(writer, sheet_name='Data', index=False)

    summary_df = pd.DataFrame({
        'Formulary': ['Universal Positive',
                      'Universal Negative',
                      'Exclusive Positive',
                      'Exclusive Negative',
                      'Exclusions'],

        'Utilizers': [uni_pos_total_members,
                      uni_neg_total_members,
                      ex_pos_total_members,
                      ex_neg_total_members,
                      ex_ex_total_members],

        'Rxs': [uni_pos_data['Rxs'].sum(),
                uni_neg_data['Rxs'].sum(),
                ex_pos_data['Rxs'].sum(),
                ex_neg_data['Rxs'].sum(),
                ex_ex_data['Rxs'].sum()],

        '% of claims': [uni_pos_pct,
                        uni_neg_pct,
                        ex_pos_pct,
                        ex_neg_pct,
                        ex_ex_pct],

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

    uni_pos_pt.to_excel(writer, sheet_name='Universal_Positive')
    uni_neg_pt.to_excel(writer, sheet_name='Universal_Negative')
    ex_pos_pt.to_excel(writer, sheet_name='Exclusive_Positive')
    ex_neg_pt.to_excel(writer, sheet_name='Exclusive_Negative')
    ex_ex_pt.to_excel(writer, sheet_name='Exclusions')

    tabs_values = {
        'Universal_Positive': f'Total Members: {uni_pos_total_members}',
        'Universal_Negative': f'Total Members: {uni_neg_total_members}',
        'Exclusive_Positive': f'Total Members: {ex_pos_total_members}',
        'Exclusive_Negative': f'Total Members: {ex_neg_total_members}',
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

    writer.close()


if __name__ == "__main__":
    process_data()
