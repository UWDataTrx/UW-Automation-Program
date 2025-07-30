import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import customtkinter as ctk
import pandas as pd
import pyperclip
import statistics
import subprocess
import re
from config.config_loader import ConfigLoader

sys.stderr = open(os.devnull, 'w')

def read_drug_data(file_path):
    try:
        needed_cols = [
            "drug_name", "strength", "quantity",
            "affiliate_ingred_cost", "affiliate_disp_fee", "days_supply"
        ]
        data = pd.read_parquet(file_path, columns=needed_cols)
        data["gross_cost"] = data["affiliate_ingred_cost"] + data["affiliate_disp_fee"]
        data["30/90"] = 30
        data.loc[data["days_supply"] < 84, "30/90"] = 30
        data.loc[data["days_supply"] >= 84, "30/90"] = 90
        # Preprocess for faster search
        data["drug_name_lower"] = data["drug_name"].str.lower().astype("category")
        return data
    except Exception as e:
        messagebox.showerror("Error Reading File", f"Error reading Parquet file: {e}")
        return None

def mode_func(x):
    try:
        return statistics.mode(x)
    except statistics.StatisticsError:
        return None

def display_drug_details(drug_names, data, show_strength=True, show_quantity=True, dosing=None, quantity=None, supply_duration=None):
    # Combine all search terms into a single regex for vectorized search
    search_terms = "|".join([re.escape(name.strip().lower()) for name in drug_names if name.strip()])
    filtered = data[data['drug_name_lower'].str.contains(search_terms, na=False, regex=True)]

    if dosing:
        filtered = filtered[filtered['strength'].str.lower().str.contains(dosing.strip().lower(), na=False)]
    if quantity:
        filtered = filtered[filtered['quantity'].astype(str).str.lower().str.contains(quantity.strip().lower(), na=False)]
    if supply_duration:
        filtered = filtered[filtered['30/90'].isin(supply_duration)]

    if filtered.empty:
        return pd.DataFrame(columns=["drug_name", "quantity", "30/90", "strength", "mean_cost", "mode_cost"])

    grouped = filtered.groupby(["drug_name", "quantity", "30/90", "strength"]).agg(
        mean_cost=('gross_cost', 'mean'),
        mode_cost=('gross_cost', mode_func)
    ).reset_index()

    grouped['mean_cost'] = grouped['mean_cost'].apply(lambda x: f"${x:,.2f}")
    grouped['mode_cost'] = grouped['mode_cost'].apply(lambda x: f"${x:,.2f}" if x is not None else "N/A")

    # Only keep the first match for each searched drug name
    result = []
    for name in drug_names:
        name = name.strip().lower()
        match = grouped[grouped['drug_name'].str.lower() == name]
        if not match.empty:
            result.append(match.iloc[0])
    if result:
        return pd.DataFrame(result)
    else:
        return pd.DataFrame(columns=["drug_name", "quantity", "30/90", "strength", "mean_cost", "mode_cost"])

def rebate_clicked():
    subprocess.Popen(["python", "rebate.py"])

def on_search():
    drug_names = entry_drug.get()
    if not drug_names.strip():
        messagebox.showwarning("Input Required", "Please enter at least one drug name.")
        return
    drug_names = [name.strip() for name in drug_names.split(',') if name.strip()]
    show_strength = strength_var.get()
    show_quantity = quantity_var.get()
    dosing = entry_dosing.get()
    quantity = entry_quantity.get()
    supply_duration = []
    if supply_var_30.get():
        supply_duration.append(30)
    if supply_var_90.get():
        supply_duration.append(90)
    result_df = display_drug_details(drug_names, data, show_strength, show_quantity, dosing, quantity, supply_duration)
    display_results(result_df)

def display_results(df):
    for i in treeview.get_children():
        treeview.delete(i)
    if df.empty:
        messagebox.showinfo("No Results", "No matching drugs found for your search.")
        return
    current_tag = 'oddrow'
    for index, row in df.iterrows():
        current_tag = 'evenrow' if current_tag == 'oddrow' else 'oddrow'
        treeview.insert("", "end", values=row.tolist(), tags=(current_tag,))

def copy_to_clipboard():
    selected_items = treeview.selection()
    if selected_items:
        selected_rows = [treeview.item(item, "values") for item in selected_items]
        tab_separated_data = "\n".join(["\t".join(map(str, row)) for row in selected_rows])
        pyperclip.copy(tab_separated_data)
    else:
        print("No rows selected.")

def export_to_parquet():
    selected_items = treeview.selection()
    if selected_items:
        selected_rows = [treeview.item(item, "values") for item in selected_items]
        df = pd.DataFrame(selected_rows, columns=columns)
        try:
            df.to_parquet("selected_data.parquet", index=False)
            messagebox.showinfo("Process Finished", "Selected rows have been saved as selected_data.parquet")
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not export to Parquet: {e}")
    else:
        messagebox.showwarning("No Selection", "No rows selected.")

root = ctk.CTk()
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

x = (screen_width - 1250) // 2
y = (screen_height - 850) // 2

root.geometry("+{}+{}".format(x, y))
root.geometry('1250x850')
root.title("B.o.B Drug Lookup")
root.configure(fg_color="#333F48")

