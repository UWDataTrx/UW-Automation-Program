import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import customtkinter as ctk
import pandas as pd
import pyperclip
import statistics
import subprocess

# sys.stderr = open(os.devnull, 'w')


def read_drug_data(file_path):
    try:
        data = pd.read_parquet(file_path)
        data["days_supply"] = data["days_supply"].astype(float)
        data["gross_cost"] = data["affiliate_ingred_cost"] + data["affiliate_disp_fee"]
        data["30/90"] = 30
        data.loc[data["days_supply"] < 84, "30/90"] = 30
        data.loc[data["days_supply"] >= 84, "30/90"] = 90
        return data
    except Exception as e:
        print("Error reading Parquet file:", e)
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

            if dosing is not None:
                drug_info = drug_info[
                    drug_info["strength"]
                    .str.lower()
                    .str.contains(dosing.strip().lower(), na=False)
                ]
            if quantity is not None:
                drug_info = drug_info[
                    drug_info["quantity"]
                    .str.lower()
                    .str.contains(quantity.strip().lower(), na=False)
                ]
            if supply_duration is not None:
                drug_info = drug_info[drug_info["30/90"].isin(supply_duration)]

            drug_pt = (
                drug_info.groupby(["drug_name", "quantity", "30/90", "strength"])
                .agg(
                    {
                        "gross_cost": ["mean", mode_func],
                        "drug_name": "count",  # Add count aggregation
                    }
                )
                .reset_index()
            )

            # Rename columns
            drug_pt.columns = [
                "drug_name",
                "30/90",
                "strength",
                "quantity",
                "mean_cost",
                "mode_cost",
                "fill_count",
            ]
            drug_pt["mean_cost"] = drug_pt["mean_cost"].apply(lambda x: f"${x:,.2f}")
            drug_pt["mode_cost"] = drug_pt["mode_cost"].apply(
                lambda x: f"${x:,.2f}" if x is not None else "N/A"
            )
            results.append(drug_pt)
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
                        "fill_count",
                    ]
                )
            )
    return pd.concat(results)


def rebate_clicked():
    subprocess.Popen(["python", "rebate.py"])


def on_search():
    drug_names = entry_drug.get()
    drug_names = [name.strip() for name in drug_names.split(",")]
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
        df.to_parquet("selected_data.parquet", index=False)
        messagebox.showinfo(
            "Process Finished", "Selected rows have been saved as selected_data.parquet"
        )
    else:
        print("No rows selected.")


root = ctk.CTk()
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

x = (screen_width - 1250) // 2
y = (screen_height - 850) // 2

root.geometry("+{}+{}".format(x, y))
root.geometry("1250x850")
root.title("B.o.B Drug Lookup")
root.configure(fg_color="#333F48")

file_path = "bob.parquet"
data = read_drug_data(file_path)

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
    "Fill Count",
]
treeview = ttk.Treeview(root, columns=columns, show="headings", selectmode="none")
for col in columns:
    treeview.heading(col, text=col)
    if col != "Drug Name":
        treeview.column(col, anchor="center")
treeview.pack(side=ctk.LEFT, padx=5, pady=10, fill="both", expand=True)


def select(event=None):
    treeview.selection_toggle(treeview.focus())


scrollbar = ctk.CTkScrollbar(root, command=treeview.yview)
scrollbar.pack(side=ctk.RIGHT, fill=ctk.Y)
treeview.configure(yscrollcommand=scrollbar.set)
treeview.bind("<ButtonRelease-1>", select)
treeview.tag_configure("oddrow", background="#FFFFFF")
treeview.tag_configure("evenrow", background="#F0F0F0")
root.bind("<Return>", lambda event: on_search())
root.mainloop()
