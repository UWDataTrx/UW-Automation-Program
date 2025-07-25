import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging  # noqa: E402
import tkinter as tk  # noqa: E402
from tkinter import messagebox  # noqa: E402
import pandas as pd  # noqa: E402



try:
    from utils.excel_utils import write_df_to_template
    from utils.utils import write_audit_log
    from config.config_loader import ConfigManager
except ImportError:

    def write_df_to_template(*args, **kwargs) -> None:
        raise ImportError(
            "utils.excel_utils not available - write_df_to_template not implemented"
        )

    def load_file_paths(*args, **kwargs) -> dict:
        raise ImportError("utils.utils not available - load_file_paths not implemented")

    def write_audit_log(script_name, message, status="INFO"):
        print(f"[{status}] {script_name}: {message}")

    raise ImportError(
        "ConfigManager is required but could not be imported from config.config_loader."
    )


try:
    from modules.audit_helper import (
        make_audit_entry,
        log_user_session_start,
        log_user_session_end,
        log_file_access,
    )
except ImportError:

    def make_audit_entry(script_name, message, status="INFO"):
        print(f"[AUDIT {status}] {script_name}: {message}")

    def log_user_session_start(script_name):
        print(f"[SESSION START] {script_name}")

    def log_user_session_end(script_name):
        print(f"[SESSION END] {script_name}")

    def log_file_access(script_name, file_path, operation):
        print(f"[FILE ACCESS] {script_name}: {operation} - {file_path}")


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
    # Overwrite protection: prevent output file from matching any input file
    output_path = Path("_Rx Claims for EPLS.xlsx").resolve()
    input_files = []
    try:
        config_manager = ConfigManager()
        file_paths = config_manager.get("file_paths.json")
        for key, val in file_paths.items():
            if val:
                input_files.append(str(Path(val).resolve()))
    except Exception:
        pass
    if str(output_path) in input_files:
        raise RuntimeError(
            f"Output file {output_path} matches an input file. Please choose a different output filename."
        )
    # Start audit session
    log_user_session_start("epls_lbl.py")
    write_audit_log("epls_lbl.py", "Processing started.")
    try:
        config_manager = ConfigManager()
        paths = config_manager.get("file_paths.json")
        for key in ["reprice", "epls"]:
            if not Path(paths[key]).exists():
                make_audit_entry(
                    "epls_lbl.py", f"{key} path not found: {paths[key]}", "FILE_ERROR"
                )
                raise FileNotFoundError(f"{key} path not found: {paths[key]}")
        template_path = Path(paths["epls"])
        log_file_access("epls_lbl.py", paths["reprice"], "LOADING")
        log_file_access("epls_lbl.py", paths["epls"], "LOADING")
        df = pd.read_excel(paths["reprice"], sheet_name="Claims Table")
        print("Columns in claims DataFrame:")
        print(df.columns)
        logger.info(f"Columns in claims DataFrame: {df.columns.tolist()}")
        if "Logic" not in df.columns:
            make_audit_entry(
                "epls_lbl.py", "Missing 'Logic' column in Claims Table", "DATA_ERROR"
            )
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
        make_audit_entry(
            "epls_lbl.py", f"Successfully generated EPLS file: {output_path}", "INFO"
        )
        log_file_access("epls_lbl.py", str(output_path), "CREATED")
        write_audit_log("epls_lbl.py", "EPLS LBL file created successfully.")
        show_message(awp, ing, total, rxs)
        messagebox.showinfo("Processing Complete", "Processing complete")
    except Exception as e:
        logger.exception("An error occurred during EPLS LBL processing")
        make_audit_entry(
            "epls_lbl.py", f"Processing failed with error: {str(e)}", "SYSTEM_ERROR"
        )
        write_audit_log("epls_lbl.py", f"An error occurred: {e}", status="ERROR")
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        log_user_session_end("epls_lbl.py")


if __name__ == "__main__":
    main()
