"""
Process management module for handling automation workflows.
Extracted from app.py to improve cohesion and reduce file size.
"""

import subprocess
import threading
import time
import logging
import os
import sys
from tkinter import messagebox

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
from config.app_config import DisruptionConfig
from utils.utils import write_shared_log


class ProcessManager:
    """Handles process management and workflow orchestration."""

    def __init__(self, app_instance):
        self.app = app_instance

    def start_process_threaded(self):
        """Start the main repricing process in a separate thread."""
        threading.Thread(target=self._start_process_internal).start()
        write_shared_log("ProcessManager", "Repricing process started")

    def _start_process_internal(self):
        """Internal method to handle the repricing process."""
        try:
            self.app.start_time = time.time()
            self.app.update_progress(0.05)

            # Extra safeguard: Remove any accidental LBL/disruption output during repricing
            os.environ["NO_LBL_OUTPUT"] = "1"

            # Validate inputs
            if not self.app.validate_merge_inputs():
                self.app.update_progress(0)
                return

            # Kill Excel processes
            self.app.update_progress(0.10)
            self._kill_excel_processes()

            # Run merge operation
            self.app.update_progress(0.20)
            self._run_merge_process()

            # Process merged file
            self.app.update_progress(0.50)
            merged_file = "merged_file.xlsx"
            self.app.process_merged_file(merged_file)

            # Progress will reach 100% when template pasting is complete in app.py

        except Exception as e:
            self.app.update_progress(0)
            logging.error(f"Process failed: {e}")
            messagebox.showerror("Error", f"Process failed: {e}")

    def _kill_excel_processes(self):
        """Kill any running Excel processes."""
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", "excel.exe"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as e:
            logging.warning(f"Could not kill Excel processes: {e}")

    def _run_merge_process(self):
        """Run the merge.py script with file inputs."""
        try:
            # Get the correct path to merge.py
            merge_script_path = os.path.join(os.path.dirname(__file__), "merge.py")
            subprocess.run(
                ["python", merge_script_path, self.app.file1_path, self.app.file2_path],
                check=True,
                cwd=os.path.dirname(
                    os.path.dirname(__file__)
                ),  # Set working directory to project root
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"Merge process failed: {e}")
            raise

    def start_disruption(self, disruption_type=None):
        """Start disruption processing using configuration-driven approach."""
        if disruption_type is None:
            disruption_type = self.app.selected_disruption_type.get().strip()

        program_file = DisruptionConfig.get_program_file(disruption_type)
        if not program_file:
            messagebox.showerror("Error", f"Unknown disruption type: {disruption_type}")
            return

        self._execute_disruption_process(disruption_type, program_file)

    def _execute_disruption_process(self, disruption_type, program_file):
        """Execute the disruption process with error handling."""
        try:
            # Get the correct path to the program file
            script_path = os.path.join(os.path.dirname(__file__), program_file)
            args = ["python", script_path]
            if self.app.template_file_path:
                args.append(str(self.app.template_file_path))

            # Use subprocess to run the disruption script
            subprocess.Popen(args, cwd=os.path.dirname(os.path.dirname(__file__)))
            messagebox.showinfo(
                "Success",
                f"{disruption_type} disruption started in a separate process.",
            )

        except Exception as e:
            logging.error(f"Failed to start {program_file}: {e}")
            messagebox.showerror("Error", f"{disruption_type} disruption failed: {e}")

    def run_label_generation(self, label_type):
        """Run label generation scripts (SHARx or EPLS)."""
        try:
            script_name = f"{label_type.lower()}_lbl.py"
            script_path = os.path.join(os.path.dirname(__file__), script_name)
            subprocess.run(
                ["python", script_path],
                check=True,
                cwd=os.path.dirname(os.path.dirname(__file__)),
            )
            write_shared_log("ProcessManager", f"{label_type} LBL generation completed")

        except subprocess.CalledProcessError as e:
            logging.error(f"{label_type} LBL generation failed: {e}")
            messagebox.showerror("Error", f"{label_type} LBL generation failed: {e}")

    def cancel_process(self):
        """Cancel the current process."""
        logging.info("Process cancellation requested")
        write_shared_log("ProcessManager", "Process cancelled")
        messagebox.showinfo("Cancelled", "Process cancellation requested.")

    def finish_notification(self):
        """Show completion notification."""
        try:
            from plyer import notification

            if hasattr(notification, "notify") and callable(notification.notify):
                notification.notify(
                    title="Repricing Automation",
                    message="Batch processing completed.",
                    timeout=5,
                )
        except ImportError:
            pass  # Notification not available

        write_shared_log("ProcessManager", "Batch processing completed")
        messagebox.showinfo("Completed", "Batch processing finished!")
