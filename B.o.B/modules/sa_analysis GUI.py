import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import customtkinter as ctk
import pandas as pd
import pyperclip
import statistics
import subprocess
import os
import sys

sys.stderr = open(os.devnull, "w")


def read_drug_data(file_path):
    if not os.path.exists(file_path):
        messagebox.showerror(
            "File Not Found", f"The file '{file_path}' does not exist."
        )
        return None
    try:
        # Read Parquet if file ends with .parquet, else CSV
        if file_path.lower().endswith(".parquet"):
            data = pd.read_parquet(file_path)
        else:
            data = pd.read_csv(file_path)
        # Check for required columns
        required_cols = [
            "drug_name",
            "strength",
            "quantity",
            "affiliate_ingred_cost",
            "affiliate_disp_fee",
            "days_supply",
        ]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            messagebox.showerror(
                "Missing Columns",
                f"The following required columns are missing: {', '.join(missing_cols)}",
            )
            return None
        data["gross_cost"] = data["affiliate_ingred_cost"] + data["affiliate_disp_fee"]
        data["30/90"] = 30
        data.loc[data["days_supply"] < 84, "30/90"] = 30
        data.loc[data["days_supply"] >= 84, "30/90"] = 90
        return data
    except Exception as e:
        messagebox.showerror("Error Reading File", f"Error reading file: {e}")
        return None


def mode_func(x):
    try:
        return statistics.mode(x)
    except statistics.StatisticsError:
        return None


def display_drug_details(
    drug_names,
    data,
    show_strength=True,
    show_quantity=True,
    dosing=None,
    quantity=None,
    supply_duration=None,
):
    results = []
    for drug in drug_names:
        # Defensive: skip empty drug names
        if not drug:
            continue
        # Case-insensitive, ignore leading/trailing spaces
        drug_info = data[
            data["drug_name"].str.lower().str.contains(drug.strip().lower(), na=False)
        ]
        if not drug_info.empty:
            if show_strength:
                drug_info.loc[:, "strength"] = (
                    drug_info["strength"].fillna("").astype(str)
                )
            else:
                drug_info["strength"] = ""

            if show_quantity:
                drug_info["quantity"] = drug_info["quantity"].astype(str)
                drug_info.loc[:, "quantity"] = drug_info["quantity"].fillna("")
            else:
                drug_info["quantity"] = ""

            if dosing:
                drug_info = drug_info[
                    drug_info["strength"]
                    .str.lower()
                    .str.contains(dosing.strip().lower(), na=False)
                ]
            if quantity:
                drug_info = drug_info[
                    drug_info["quantity"]
                    .str.lower()
                    .str.contains(quantity.strip().lower(), na=False)
                ]
            if supply_duration:
                drug_info = drug_info[drug_info["30/90"].isin(supply_duration)]

            if not drug_info.empty:
                drug_pt = (
                    drug_info.groupby(["drug_name", "quantity", "30/90", "strength"])
                    .agg({"gross_cost": ["mean", mode_func]})
                    .reset_index()
                )
                drug_pt.columns = [
                    "drug_name",
                    "30/90",
                    "strength",
                    "quantity",
                    "mean_cost",
                    "mode_cost",
                ]
                drug_pt["mean_cost"] = drug_pt["mean_cost"].apply(
                    lambda x: f"${x:,.2f}"
                )
                drug_pt["mode_cost"] = drug_pt["mode_cost"].apply(
                    lambda x: f"${x:,.2f}" if x is not None else "N/A"
                )
                results.append(drug_pt)
            else:
                # No results after filtering
                results.append(
                    pd.DataFrame(
                        columns=[
                            "drug_name",
                            "quantity",
                            "30/90",
                            "strength",
                            "mean_cost",
                            "mode_cost",
                        ]
                    )
                )
        else:
            results.append(
                pd.DataFrame(
                    columns=[
                        "drug_name",
                        "quantity",
                        "30/90",
                        "strength",
                        "mean_cost",
                        "mode_cost",
                    ]
                )
            )
    if results:
        return pd.concat(results)
    else:
        return pd.DataFrame(
            columns=[
                "drug_name",
                "quantity",
                "30/90",
                "strength",
                "mean_cost",
                "mode_cost",
            ]
        )


def rebate_clicked():
    subprocess.Popen(["python", "rebate.py"])


def on_search():
    drug_names = entry_drug.get()
    if not drug_names.strip():
        messagebox.showwarning("Input Required", "Please enter at least one drug name.")
        return
    drug_names = [name.strip() for name in drug_names.split(",") if name.strip()]
    show_strength = strength_var.get()
    show_quantity = quantity_var.get()
    dosing = entry_dosing.get()
    quantity = entry_quantity.get()
    supply_duration = []
    if supply_var_30.get():
        supply_duration.append(30)
    if supply_var_90.get():
        supply_duration.append(90)
    result_df = display_drug_details(
        drug_names,
        data,
        show_strength,
        show_quantity,
        dosing,
        quantity,
        supply_duration,
    )
    display_results(result_df)


def display_results(df):
    for i in treeview.get_children():
        treeview.delete(i)

    if df.empty:
        messagebox.showinfo("No Results", "No matching drugs found for your search.")
        return

    current_tag = "oddrow"
    for index, row in df.iterrows():
        if current_tag == "oddrow":
            current_tag = "evenrow"
        else:
            current_tag = "oddrow"
        treeview.insert("", "end", values=row.tolist(), tags=(current_tag,))


