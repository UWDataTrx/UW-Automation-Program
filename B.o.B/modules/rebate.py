import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import customtkinter as ctk
import pyperclip
import os
import sys

sys.stderr = open(os.devnull, 'w')



def vlookup_rebate(parquet_file, rebate_file):
    # Check file existence
    if not os.path.exists(parquet_file):
        messagebox.showerror("File Not Found", f"The file '{parquet_file}' does not exist.")
        return None
    if not os.path.exists(rebate_file):
        messagebox.showerror("File Not Found", f"The file '{rebate_file}' does not exist.")
        return None
    try:
        df = pd.read_parquet(parquet_file)
    except Exception as e:
        messagebox.showerror("Read Error", f"Could not read Parquet file: {e}")
        return None
    try:
        rebate_df = pd.read_csv(rebate_file)
    except Exception as e:
        messagebox.showerror("Read Error", f"Could not read CSV file: {e}")
        return None

    # Check for required columns
    required_df_cols = ['Drug Name', 'Average Cost', 'Mode Cost']
    required_rebate_cols = ['drug_name', 'Rebatable', 'specialty']
    missing_df_cols = [col for col in required_df_cols if col not in df.columns]
    missing_rebate_cols = [col for col in required_rebate_cols if col not in rebate_df.columns]
    if missing_df_cols:
        messagebox.showerror("Missing Columns", f"The following columns are missing in {parquet_file}: {', '.join(missing_df_cols)}")
        return None
    if missing_rebate_cols:
        messagebox.showerror("Missing Columns", f"The following columns are missing in {rebate_file}: {', '.join(missing_rebate_cols)}")
        return None

    df['Drug Name'] = df['Drug Name'].str.capitalize()
    rebate_df['drug_name'] = rebate_df['drug_name'].str.capitalize()

    merged_df = pd.merge(df, rebate_df, left_on='Drug Name', right_on='drug_name', how='left')
    merged_df = merged_df.drop_duplicates(subset='Drug Name', keep='first')

    columns = ["Drug Name", "Average Cost", "Mode Cost", "Rebatable", "specialty"]
    merged_df = merged_df[columns]
    merged_df = merged_df.fillna('Delete Row')

    if merged_df.empty:
        messagebox.showinfo("No Results", "No matching drugs found in rebate lookup.")
        return None

    return merged_df


def display_data(merged_df):
    if merged_df is None or merged_df.empty:
        return
    def copy_to_clipboard():
        selected_items = treeview.selection()
        if selected_items:
            selected_rows = [treeview.item(item, "values") for item in selected_items]
            tab_separated_data = "\n".join(["\t".join(map(str, row)) for row in selected_rows])
            pyperclip.copy(tab_separated_data)
        else:
            print("No rows selected.")

    def select_all():
        for item in treeview.get_children():
            select_children(item)

    def select_children(item):
        treeview.selection_add(item)
        item_children = treeview.get_children(item)
        if item_children:
            for item_inner in item_children:
                select_children(item_inner)



    root = ctk.CTk()

    screen_width = root.winfo_screenwidth()

    window_height = 500
    root.geometry(f"{screen_width}x{window_height}+0+250")
    root.title("Rebate Lookup Results")
    root.configure(fg_color="#333F48")

    frame = ctk.CTkFrame(root, bg_color='#333F48',fg_color="#333F48")
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    label = ctk.CTkLabel(frame, text="Savings Analysis Lookup", font=("Oswald", 24, 'bold'))
    label.pack(side=ctk.TOP,padx=5, pady=10)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview.Heading", font=("Oswald", 12, 'bold'), foreground='#333F48', background='dark grey', relief='flat')
    style.configure("Treeview", font=("Oswald", 12), rowheight=25, background='#333F48', fieldbackground='#333F48', bordercolor="#333F48")

    columns = merged_df.columns.tolist()

    treeview = ttk.Treeview(frame, columns=columns, show="headings")
    for i, col in enumerate(columns):
        try:
            treeview.heading(i, text=col)
            if col == "Drug Name":
                treeview.column(i, anchor="w")
            else:
                treeview.column(i, anchor="center")
        except tk.TclError as e:
            print("Error setting up column:", e)

    treeview.tag_configure('oddrow', background='#FFFFFF')
    treeview.tag_configure('evenrow', background='#F0F0F0')

    merged_df.reset_index(drop=True, inplace=True)

    for index, row in merged_df.iterrows():
        values = [str(val) for val in row.tolist()]
        tag = 'oddrow' if index % 2 == 0 else 'evenrow'
        treeview.insert("", "end", values=values, tags=(tag,))

    scrollbar = ctk.CTkScrollbar(frame, command=treeview.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    treeview.configure(yscrollcommand=scrollbar.set)

    treeview.pack(side=ctk.LEFT, fill="both", expand=True)

    button_copy = ctk.CTkButton(root, text="Copy Selected Rows", command=copy_to_clipboard, font=("Oswald", 16, 'bold'))
    button_copy.pack(side=ctk.BOTTOM, pady=10)

    all_button = ctk.CTkButton(root, text="Select All Rows", command=select_all, font=("Oswald", 16, 'bold'))
    all_button.pack(side=ctk.BOTTOM, pady=10)

    root.mainloop()


if __name__ == "__main__":
    parquet_file = "selected_data.parquet"
    rebate_file = "merged_file.csv"
    merged_df = vlookup_rebate(parquet_file, rebate_file)
    display_data(merged_df)
