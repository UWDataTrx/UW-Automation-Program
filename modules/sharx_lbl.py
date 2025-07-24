import logging
import tkinter as tk
import sys
from pathlib import Path
# Ensure project root is in sys.path before importing project_settings
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from project_settings import PROJECT_ROOT  # noqa: E402
from tkinter import messagebox  # noqa: E402
import pandas as pd  # noqa: E402
from utils.excel_utils import write_df_to_template  # noqa: E402
from utils.utils import write_audit_log  # noqa: E402
from config.config_loader import ConfigManager  # noqa: E402
from modules.audit_helper import (  # noqa: E402
    make_audit_entry,
    log_user_session_start,
    log_user_session_end,
    log_file_access,
)
import sys  # noqa: E402
# Ensure project root is in sys.path before importing project_settings
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


CLAIMS_SHEET = "Claims Table"
OUTPUT_SHEET = "Line By Line"
output_filename = "LBL for Disruption.xlsx"
if len(sys.argv) > 1:
    output_filename = sys.argv[1]
output_path = Path(output_filename).resolve()
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

# Setup logging
logging.basicConfig(
    filename="sharx_lbl.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def show_message(awp: float, ing: float, total: float, rxs: int) -> None:
    messagebox.showinfo(
        "Process Complete",
        f"SHARx LBL has been created\n\n"
        f"Total AWP: ${awp:.2f}\n\n"
        f"Total Ing Cost: ${ing:.2f}\n\n"
        f"Total Gross Cost: ${total:.2f}\n\n"
        f"Total Claim Count: {rxs}",
    )


def main():
    root = tk.Tk()
    root.withdraw()

    # Start audit session
    log_user_session_start("sharx_lbl.py")
    write_audit_log("sharx_lbl.py", "Processing started.")

    try:
        # Get the config file path relative to the project root
        config_manager = ConfigManager()
        paths = config_manager.get("file_paths.json")
        # Fallback to file dialogs if required keys are missing
        if "reprice" not in paths:
            from tkinter import filedialog

            paths["reprice"] = filedialog.askopenfilename(title="Select Claims File")
        if "sharx" not in paths:
            from tkinter import filedialog

            paths["sharx"] = filedialog.askopenfilename(
                title="Select SHARx Template File"
            )

        template_path = Path(paths["sharx"]).resolve()

        # Log file access
        log_file_access("sharx_lbl.py", paths["reprice"], "LOADING")
        log_file_access("sharx_lbl.py", paths["sharx"], "LOADING")

        try:
            df = pd.read_excel(paths["reprice"], sheet_name=CLAIMS_SHEET)
        except FileNotFoundError:
            logger.error(f"Claims file not found: {paths['reprice']}")
            make_audit_entry(
                "sharx_lbl.py",
                f"Claims file not found: {paths['reprice']}",
                "FILE_ERROR",
            )
            raise FileNotFoundError(f"Claims file not found: {paths['reprice']}")
        except ValueError as e:
            logger.error(f"Sheet loading failed: {e}")
            make_audit_entry("sharx_lbl.py", f"Sheet loading failed: {e}", "DATA_ERROR")
            raise ValueError(f"Sheet loading failed: {e}")

        # Debug print and log
        print("Columns in claims DataFrame:")
        print(df.columns)
        logger.info(f"Columns in claims DataFrame: {df.columns.tolist()}")

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
            "GrossCost",
            "Pharmacy Name",
            "INPUTFILECHANNEL",
            "DATEFILLED",
            "MemberID",
            "DAYSUPPLY",
            "QUANTITY",
            "NDC",
            "DST Drug Name",
        ]
        missing_cols = [col for col in columns_to_keep if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing columns in input data: {missing_cols}")
        df = df[columns_to_keep]

        output_path = Path("_Rx Claims for SHARx.xlsx").resolve()

        write_df_to_template(
            str(template_path),
            str(output_path),
            sheet_name=OUTPUT_SHEET,
            df=df,
            start_cell="A2",
            header=False,
            index=False,
            open_file=False,
            visible=False,
        )

        logger.info(f"SHARx output saved to: {output_path}")
        logger.info("SHARx LBL file created successfully.")

        # Log successful completion
        make_audit_entry(
            "sharx_lbl.py", f"Successfully generated SHARx file: {output_path}", "INFO"
        )
        log_file_access("sharx_lbl.py", str(output_path), "CREATED")

        write_audit_log("sharx_lbl.py", "SHARx LBL file created successfully.")
        show_message(awp, ing, total, rxs)
        messagebox.showinfo("Processing Complete", "Processing complete")

    except Exception as e:
        logger.exception("An error occurred during SHARx LBL processing")
        make_audit_entry(
            "sharx_lbl.py", f"Processing failed with error: {str(e)}", "SYSTEM_ERROR"
        )
        write_audit_log("sharx_lbl.py", f"An error occurred: {e}", status="ERROR")
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        # End audit session
        log_user_session_end("sharx_lbl.py")
        root.quit()


if __name__ == "__main__":
    main()