def copy_to_clipboard():
    selected_items = treeview.selection()
    if selected_items:
        selected_rows = [treeview.item(item, "values") for item in selected_items]
        tab_separated_data = "\n".join(
            ["\t".join(map(str, row)) for row in selected_rows]
        )
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
            messagebox.showinfo(
                "Process Finished",
                "Selected rows have been saved as selected_data.parquet",
            )
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
root.geometry("1250x850")
root.title("B.o.B Drug Lookup")
root.configure(fg_color="#333F48")


# Change this to your .parquet file
file_path = r"C:\Users\DamionMorrison\OneDrive - True Rx Health Strategists\True Community - Data Analyst\UW Python Program\UW-Automation-Program\B.o.B\modules\results.parquet"
data = read_drug_data(file_path)
if data is None or data.empty:
    messagebox.showerror(
        "Data Load Error", f"Failed to load data from {file_path} or file is empty."
    )
else:
    if "drug_name" in data.columns:
        print("First 10 drug names in data:")
        print(data["drug_name"].drop_duplicates().head(10).to_list())
    else:
        print(f"Columns in {file_path}: {data.columns.tolist()}")

frame1 = ctk.CTkFrame(root, fg_color="#333F48")
frame1.pack(padx=10, pady=10)

label_drug = ctk.CTkLabel(
    frame1, text="Enter Drug Names (comma-separated)", font=("oswald", 24, "bold")
)
label_drug.grid(row=1, column=1, columnspan=4, padx=10, pady=30)

entry_drug = ctk.CTkEntry(frame1, width=600, font=(None, 16))
entry_drug.grid(row=2, column=1, columnspan=3, padx=10, pady=10)

label_dosing = ctk.CTkLabel(frame1, text="Enter Dosing", font=("oswald", 16, "bold"))
label_dosing.grid(row=4, column=3, padx=10, pady=10)
entry_dosing = ctk.CTkEntry(frame1, width=75, font=(None, 16))
entry_dosing.grid(row=5, column=3, padx=10, pady=10)

label_quantity = ctk.CTkLabel(
    frame1, text="Enter Quantity", font=("oswald", 16, "bold")
)
label_quantity.grid(row=4, column=1, padx=10, pady=10)
entry_quantity = ctk.CTkEntry(frame1, width=75, font=(None, 16))
entry_quantity.grid(row=5, column=1, padx=10, pady=10)

strength_var = tk.BooleanVar(value=False)
check_strength = ctk.CTkCheckBox(
    frame1, text="Show Dosing", variable=strength_var, font=("oswald", 16, "bold")
)
check_strength.grid(row=3, column=3, padx=10, pady=10)
quantity_var = tk.BooleanVar(value=False)
check_quantity = ctk.CTkCheckBox(
    frame1, text="Show Quantity", variable=quantity_var, font=("oswald", 16, "bold")
)
check_quantity.grid(row=3, column=1, padx=10, pady=10)

supply_var_30 = tk.BooleanVar(value=True)
check_30_day = ctk.CTkCheckBox(
    frame1, text="30 Days", variable=supply_var_30, font=("oswald", 16, "bold")
)
check_30_day.grid(row=3, column=4, padx=10, pady=10)
supply_var_90 = tk.BooleanVar(value=False)
check_90_day = ctk.CTkCheckBox(
    frame1, text="90 Days", variable=supply_var_90, font=("oswald", 16, "bold")
)
check_90_day.grid(row=4, column=4, padx=10, pady=10)

button_search = ctk.CTkButton(
    frame1, text="Search", command=on_search, font=("Oswald", 16, "bold")
)
button_search.grid(row=2, column=4, columnspan=2, padx=5, pady=5)

button_copy = ctk.CTkButton(
    root,
    text="Copy Selected Rows",
    command=copy_to_clipboard,
    font=("Oswald", 16, "bold"),
)
button_copy.pack(pady=10)

button_rebate = ctk.CTkButton(
    root,
    text="Savings Analysis Lookup",
    command=rebate_clicked,
    font=("Oswald", 16, "bold"),
)
button_rebate.pack(side=ctk.BOTTOM, pady=10)


button_export_csv = ctk.CTkButton(
    root, text="Export Selected", command=export_to_parquet, font=("Oswald", 16, "bold")
)
button_export_csv.pack(side=ctk.BOTTOM, pady=10)


style = ttk.Style()
style.theme_use("clam")
style.configure(
    "Treeview.Heading",
    font=("Oswald", 14, "bold"),
    foreground="#333F48",
    background="dark grey",
    relief="flat",
)
style.configure(
    "Treeview",
    font=("Oswald", 14),
    rowheight=25,
    background="#333F48",
    fieldbackground="#333F48",
    bordercolor="#333F48",
)


columns = [
    "Drug Name",
    "Quantity",
    "30/90 Day Supply",
    "Dosing",
    "Average Cost",
    "Mode Cost",
]
# Use 'extended' to allow multiple row selection for copy/export
treeview = ttk.Treeview(root, columns=columns, show="headings", selectmode="extended")
for col in columns:
    treeview.heading(col, text=col)
    if col != "Drug Name":
        treeview.column(col, anchor="center")
treeview.pack(side=ctk.LEFT, padx=5, pady=10, fill="both", expand=True)


# Remove custom select function; default selection works with mouse clicks


scrollbar = ctk.CTkScrollbar(root, command=treeview.yview)
scrollbar.pack(side=ctk.RIGHT, fill=ctk.Y)
treeview.configure(yscrollcommand=scrollbar.set)
# No need to bind custom select, default works
treeview.tag_configure("oddrow", background="#FFFFFF")
treeview.tag_configure("evenrow", background="#F0F0F0")
root.bind("<Return>", lambda event: on_search())
root.mainloop()
print("Done")
