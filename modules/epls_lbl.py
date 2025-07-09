import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
import os
import sys

import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.excel_utils import write_df_to_template

from utils.utils import load_file_paths, write_shared_log

# Setup logging
logging.basicConfig(
    filename="epls_lbl.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def show_message(awp, ing, total, rxs):
    messagebox.showinfo(
        "Process Complete",
        f"EPLS LBL has been created\n\n"
        f"Total AWP: ${awp:.2f}\n\n"
        f"Total Ing Cost: ${ing:.2f}\n\n"
        f"Total Gross Cost: ${total:.2f}\n\n"
        f"Total Claim Count: {rxs}",
    )


def main() -> None:
    tk.Tk().withdraw()
    write_shared_log("epls_lbl.py", "Processing started.")
    try:
        # Get the config file path relative to the project root
        config_path = Path(__file__).parent.parent / "config" / "file_paths.json"
        paths = load_file_paths(str(config_path))

        # Failsafe: check that both input and template files exist
        for key in ["reprice", "epls"]:
            if not Path(paths[key]).exists():
                raise FileNotFoundError(f"{key} path not found: {paths[key]}")

        template_path = Path(paths["epls"])
        df = pd.read_excel(paths["reprice"], sheet_name="Claims Table")

        # Debug print and log
        print("Columns in claims DataFrame:")
        print(df.columns)
        logger.info(f"Columns in claims DataFrame: {df.columns.tolist()}")

        if "Logic" not in df.columns:
            raise KeyError("Missing 'Logic' column in Claims Table.")

        df["Logic"] = pd.to_numeric(df["Logic"], errors="coerce")
        df = df[df["Logic"].between(1, 10)]

        awp = df["Total AWP (Historical)"].sum()
        ing = df["Rx Sense Ing Cost"].sum()
        total = df["RxSense Total Cost"].sum()
        rxs = df["Rxs"].sum()

        columns_to_keep = [
            "MONY",
            "Rxs",
            "Rx Sense Ing Cost",
            "RxSense Dispense Fee",
            "RxSense Total Cost",
            "Total AWP (Historical)",
            "Pharmacy Name",
            "INPUTFILECHANNEL",
            "DATEFILLED",
            "MemberID",
            "DAYSUPPLY",
            "QUANTITY",
            "NDC",
            "DST Drug Name",
            "GrossCost",
            "Universal Rebates",
            "Exclusive Rebates",
            "Specialty Vlookup",
        ]

        missing_cols = [col for col in columns_to_keep if col not in df.columns]
        if missing_cols:
            raise KeyError(f"Missing expected columns: {missing_cols}")

        df = df[columns_to_keep]
        logger.info(f"Filtered DataFrame shape: {df.shape}")

        df["Specialty Vlookup"] = df["Specialty Vlookup"].map({"No": "N"}).fillna("Y")

        logger.info(f"AWP: {awp:.2f}, Ing: {ing:.2f}, Total: {total:.2f}, Rxs: {rxs}")

        output_path = Path("_Rx Claims for EPLS.xlsx")
        write_df_to_template(
            str(template_path),
            str(output_path),
            sheet_name="Line By Line",
            df=df,
            start_cell="A2",
            header=False,
            index=False,
            open_file=False,
            visible=False,
        )

        logger.info("EPLS LBL file created successfully.")
        write_shared_log("epls_lbl.py", "EPLS LBL file created successfully.")
        show_message(awp, ing, total, rxs)
        messagebox.showinfo("Processing Complete", "Processing complete")
    except Exception as e:
        logger.exception("An error occurred during EPLS LBL processing")
        write_shared_log("epls_lbl.py", f"An error occurred: {e}", status="ERROR")
        messagebox.showerror("Error", f"An error occurred: {e}")


if __name__ == "__main__":
    main()
