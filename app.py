import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import os
from utils.utils import write_shared_log
import logging
import threading
import multiprocessing
import pandas as pd
from typing import Optional
import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from pathlib import Path
import json
import time
import re
import importlib
import importlib.util
import warnings

# Import custom modules
# Theme colors now handled by UIBuilder
from config.app_config import ProcessingConfig, AppConstants
from modules.file_processor import FileProcessor
from modules.template_processor import TemplateProcessor
from modules.data_processor import DataProcessor
from modules.process_manager import ProcessManager
from modules.ui_builder import UIBuilder
from modules.log_manager import LogManager, ThemeController

# Excel COM check
XLWINGS_AVAILABLE = importlib.util.find_spec("xlwings") is not None
EXCEL_COM_AVAILABLE = importlib.util.find_spec("win32com.client") is not None

# Logging setup
logging.basicConfig(
    filename="repricing_log.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self):
        self.config = {}
        if AppConstants.CONFIG_FILE.exists():
            self.load()
        else:
            self.save_default()

    def save_default(self):
        self.config = {"last_folder": str(Path.cwd())}
        self.save()

    def load(self):
        with open(AppConstants.CONFIG_FILE, "r") as f:
            self.config = json.load(f)

    def save(self):
        with open(AppConstants.CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)


class App:
    def __init__(self, root):
        self.root = root
        self._initialize_variables()
        self._initialize_processors()
        self.ui_builder.build_complete_ui()
        self.theme_controller.apply_initial_theme()
        self.log_manager.initialize_logging()
        self.log_manager.log_application_start()

    def _initialize_variables(self):
        """Initialize all instance variables."""
        self.file1_path = None
        self.file2_path = None
        self.template_file_path = None
        self.cancel_event = threading.Event()
        self.start_time = None
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_label_var = tk.StringVar(value="0%")
        self.config_manager = ConfigManager()
        self.selected_disruption_type = tk.StringVar(value="Tier")
        self.file1_label: Optional[ctk.CTkLabel] = None
        self.file2_label: Optional[ctk.CTkLabel] = None
        self.template_label: Optional[ctk.CTkLabel] = None
        self.toggle_theme_button: Optional[ctk.CTkButton] = None
        self.progress_bar: Optional[ctk.CTkProgressBar] = None
        self.progress_label: Optional[ctk.CTkLabel] = None

    def _initialize_processors(self):
        """Initialize all processor and manager instances."""
        self.file_processor = FileProcessor(self)
        self.template_processor = TemplateProcessor(self)
        self.data_processor = DataProcessor(self)
        self.process_manager = ProcessManager(self)
        self.ui_builder = UIBuilder(self)
        self.log_manager = LogManager(self)
        self.theme_controller = ThemeController(self)

    # The following methods are moved to their respective manager classes for better cohesion:
    # - apply_theme_colors -> ThemeController
    # - check_template -> FileProcessor
    # - sharx_lbl, epls_lbl -> ProcessManager
    # - show_shared_log_viewer -> LogManager

    # Example: Remove apply_theme_colors from App, and use self.theme_controller.apply_theme_colors instead.



    def import_file1(self):
        """Import the first file with template validation using guard clauses."""
        file_path = self._get_file_path("Select File Uploaded to Tool")
        if not file_path:
            return  # User cancelled
        
        self._set_file1_path(file_path)
        self._validate_gross_cost_template(file_path)

    def _get_file_path(self, title):
        """Get file path from file dialog."""
        return filedialog.askopenfilename(
            title=title,
            filetypes=ProcessingConfig.FILE_TYPES,
        )

    def _set_file1_path(self, file_path):
        """Set the file1 path and update UI."""
        self.file1_path = file_path
        if self.file1_label:
            self.file1_label.configure(text=os.path.basename(file_path))
        self.file_processor.check_template(file_path)
        write_shared_log("File1 imported", file_path)

    def _validate_gross_cost_template(self, file_path):
        """Validate GrossCost column and suggest template type using data processor."""
        template_suggestion = self.data_processor.validate_gross_cost_template(file_path)
        if template_suggestion:
            messagebox.showinfo("Template Selection", template_suggestion)

    def import_file2(self):
        """Import the second file."""
        file_path = self._get_file_path("Select File From Tool")
        if not file_path:
            return  # User cancelled
        
        self.file2_path = file_path
        if self.file2_label:
            self.file2_label.configure(text=os.path.basename(file_path))
        write_shared_log("File2 imported", file_path)

    def import_template_file(self):
        """Import the template file."""
        file_path = filedialog.askopenfilename(
            title="Select Template File", filetypes=ProcessingConfig.TEMPLATE_FILE_TYPES
        )
        if not file_path:
            return  # User cancelled
        
        self.template_file_path = file_path
        if self.template_label:
            self.template_label.configure(text=os.path.basename(file_path))
        write_shared_log("Template file imported", file_path)

    # Logging and notification methods
    # Removed duplicate write_audit_log method to resolve method name conflict.

    # Cancel during repricing
    def cancel_process(self):
        """Cancel the process using process manager."""
        self.process_manager.cancel_process()

    # Live log viewer (old version, renamed to avoid conflict)
    def show_log_viewer_old(self):
        win = tk.Toplevel(self.root)
        win.title("Log Viewer")
        txt = scrolledtext.ScrolledText(win, width=100, height=30)
        txt.pack(fill="both", expand=True)

        def refresh():
            with open("repricing_log.log", "r") as f:
                txt.delete("1.0", tk.END)
                txt.insert(tk.END, f.read())
            win.after(3000, refresh)

        refresh()

    def update_progress(self, value=None, message=None):
        """Update the progress bar and label with reduced complexity."""
        def do_update():
            if value is None:
                self._set_indeterminate_progress(message)
            else:
                self._set_determinate_progress(value, message)
            self.root.update_idletasks()

        self._schedule_ui_update(do_update)

    def _set_indeterminate_progress(self, message):
        """Set progress bar to indeterminate mode."""
        if self.progress_bar:
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start()
        display_message = message or "Processing... (unknown duration)"
        self.progress_label_var.set(display_message)

    def _set_determinate_progress(self, value, message):
        """Set progress bar to determinate mode with specific value."""
        if self.progress_bar:
            if self.progress_bar.cget("mode") != "determinate":
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
            
            self.progress_bar.set(value)
        
        self.progress_var.set(value)
        
        if message:
            self.progress_label_var.set(message)
        else:
            self._set_calculated_progress_message(value)

    def _set_calculated_progress_message(self, value):
        """Calculate and set progress message with time estimates."""
        percent = int(value * 100)
        elapsed = time.time() - self.start_time if self.start_time else 0
        est = int((elapsed / value) * (1 - value)) if value > 0 else 0
        self.progress_label_var.set(f"Progress: {percent}% | Est. {est}s left")

    def _schedule_ui_update(self, update_func):
        """Schedule UI update on main thread or execute immediately."""
        if threading.current_thread() is threading.main_thread():
            update_func()
        else:
            self.root.after(0, update_func)

    def write_audit_log(self, file1, file2, status):
        """Write audit log entry using file processor."""
        return self.file_processor.write_audit_log(file1, file2, status)

    def show_log_viewer(self):
        """Show log viewer using log manager."""
        self.log_manager.show_log_viewer()

    # Disruption and process methods
    # Removed select_disruption_type method since disruption_type_combobox does not exist.

    def start_disruption(self, disruption_type=None):
        """Start disruption processing using process manager."""
        self.process_manager.start_disruption(disruption_type)

    def start_process_threaded(self):
        """Start the repricing process using the process manager."""
        self.process_manager.start_process_threaded()

    def finish_notification(self):
        """Show completion notification using process manager."""
        self.process_manager.finish_notification()

    # Repricing workflow methods
    def paste_into_template(self, processed_file):
        """Paste processed data into Excel template using background threading."""
        def run_in_background():
            try:
                self._execute_template_paste(processed_file)
            except Exception as e:
                logger.exception("Error during paste with xlwings")
                self.root.after(
                    0,
                    lambda e=e: messagebox.showerror(
                        "Error", f"Template update failed:\n{e}"
                    ),
                )
                self.root.after(0, lambda: self.update_progress(0))

        threading.Thread(target=run_in_background, daemon=True).start()

    def _execute_template_paste(self, processed_file):
        """Execute the template paste operation with proper error handling."""
        import time

        start_time = time.time()
        
        # Initialize progress
        self.root.after(
            0,
            lambda: self.update_progress(None, "Preparing to paste into template..."),
        )

        # Validate template path
        if not self.template_file_path:
            raise ValueError("Template file path is not set.")

        # Prepare data and paths
        paste_data = self._prepare_template_data(processed_file)
        paths = self._prepare_template_paths()
        
        # Create backup and setup output file
        self._create_template_backup(paths)
        
        # Execute Excel operations
        self._execute_excel_paste(paste_data, paths)
        
        # Finalize and notify
        elapsed = time.time() - start_time
        msg = f"Template updated successfully in {elapsed:.2f} seconds."
        logger.info(msg)
        self.root.after(0, lambda: self.update_progress(1.0, msg))
        self.root.after(0, lambda: self.show_toast(msg))
        self.root.after(
            0,
            lambda: messagebox.showinfo(
                "Template Update Complete",
                "Pasting into the template is complete. You may now review the updated file.",
            ),
        )

    def _prepare_template_data(self, processed_file):
        """Prepare data for template pasting."""
        df = pd.read_excel(processed_file)
        df = self.format_dataframe(df)
        return {
            "data": df.values,
            "nrows": df.shape[0],
            "ncols": df.shape[1]
        }

    def _prepare_template_paths(self):
        """Prepare file paths for template operations using file processor."""
        return self.file_processor.prepare_file_paths(self.template_file_path)

    def _create_template_backup(self, paths):
        """Create backup of template and prepare output file using template processor."""
        self.template_processor.create_template_backup(paths)

    def _execute_excel_paste(self, paste_data, paths):
        """Execute the Excel paste operation."""
        import xlwings as xw
        
        # Start Excel session
        app = xw.App(visible=False)
        wb = app.books.open(str(paths["output"]))
        ws = wb.sheets["Claims Table"]

        try:
            # Batch read formulas and prepare data
            formulas = ws.range((2, 1), (paste_data["nrows"] + 1, paste_data["ncols"])).formula
            data_to_write = self._prepare_excel_data(paste_data, formulas)
            
            # Paste values with progress updates
            self._paste_data_with_progress(ws, data_to_write, paste_data["nrows"], paste_data["ncols"])
            
            # Save and close
            wb.save()
            wb.close()
            app.quit()
            
        except Exception as e:
            # Ensure Excel is closed even on error
            try:
                wb.close()
                app.quit()
            except Exception:
                pass
            raise e

    def _prepare_excel_data(self, paste_data, formulas):
        """Prepare data for Excel, preserving formulas."""
        data_to_write = []
        
        for i in range(paste_data["nrows"]):
            row = []
            for j in range(paste_data["ncols"]):
                if formulas[i][j] == "":
                    row.append(paste_data["data"][i][j])
                else:
                    row.append(None)
            data_to_write.append(row)
        
        return data_to_write

    def _paste_data_with_progress(self, ws, data_to_write, nrows, ncols):
        """Paste data to Excel with progress updates."""
        # Paste values
        ws.range((2, 1), (nrows + 1, ncols)).value = data_to_write
        
        # Update progress periodically
        for i in range(0, nrows, 250):
            percent = 0.94 + 0.04 * (i / max(1, nrows))
            msg = f"Pasting row {i + 1} of {nrows}..."
            self.root.after(
                0, lambda v=percent, m=msg: self.update_progress(v, m)
            )

    def filter_template_columns(self, df):
        try:
            # Ensure 'ClientName' and 'Logic' columns exist and are in the correct order
            if "ClientName" in df.columns and "Logic" in df.columns:
                client_name_idx = df.columns.get_loc("ClientName")
                logic_idx = df.columns.get_loc("Logic")
                if client_name_idx <= logic_idx:
                    # Select columns from 'ClientName' to 'Logic' (inclusive)
                    selected_columns = df.columns[client_name_idx : logic_idx + 1]
                    logger.info(
                        f"Pasting only these columns: {selected_columns.tolist()}"
                    )
                    return df[selected_columns]
                else:
                    logger.warning(
                        "'Logic' column appears before 'ClientName'; returning full DataFrame."
                    )
                    return df
            else:
                raise ValueError(
                    "Required columns 'ClientName' or 'Logic' are missing."
                )
        except Exception as e:
            logger.warning(f"Error filtering columns: {e}. Using full DataFrame.")
            return df

    def format_dataframe(self, df):
        """Format DataFrame using template processor."""
        return self.template_processor.format_dataframe(df)

    def show_toast(self, message, duration=3000):
        """Show toast notification using template processor."""
        return self.template_processor.show_toast(message, duration)

    def start_process(self):
        threading.Thread(target=self._start_process_internal).start()
        write_shared_log("Repricing process started", "")

    def validate_merge_inputs(self):
        """Validate merge inputs using data processor."""
        is_valid, message = self.data_processor.validate_merge_inputs(
            self.file1_path, self.file2_path
        )
        if not is_valid:
            messagebox.showerror("Error", message)
        return is_valid

    def _start_process_internal(self):
        self.start_time = time.time()
        self.update_progress(0.05)

        # Extra safeguard: Remove any accidental LBL/disruption output during repricing
        os.environ["NO_LBL_OUTPUT"] = "1"

        if not self.file1_path or not self.file2_path:
            self.update_progress(0)
            messagebox.showerror("Error", "Please select both files before proceeding.")
            return

        if not self.validate_merge_inputs():
            self.update_progress(0)
            return

        try:
            self.update_progress(0.10)
            subprocess.run(
                ["taskkill", "/F", "/IM", "excel.exe"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.update_progress(0.20)
            subprocess.run(
                ["python", "merge.py", self.file1_path, self.file2_path], check=True
            )
            self.update_progress(0.50)
            MERGED_FILE = "merged_file.xlsx"
            self.process_merged_file(MERGED_FILE)
            self.update_progress(0.90)
            # After all processing is done
            self.update_progress(1.0)
            # Ensure LBL scripts are NOT called here or in process_merged_file
        except subprocess.CalledProcessError as e:
            self.update_progress(0)
            logger.exception("Failed to run merge.py")
            messagebox.showerror("Error", f"Failed to run merge.py: {e}")

    def process_merged_file(self, file_path):
        """Process merged file with reduced complexity using helper methods."""
        try:
            # Initialize processing
            self._initialize_processing()
            
            # Load and validate data
            df = self._load_and_validate_data(file_path)
            
            # Process data using multiprocessing
            processed_df = self._process_data_multiprocessing(df)
            
            # Save outputs
            output_file = self._save_processed_outputs(processed_df)
            
            # Finalize processing
            self._finalize_processing(output_file)
            
        except Exception as e:
            logger.error(f"Error processing merged file: {e}")
            messagebox.showerror("Error", f"Processing failed: {e}")

    def _initialize_processing(self):
        """Initialize the processing environment."""
        self.update_progress(0.55)
        open("repricing_log.log", "w").close()
        logging.basicConfig(
            filename="repricing_log.log",
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logging.info("Starting merged file processing")

    def _load_and_validate_data(self, file_path):
        """Load and validate the merged file data."""
        df = pd.read_excel(file_path)
        logging.info(f"Loaded {len(df)} records from {file_path}")
        self.update_progress(0.60)

        # Validate required columns using configuration
        ProcessingConfig.validate_required_columns(df)

        # Prepare data for processing
        df = df.sort_values(by=["DATEFILLED", "SOURCERECORDID"], ascending=True)
        df["Logic"] = ""
        df["RowID"] = np.arange(len(df))
        
        return df

    def _process_data_multiprocessing(self, df):
        """Process data using multiprocessing for improved performance."""
        self.update_progress(0.65)
        
        # Import and use multiprocessing helpers
        from modules import mp_helpers

        num_workers = ProcessingConfig.get_multiprocessing_workers()
        df_blocks = np.array_split(df, num_workers)
        out_queue = multiprocessing.Queue()
        processes = []
        
        # Start worker processes
        for block in df_blocks:
            p = multiprocessing.Process(
                target=mp_helpers.worker, args=(block, out_queue)
            )
            p.start()
            processes.append(p)
        
        # Collect results
        results = [out_queue.get() for _ in processes]
        for p in processes:
            p.join()
        
        processed_df = pd.concat(results)
        self.update_progress(0.75)
        
        return processed_df

    def _save_processed_outputs(self, df):
        """Save processed data to various output formats."""
        # Sort and filter data
        df_sorted = pd.concat([df[df["Logic"] == ""], df[df["Logic"] == "OR"]])
        
        # Prepare output directory and files
        output_dir = Path.cwd()
        output_file = output_dir / "merged_file_with_OR.xlsx"
        
        # Create row mapping for highlighting
        row_mapping = {
            row["RowID"]: i + 2 for i, (_, row) in enumerate(df_sorted.iterrows())
        }
        excel_rows_to_highlight = [
            row_mapping[rid] for rid in [] if rid in row_mapping
        ]  # Placeholder
        
        # Clean up data
        df_sorted.drop(columns=["RowID"], inplace=True, errors="ignore")
        
        # Save to multiple formats
        self._save_to_parquet(df_sorted, output_dir)
        self._save_to_excel(df_sorted, output_file)
        self._save_to_csv(df_sorted, output_dir)
        
        # Save unmatched reversals info
        self._save_unmatched_reversals(excel_rows_to_highlight, output_dir)
        
        self.update_progress(0.80)
        return output_file

    def _save_to_parquet(self, df, output_dir):
        """Save data to Parquet format for large DataFrames."""
        try:
            parquet_path = output_dir / "merged_file_with_OR.parquet"
            df.drop_duplicates().to_parquet(parquet_path, index=False)
            logger.info(f"Saved intermediate Parquet file: {parquet_path}")
        except Exception as e:
            logger.warning(f"Could not save Parquet: {e}")

    def _save_to_excel(self, df, output_file):
        """Save data to Excel format."""
        df.drop_duplicates().to_excel(output_file, index=False)

    def _save_to_csv(self, df, output_dir):
        """Save data to CSV format with opportunity name."""
        opportunity_name = self._extract_opportunity_name()
        csv_path = output_dir / f"{opportunity_name} Claim Detail.csv"
        df.drop_duplicates().to_csv(csv_path, index=False)

    def _save_unmatched_reversals(self, excel_rows_to_highlight, output_dir):
        """Save unmatched reversals information."""
        unmatched_path = output_dir / "unmatched_reversals.txt"
        with open(unmatched_path, "w") as f:
            f.write(",".join(map(str, excel_rows_to_highlight)))

    def _extract_opportunity_name(self):
        """Extract opportunity name from file1_path."""
        opportunity_name = ProcessingConfig.DEFAULT_OPPORTUNITY_NAME
        try:
            if self.file1_path:
                if self.file1_path.lower().endswith(".xlsx"):
                    df_file1 = pd.read_excel(self.file1_path)
                else:
                    df_file1 = pd.read_csv(self.file1_path)
                
                if df_file1.shape[1] >= 2:
                    # Get the value from the first row, second column
                    raw_name = str(df_file1.iloc[0, 1])
                    # Clean for filename
                    opportunity_name = re.sub(r'[\\/*?:"<>|]', "_", raw_name)
        except Exception as e:
            logger.warning(f"Could not extract opportunity name from file1: {e}")
        
        return opportunity_name

    def _finalize_processing(self, output_file):
        """Finalize processing with highlighting and notifications."""
        self.highlight_unmatched_reversals(output_file)
        self.update_progress(0.85)

        messagebox.showinfo(
            "Success", f"Processing complete. File saved as {output_file}"
        )
        self.paste_into_template(output_file)
        self.update_progress(0.90)

    def highlight_unmatched_reversals(self, excel_file):
        """Highlight unmatched reversals in Excel file with reduced nesting complexity."""
        try:
            wb = load_workbook(excel_file)
            ws = wb.active
            
            # Early return if worksheet is invalid
            if ws is None:
                logger.warning("Worksheet is None, cannot highlight reversals")
                return
            
            # Early return if reversals file doesn't exist
            if not os.path.exists("unmatched_reversals.txt"):
                logger.info("No unmatched_reversals.txt file found")
                wb.save(excel_file)
                return
            
            # Apply highlighting to unmatched reversals
            self._apply_reversal_highlighting(ws, wb, excel_file)
            
        except Exception as e:
            logger.error(f"Failed to highlight unmatched reversals: {e}")

    def _apply_reversal_highlighting(self, ws, wb, excel_file):
        """Apply highlighting to rows specified in unmatched_reversals.txt."""
        fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
        
        with open("unmatched_reversals.txt", "r") as f:
            rows = f.read().strip().split(",")
        
        for row_str in rows:
            if self._is_valid_row_number(row_str, ws):
                self._highlight_row(ws, int(row_str), fill)
        
        wb.save(excel_file)
        logger.info(f"Highlighted unmatched reversals in {excel_file}")

    def _is_valid_row_number(self, row_str, ws):
        """Check if row string represents a valid row number."""
        return row_str.isdigit() and 1 <= int(row_str) <= ws.max_row

    def _highlight_row(self, ws, row_num, fill):
        """Highlight all cells in a specific row."""
        row = ws[row_num]
        for cell in row:
            cell.fill = fill


warnings.filterwarnings("ignore", category=FutureWarning, message=".*swapaxes.*")
warnings.filterwarnings("ignore", category=FutureWarning, message=".*swapaxes.*")


def process_logic_block(df_block):
    """
    Vectorized numpy logic to mark 'OR' in 'Logic' for reversals with matching claims.
    Refactored to reduce nesting complexity and improve readability.
    """
    arr = df_block.to_numpy()
    col_idx = {col: i for i, col in enumerate(df_block.columns)}
    
    # Extract and prepare data
    logic_data = _extract_logic_data(arr, col_idx)
    
    # Early return if no reversals to process
    if not np.any(logic_data["is_reversal"]):
        return pd.DataFrame(arr, columns=df_block.columns)
    
    # Process reversals with reduced nesting
    _process_reversals(arr, col_idx, logic_data)
    
    return pd.DataFrame(arr, columns=df_block.columns)


def _extract_logic_data(arr, col_idx):
    """Extract and prepare data for logic processing."""
    qty = arr[:, col_idx["QUANTITY"]].astype(float)
    return {
        "qty": qty,
        "is_reversal": qty < 0,
        "is_claim": qty > 0,
        "ndc": arr[:, col_idx["NDC"]].astype(str),
        "member": arr[:, col_idx["MemberID"]].astype(str),
        "datefilled": pd.to_datetime(arr[:, col_idx["DATEFILLED"]], errors="coerce"),
        "abs_qty": np.abs(qty)
    }


def _process_reversals(arr, col_idx, logic_data):
    """Process reversals with matching logic, using guard clauses to reduce nesting."""
    rev_idx = np.where(logic_data["is_reversal"])[0]
    claim_idx = (
        np.where(logic_data["is_claim"])[0] 
        if np.any(logic_data["is_claim"]) 
        else np.array([], dtype=int)
    )
    
    # Create context object to reduce function argument count
    match_context = MatchContext(arr, col_idx, logic_data, claim_idx)
    
    for i in rev_idx:
        found_match = _try_find_match(match_context, i)
        
        # Mark unmatched reversals as 'OR'
        if not found_match:
            arr[i, col_idx["Logic"]] = "OR"


class MatchContext:
    """Context object to encapsulate matching parameters and reduce argument count."""
    
    def __init__(self, arr, col_idx, logic_data, claim_idx):
        self.arr = arr
        self.col_idx = col_idx
        self.logic_data = logic_data
        self.claim_idx = claim_idx


def _try_find_match(context, reversal_idx):
    """Attempt to find a matching claim for a reversal. Returns True if match found."""
    # Guard clause: no claims to match against
    if context.claim_idx.size == 0:
        return False
    
    # Find potential matches
    matches = _find_matching_claims(context.logic_data, context.claim_idx, reversal_idx)
    
    # Guard clause: no matches found
    if not np.any(matches):
        return False
    
    # Mark both reversal and matching claim as 'OR'
    context.arr[reversal_idx, context.col_idx["Logic"]] = "OR"
    context.arr[context.claim_idx[matches][0], context.col_idx["Logic"]] = "OR"
    return True


def _find_matching_claims(logic_data, claim_idx, reversal_idx):
    """Find claims that match the reversal based on NDC, member, quantity, and date."""
    matches = (
        (logic_data["ndc"][claim_idx] == logic_data["ndc"][reversal_idx])
        & (logic_data["member"][claim_idx] == logic_data["member"][reversal_idx])
        & (logic_data["abs_qty"][claim_idx] == logic_data["abs_qty"][reversal_idx])
    )
    
    # Add date constraint (within 30 days)
    date_diffs = np.abs(
        (logic_data["datefilled"][claim_idx] - logic_data["datefilled"][reversal_idx]).days
    )
    matches &= date_diffs <= 30
    
    return matches


if __name__ == "__main__":
    multiprocessing.freeze_support()
    ctk.set_appearance_mode("light")  # Start in light mode
    root = ctk.CTk()  # or tk.Tk() if not using customtkinter
    app = App(root)
    root.mainloop()
