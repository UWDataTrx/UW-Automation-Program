import sys
from pathlib import Path

# Ensure project root is in sys.path before importing project_settings
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    from project_settings import PROJECT_ROOT

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))

import subprocess  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import logging  # noqa: E402
from tkinter import messagebox  # noqa: E402
from config.app_config import DisruptionConfig  # noqa: E402
from utils.utils import write_audit_log  # noqa: E402


class ProcessManager:
    """Handles process management and workflow orchestration."""

    def __init__(self, app_instance):
        self.app = app_instance

    def start_process_threaded(self):
        """Start the main repricing process in a separate thread."""
        threading.Thread(target=self._start_process_internal).start()
        write_audit_log("ProcessManager", "Repricing process started")

    def _start_process_internal(self):
        """Internal method to handle the repricing process."""
        try:
            self.app.start_time = time.time()
            self.app.update_progress(0.05)

            # Extra safeguard: Remove any accidental LBL/disruption output during repricing
            # (implementation here if needed)

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

    @staticmethod
    def _kill_excel_processes():
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
            merge_script_path = Path(__file__).parent / "merge.py"
            subprocess.run(
                [
                    "python",
                    str(merge_script_path),
                    self.app.file1_path,
                    self.app.file2_path,
                ],
                check=True,
                cwd=str(
                    Path(__file__).parent.parent
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

            script_path = Path(__file__).parent / program_file
            args = ["python", str(script_path)]
            if self.app.template_file_path:
                args.append(str(self.app.template_file_path))

            # Use subprocess to run the disruption script
            subprocess.Popen(args, cwd=str(Path(__file__).parent.parent))
            messagebox.showinfo(
                "Success",
                f"{disruption_type} disruption started in a separate process.",
            )

        except Exception as e:
            logging.error(f"Failed to start {program_file}: {e}")
            messagebox.showerror("Error", f"{disruption_type} disruption failed: {e}")

    @staticmethod
    def run_label_generation(label_type):
        """Run label generation scripts (SHARx or EPLS)."""
        try:
            script_name = f"{label_type.lower()}_lbl.py"
            script_path = Path(__file__).parent / script_name
            subprocess.run(
                ["python", str(script_path)],
                check=True,
                cwd=str(Path(__file__).parent.parent),
            )
            write_audit_log("ProcessManager", f"{label_type} LBL generation completed")

        except subprocess.CalledProcessError as e:
            logging.error(f"{label_type} LBL generation failed: {e}")
            messagebox.showerror("Error", f"{label_type} LBL generation failed: {e}")

    @staticmethod
    def cancel_process():
        """Cancel the current process."""
        logging.info("Process cancellation requested")
        write_audit_log("ProcessManager", "Process cancelled")
        messagebox.showinfo("Cancelled", "Process cancellation requested.")

    @staticmethod
    def finish_notification():
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

        write_audit_log("ProcessManager", "Batch processing completed")
        messagebox.showinfo("Completed", "Batch processing finished!")