# Use config loader for file path
try:
    file_paths = ConfigLoader.load_file_paths()
    file_path = file_paths.get("results_parquet", "")
except Exception as e:
    messagebox.showerror("Config Error", f"Could not load file_paths.json: {e}")
    file_path = ""

data = read_drug_data(file_path)
if data is None or data.empty:
    messagebox.showerror("Data Load Error", f"Failed to load data from {file_path} or file is empty.")
else:
    if "drug_name" in data.columns:
        print("First 10 drug names in data:")
        print(data["drug_name"].drop_duplicates().head(10).to_list())
    else:
        print(f"Columns in {file_path}: {data.columns.tolist()}")

frame1 = ctk.CTkFrame(root, fg_color="#333F48")
frame1.pack(padx=10, pady=10)

# Define columns for the treeview
columns = ["drug_name", "quantity", "30/90", "strength", "mean_cost", "mode_cost"]

# Add a frame for the Treeview and scrollbar
tree_frame = ctk.CTkFrame(root, fg_color="#333F48")
tree_frame.pack(padx=10, pady=10, fill="both", expand=True)

treeview = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
for col in columns:
    display_name = "Average Cost" if col == "mean_cost" else col.replace("_", " ").title()
    treeview.heading(col, text=display_name)
    treeview.column(col, width=180, anchor="center")
treeview.pack(side="left", fill="both", expand=True)

# Add vertical scrollbar
scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=treeview.yview)
scrollbar.pack(side="right", fill="y")
treeview.configure(yscrollcommand=scrollbar.set)

# Tag configuration for alternating row colors
treeview.tag_configure('oddrow', background='#3A4650', foreground='white')
treeview.tag_configure('evenrow', background='#333F48', foreground='white')

label_drug = ctk.CTkLabel(frame1, text="Enter Drug Names (comma-separated)", font=('oswald', 24, 'bold'))
label_drug.grid(row=1, column=1, columnspan=4, padx=10, pady=30)

entry_drug = ctk.CTkEntry(frame1, width=600, font=(None, 16))
entry_drug.grid(row=2, column=1, columnspan=3, padx=10, pady=10)

label_dosing = ctk.CTkLabel(frame1, text="Enter Dosing", font=('oswald', 16, 'bold'))
label_dosing.grid(row=4, column=3, padx=10, pady=10)
entry_dosing = ctk.CTkEntry(frame1, width=75, font=(None, 16))
entry_dosing.grid(row=5, column=3, padx=10, pady=10)

label_quantity = ctk.CTkLabel(frame1, text="Enter Quantity", font=('oswald', 16, 'bold'))
label_quantity.grid(row=4, column=1, padx=10, pady=10)
entry_quantity = ctk.CTkEntry(frame1, width=75, font=(None, 16))
entry_quantity.grid(row=5, column=1, padx=10, pady=10)

strength_var = tk.BooleanVar(value=False)
check_strength = ctk.CTkCheckBox(frame1, text="Show Dosing", variable=strength_var, font=('oswald', 16, 'bold'))
check_strength.grid(row=3, column=3, padx=10, pady=10)
quantity_var = tk.BooleanVar(value=False)
check_quantity = ctk.CTkCheckBox(frame1, text="Show Quantity", variable=quantity_var, font=('oswald', 16, 'bold'))
check_quantity.grid(row=3, column=1, padx=10, pady=10)

supply_var_30 = tk.BooleanVar(value=True)
check_30_day = ctk.CTkCheckBox(frame1, text="30 Days", variable=supply_var_30, font=('oswald', 16, 'bold'))
check_30_day.grid(row=3, column=4, padx=10, pady=10)
supply_var_90 = tk.BooleanVar(value=False)
check_90_day = ctk.CTkCheckBox(frame1, text="90 Days", variable=supply_var_90, font=('oswald', 16, 'bold'))
check_90_day.grid(row=3, column=5, padx=10, pady=10)

button_search = ctk.CTkButton(frame1, text="Search", command=on_search, font=('oswald', 16, 'bold'))
button_search.grid(row=6, column=1, padx=10, pady=10)

button_copy = ctk.CTkButton(frame1, text="Copy to Clipboard", command=copy_to_clipboard, font=('oswald', 16, 'bold'))
button_copy.grid(row=6, column=2, padx=10, pady=10)

button_export = ctk.CTkButton(frame1, text="Export to Parquet", command=export_to_parquet, font=('oswald', 16, 'bold'))
button_export.grid(row=6, column=3, padx=10, pady=10)

button_rebate = ctk.CTkButton(frame1, text="Rebate Lookup", command=rebate_clicked, font=('oswald', 16, 'bold'))
button_rebate.grid(row=6, column=4, padx=10, pady=10)

root.bind("<Return>", lambda event: on_search())

style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview",
    background="#333F48",        # dark background
    foreground="white",          # text color
    fieldbackground="#333F48",   # background for empty space
    rowheight=30,
    bordercolor="#333F48"
)
style.configure("Treeview.Heading",
    background="#333F48",
    foreground="white",
    font=('oswald', 14, 'bold')
)
style.map('Treeview', background=[('selected', '#607D8B')])

root.mainloop()
print('Done')