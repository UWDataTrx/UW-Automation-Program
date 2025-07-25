import pandas as pd
import customtkinter as ctk
from tkinter import filedialog
import tkinter as tk

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

    try:
        claims_data = pd.read_excel(claims_file_path,
                                    sheet_name='Claims Table',
                                    usecols=['NDC', 'MemberID', 'DATEFILLED', 'FormularyTier', 'Rxs', 'Logic'])
    except ValueError as e:
        print("Error:", e)
        print("Trying Sheet1")
        try:
            claims_data = pd.read_excel(claims_file_path, sheet_name='Sheet1',
                                        usecols=['NDC', 'MemberID', 'DATEFILLED', 'FormularyTier', 'Rxs', 'Logic'])
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
    merged1_data = pd.merge(u_data, merged_data, left_on='NDC', right_on='NDC', how='left')
    merged2_data = pd.merge(e_data, merged1_data, left_on='NDC', right_on='NDC', how='left')

    column_mapping = {
        'Tier_x': 'Exclusive Tier',
        'Tier_y': 'Universal Tier'
    }

    merged2_data.rename(columns=column_mapping, inplace=True)

    latest_date = merged2_data['DATEFILLED'].max()

    starting_point = latest_date - pd.DateOffset(months=6) + pd.DateOffset(days=1)
    recent_data = merged2_data[
        (merged2_data['DATEFILLED'] >= starting_point) & (merged2_data['DATEFILLED'] <= latest_date)]

    recent_data['Logic'] = pd.to_numeric(recent_data['Logic'], errors='coerce')

    filtered_data = recent_data[
        (recent_data['Logic'] >= 5) & (recent_data['Logic'] <= 10) & (recent_data['Maint Drug?'] == 'Y')]

    filtered1_data = filtered_data[~filtered_data['Product Name'].str.contains(r'\balbuterol\b', case=False)]

    data = filtered1_data[
        ~filtered1_data['Alternative'].str.contains('Covered|Use different NDC', case=False, regex=True)]

    output_file_path = 'LBL for Disruption.xlsx'

    writer = pd.ExcelWriter(output_file_path, engine='xlsxwriter')

    data.to_excel(writer, sheet_name='Data', index=False)

    writer.close()


if __name__ == "__main__":
    process_data()