import csv
import getpass
import sys
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext

# Ensure project root is in sys.path before importing other modules
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
import json  # noqa: E402
import logging  # noqa: E402

from modules.audit_helper import (log_user_session_end,  # noqa: E402
                                  log_user_session_start, validate_user_access)
from utils.utils import write_audit_log  # noqa: E402


class LogManager:
    """Handles log viewing and management operations."""

    def __init__(self, app_instance):
        self.app = app_instance
        # Load the audit log path from config
        config_path = Path(__file__).parent.parent / "config" / "file_paths.json"
        with open(config_path, "r") as f:
            file_paths = json.load(f)
        log_path_str = file_paths["audit_log"]
        if log_path_str.startswith("$") or "${" in log_path_str:
            import os

            log_path_str = os.path.expandvars(log_path_str)
        self.shared_log_path = str(Path(log_path_str))

    def show_log_viewer(self):
        """Show the live log viewer window."""
        log_win = tk.Toplevel(self.app.root)
        log_win.title("Live Log Viewer")
        text_area = scrolledtext.ScrolledText(log_win, width=100, height=30)
        text_area.pack(fill="both", expand=True)

        def update_logs():
            try:
                with open("repricing_log.log", "r") as f:
                    text_area.delete(1.0, tk.END)
                    text_area.insert(tk.END, f.read())
            except FileNotFoundError:
                text_area.delete(1.0, tk.END)
                text_area.insert(tk.END, "No log file found.")
            except Exception as e:
                text_area.delete(1.0, tk.END)
                text_area.insert(tk.END, f"Error reading log file: {e}")
            log_win.after(3000, update_logs)

        update_logs()

    def show_shared_log_viewer(self):
        """Show the shared audit log viewer with search functionality."""
        log_win = tk.Toplevel(self.app.root)
        log_win.title("Shared Audit Log Viewer")
        log_win.geometry("1000x600")

        # Create filter frame
        filter_frame = tk.Frame(log_win)
        filter_frame.pack(fill="x")
        tk.Label(filter_frame, text="Search:").pack(side="left", padx=5)
        filter_entry = tk.Entry(filter_frame)
        filter_entry.pack(side="left", fill="x", expand=True, padx=5)

        # Create text area
        text_area = scrolledtext.ScrolledText(log_win, width=150, height=30)
        text_area.pack(fill="both", expand=True)

        def refresh():
            """Refresh the log display with optional filtering."""
            try:
                username = getpass.getuser()

                base_log_dir = Path(self.shared_log_path).parent
                user_log_path = base_log_dir / username / "Audit_Log.csv"
                if not user_log_path.exists():
                    text_area.delete(1.0, tk.END)
                    text_area.insert(
                        tk.END, f"Audit log file not found at: {user_log_path}"
                    )
                    return

                with user_log_path.open("r", newline="", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    rows = list(reader)

                search_term = filter_entry.get().lower()
                if search_term:
                    filtered = [
                        row
                        for row in rows
                        if any(search_term in str(cell).lower() for cell in row)
                    ]
                else:
                    filtered = rows

                text_area.delete(1.0, tk.END)
                for row in filtered:
                    text_area.insert(tk.END, " | ".join(row) + "\n")

            except Exception as e:
                text_area.delete(1.0, tk.END)
                text_area.insert(tk.END, f"[ERROR] Could not read audit log:\n{e}")
                logging.error(f"Error reading audit log: {e}")

            # Auto-refresh every 5 seconds
            log_win.after(5000, refresh)

        # Bind search on Enter key
        filter_entry.bind("<Return>", lambda event: refresh())

        # Initial load
        refresh()

    def initialize_logging(self):
        """Initialize logging configuration."""
        # Clear existing log
        log_file = "repricing_log.log"
        try:
            open(log_file, "w").close()  # Clear the file
        except Exception as e:
            logging.warning(f"Could not clear log file: {e}")

        # Configure logging
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            filemode="w",  # Overwrite mode
        )
        logging.info("Logging initialized")

    def log_application_start(self):
        """Log application startup with comprehensive user information."""
        # Validate user access first
        if not validate_user_access():
            logging.warning("User validation failed but allowing access")

        logging.info("Repricing Automation application started")
        log_user_session_start("RepricingApp")

    def log_application_shutdown(self):
        """Log application shutdown with user information."""
        logging.info("Repricing Automation application shutting down")
        log_user_session_end("RepricingApp")


class ThemeController:
    """Controls theme switching functionality."""

    def __init__(self, app_instance):
        self.app = app_instance
        self.current_theme = "light"

    def toggle_dark_mode(self):
        """Toggle between light and dark themes."""
        import customtkinter as ctk

        from ui.ui_components import DARK_COLORS, LIGHT_COLORS, ThemeManager

        if self.current_theme == "light":
            # Switch to Dark mode
            ctk.set_appearance_mode("dark")
            ThemeManager.apply_theme_colors(self.app, DARK_COLORS)
            self.app.toggle_theme_button.configure(text="Switch to Light Mode")
            self.current_theme = "dark"
        else:
            # Switch to Light mode
            ctk.set_appearance_mode("light")
            ThemeManager.apply_theme_colors(self.app, LIGHT_COLORS)
            self.app.toggle_theme_button.configure(text="Switch to Dark Mode")
            self.current_theme = "light"

        logging.info(f"Theme switched to {self.current_theme} mode")
        write_audit_log("ThemeController", f"Theme changed to {self.current_theme}")

    def apply_initial_theme(self):
        """Apply the initial light theme."""
        from ui.ui_components import LIGHT_COLORS, ThemeManager

        ThemeManager.apply_theme_colors(self.app, LIGHT_COLORS)
