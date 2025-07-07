import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import os
import shutil
from utils.utils import write_shared_log
import logging
import threading
import multiprocessing
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

from pathlib import Path
import json
import csv
import time
from datetime import datetime
from plyer import notification
import re
import importlib
import importlib.util
import warnings

import random
import pyjokes
import emoji

# Excel COM check
XLWINGS_AVAILABLE = importlib.util.find_spec("xlwings") is not None
EXCEL_COM_AVAILABLE = importlib.util.find_spec("win32com.client") is not None

# Configuration and audit log files
CONFIG_FILE = Path("config.json")
AUDIT_LOG = Path("audit_log.csv")

# UI styling variables
font_select = ("Cambria", 20, "bold")

# Color palettes
LIGHT_COLORS = {
    "dark_blue": "#D9EAF7",
    "grey_blue": "#A3B9CC",
    "mint": "#8FD9A8",
    "button_red": "#D52B2B",
}
DARK_COLORS = {
    "dark_blue": "#223354",
    "grey_blue": "#31476A",
    "mint": "#26A69A",
    "button_red": "#931D1D",
}

# Template handling constants
BACKUP_SUFFIX = "_backup.xlsx"
UPDATED_TEMPLATE_NAME = "_Rx Repricing_wf.xlsx"

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
        if CONFIG_FILE.exists():
            self.load()
        else:
            self.save_default()

    def save_default(self):
        self.config = {"last_folder": str(Path.cwd())}
        self.save()

    def load(self):
        with open(CONFIG_FILE, "r") as f:
            self.config = json.load(f)

    def save(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)


class App:
    def __init__(self, root):
        import getpass

        self.root = root
        self.root.title("Reprice Automation")
        self.root.configure(fg_color=LIGHT_COLORS["dark_blue"])
        self.root.resizable(True, True)
        # Ensure full UI visibility on launch
        self.root.geometry("900x900")
        # Or maximize window:
        # self.root.state('zoomed')

        # Paths
        self.file1_path = None
        self.file2_path = None
        self.template_file_path = None

        # Process control
        self.cancel_event = threading.Event()
        self.start_time = None

        # Progress variables
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_label_var = tk.StringVar(value="0%")

        # Config
        self.config_manager = ConfigManager()

        self.selected_disruption_type = tk.StringVar(value="Tier")

        self._build_ui()
        # Move apply_theme_colors call after method definition or ensure method is defined above this line
        # self.apply_theme_colors(LIGHT_COLORS)  # Temporarily comment out

        default_template = Path("_Rx Repricing_wf.xlsx")
        if default_template.exists():
            self.template_file_path = str(default_template)
        else:
            self.template_file_path = None

        # Show a personalized welcome message with a random joke and emoji
        user = getpass.getuser()
        welcome_messages = {
            "DamionMorrison": "Welcome back, Damion! Ready to reprice?",
            "DannyBushnell": "Hello Danny! Let's get started.",
            "BrettBauer": "Hi Brett, your automation awaits!",
            "BrendanReamer": "Welcome Brendan! Ready to optimize?",
        }
        msg = welcome_messages.get(
            user, f"Welcome, {user}! Ready to use the Repricing Automation Toolkit?"
        )

        # Add a random joke and emoji
        try:
            joke = pyjokes.get_joke()
        except Exception:
            joke = "Have a great day!"
        emojis = [
            ":rocket:",
            ":sunglasses:",
            ":star:",
            ":tada:",
            ":computer:",
            ":chart_with_upwards_trend:",
        ]
        chosen_emoji = emoji.emojize(random.choice(emojis), language="alias")
        full_msg = f"{msg}\n\n{joke} {chosen_emoji}"
        self.root.after(500, lambda: messagebox.showinfo("Welcome", full_msg))

    def apply_theme_colors(self, colors):
        self.root.configure(fg_color=colors["dark_blue"])
        self.button_frame.configure(fg_color=colors["grey_blue"])
        self.notes_frame.configure(fg_color=colors["grey_blue"])
        self.dis_frame.configure(fg_color=colors["grey_blue"])
        self.prog_frame.configure(fg_color=colors["grey_blue"])

        button_widgets = [
            "file1_button",
            "file2_button",
            "template_button",
            "cancel_button",
            "logs_button",
            "toggle_theme_button",
            "sharx_lbl_button",
            "epls_lbl_button",
            "start_process_button",
        ]
        for btn_name in button_widgets:
            btn = getattr(self, btn_name, None)
            if btn:
                btn.configure(fg_color=colors["mint"], text_color="#000000")

        if hasattr(self, "exit_button"):
            self.exit_button.configure(
                fg_color=colors["button_red"], text_color="#000000"
            )
        # Removed obsolete UI elements: start_disruption_button and disruption_type_combobox
        if hasattr(self, "prog_frame"):
            self.prog_frame.configure(fg_color=colors["grey_blue"])
        if hasattr(self, "progress_label"):
            self.progress_label.configure(
                bg_color=colors["grey_blue"], text_color="#000000"
            )

    def check_template(self, file_path):
        print(f"Checking template for: {file_path}")

    def sharx_lbl(self):
        try:
            subprocess.run(["python", "sharx_lbl.py"], check=True)
        except subprocess.CalledProcessError as e:
            logger.exception("SHARx LBL generation failed")
            messagebox.showerror("Error", f"SHARx LBL generation failed: {e}")

    def epls_lbl(self):
        try:
            subprocess.run(["python", "epls_lbl.py"], check=True)
        except subprocess.CalledProcessError as e:
            logger.exception("EPLS LBL generation failed")
            messagebox.showerror("Error", f"EPLS LBL generation failed: {e}")

    def show_shared_log_viewer(self):
        import csv

        SHARED_LOG_PATH = os.path.expandvars(
            r"%OneDrive%/True Community - Data Analyst/Python Repricing Automation Program/Logs/audit_log.csv"
        )

        log_win = tk.Toplevel(self.root)
        log_win.title("Shared Audit Log Viewer")
        log_win.geometry("1000x600")

        filter_frame = tk.Frame(log_win)
        filter_frame.pack(fill="x")
        tk.Label(filter_frame, text="Search:").pack(side="left", padx=5)
        filter_entry = tk.Entry(filter_frame)
        filter_entry.pack(side="left", fill="x", expand=True, padx=5)

        text_area = scrolledtext.ScrolledText(log_win, width=150, height=30)
        text_area.pack(fill="both", expand=True)

        def refresh():
            try:
                with open(SHARED_LOG_PATH, "r", newline="", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    rows = list(reader)

                search_term = filter_entry.get().lower()
                filtered = (
                    [
                        row
                        for row in rows
                        if any(search_term in str(cell).lower() for cell in row)
                    ]
                    if search_term
                    else rows
                )

                text_area.delete(1.0, tk.END)
                for row in filtered:
                    text_area.insert(tk.END, " | ".join(row) + "\n")
            except Exception as e:
                text_area.insert(tk.END, f"[ERROR] Could not read shared log:\n{e}")

            log_win.after(5000, refresh)

    def _build_ui(self):
        # Title
        self.title_label = ctk.CTkLabel(
            self.root, text="Repricing Automation", font=("Cambria", 26, "bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w", pady=20, padx=20)

        # File & action buttons frame (move to row=2)
        self.button_frame = ctk.CTkFrame(self.root, fg_color=LIGHT_COLORS["grey_blue"])
        self.button_frame.grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=10, padx=10
        )

        # Headers
        file_name_title = ctk.CTkLabel(
            self.button_frame, text="File Name", font=font_select
        )
        file_name_title.grid(row=0, column=2, pady=10, padx=10)

        # Import File 1
        self.file1_button = ctk.CTkButton(
            self.button_frame,
            text="Import File Uploaded to Tool",
            command=self.import_file1,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.file1_button.grid(row=1, column=0, pady=10, padx=10, sticky="ew")
        self.file1_label = ctk.CTkLabel(self.button_frame, text="", width=350)
        self.file1_label.grid(row=1, column=2, pady=20, padx=10)

        # Import File 2
        self.file2_button = ctk.CTkButton(
            self.button_frame,
            text="Import File From Tool",
            command=self.import_file2,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.file2_button.grid(row=2, column=0, pady=10, padx=10, sticky="ew")
        self.file2_label = ctk.CTkLabel(self.button_frame, text="")
        self.file2_label.grid(row=2, column=2, pady=20, padx=10)

        # Select Template
        self.template_button = ctk.CTkButton(
            self.button_frame,
            text="Select Template File",
            command=self.import_template_file,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.template_button.grid(row=3, column=0, pady=10, padx=10, sticky="ew")
        self.template_label = ctk.CTkLabel(self.button_frame, text="")
        self.template_label.grid(row=3, column=2, pady=20, padx=10)
        if self.template_file_path:
            self.template_label.configure(
                text=os.path.basename(self.template_file_path), font=font_select
            )

        # Cancel, Logs, Theme buttons
        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self.cancel_process,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["button_red"],  # darker red
            text_color="#000000",  # black text
        )
        self.cancel_button.grid(row=4, column=0, pady=10, padx=10, sticky="ew")

        # View Logs button
        self.logs_button = ctk.CTkButton(
            self.button_frame,
            text="View Logs",
            command=self.show_log_viewer,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.logs_button.grid(row=4, column=1, pady=10, padx=10, sticky="ew")

        # Shared Log Button
        self.shared_log_button = ctk.CTkButton(
            self.button_frame,
            text="Shared Audit Log",
            command=self.show_shared_log_viewer,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.shared_log_button.grid(row=6, column=1, pady=10, padx=10, sticky="ew")

        # Toggle Dark Mode button
        self.toggle_theme_button = ctk.CTkButton(
            self.button_frame,
            text="Switch to Dark Mode",
            command=self.toggle_dark_mode,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.toggle_theme_button.grid(row=4, column=2, pady=10, padx=10, sticky="ew")

        # SHARx, EPLS LBL buttons and Start Repricing button
        self.sharx_lbl_button = ctk.CTkButton(
            self.button_frame,
            text="Generate SHARx LBL",
            command=self.sharx_lbl,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.sharx_lbl_button.grid(row=5, column=0, pady=10, padx=10, sticky="ew")
        self.epls_lbl_button = ctk.CTkButton(
            self.button_frame,
            text="Generate EPLS LBL",
            command=self.epls_lbl,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.epls_lbl_button.grid(row=5, column=1, pady=10, padx=10, sticky="ew")
        self.start_process_button = ctk.CTkButton(
            self.button_frame,
            text="Start Repricing",
            command=self.start_process_threaded,
            font=font_select,
            height=40,
            width=200,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.start_process_button.grid(row=5, column=2, pady=10, padx=10, sticky="ew")

        # Exit button (keep at bottom of button_frame)
        self.exit_button = ctk.CTkButton(
            self.button_frame,
            text="Exit",
            command=self.root.quit,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["button_red"],  # darker red
            text_color="#000000",  # black text
        )
        self.exit_button.grid(row=6, column=2, pady=10, padx=10, sticky="ew")

        # Notes (move to row=3)
        self.notes_frame = ctk.CTkFrame(self.root, fg_color=LIGHT_COLORS["grey_blue"])
        self.notes_frame.grid(
            row=3, column=0, columnspan=4, sticky="ew", pady=10, padx=10
        )
        notes = ctk.CTkLabel(
            self.notes_frame,
            text=(
                "Note:\n\n"
                "Ensure FormularyTier is set before running disruption.\n"
                "Close any open Excel instances.\n"
                "Keep template name as _Rx Repricing_wf until done."
            ),
            font=font_select,
            justify="left",
        )
        notes.pack(padx=20, pady=10)

        # Disruption type selector frame (now just below notes) with individual buttons
        self.dis_frame = ctk.CTkFrame(self.root, fg_color=LIGHT_COLORS["grey_blue"])
        self.dis_frame.grid(
            row=4, column=0, columnspan=4, sticky="ew", pady=10, padx=10
        )

        # Individual disruption buttons (removed Full Claims File)
        disruption_labels = [
            "Tier Disruption",
            "B/G Disruption",
            "OpenMDF (Tier)",
            "OpenMDF (B/G)",
        ]
        for idx, label in enumerate(disruption_labels):
            btn = ctk.CTkButton(
                self.dis_frame,
                text=label,
                command=lambda label_text=label: self.start_disruption(label_text),
                font=font_select,
                height=40,
                fg_color=LIGHT_COLORS["mint"],
                text_color="#000000",
            )
            btn.grid(row=0, column=idx, padx=10, pady=10, sticky="ew")

        # Progress bar frame (ensure it is always below the disruption buttons)
        self.prog_frame = ctk.CTkFrame(self.root, fg_color=LIGHT_COLORS["grey_blue"])
        self.prog_frame.grid(
            row=5, column=0, columnspan=4, sticky="ew", pady=10, padx=10
        )
        self.progress_bar = ctk.CTkProgressBar(
            self.prog_frame, orientation="horizontal", mode="determinate"
        )
        self.progress_bar.set(self.progress_var.get())
        self.progress_bar.pack(padx=10, pady=(10, 5), fill="x")
        self.progress_label = ctk.CTkLabel(
            self.prog_frame, textvariable=self.progress_label_var
        )
        self.progress_label.pack(padx=10, pady=(0, 10), anchor="w")

        # Progress bar frame (now below dis_frame)
        self.prog_frame = ctk.CTkFrame(self.root, fg_color=LIGHT_COLORS["grey_blue"])
        self.prog_frame.grid(
            row=5, column=0, columnspan=3, sticky="ew", pady=10, padx=10
        )
        self.progress_bar = ctk.CTkProgressBar(
            self.prog_frame, orientation="horizontal", mode="determinate"
        )
        self.progress_bar.set(self.progress_var.get())
        self.progress_bar.pack(padx=10, pady=(10, 5), fill="x")
        self.progress_label = ctk.CTkLabel(
            self.prog_frame, textvariable=self.progress_label_var
        )
        self.progress_label.pack(padx=10, pady=(0, 10), anchor="w")

        # Import File 1
        self.file1_button = ctk.CTkButton(
            self.button_frame,
            text="Import File Uploaded to Tool",
            command=self.import_file1,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.file1_button.grid(row=1, column=0, pady=10, padx=10, sticky="ew")
        self.file1_label = ctk.CTkLabel(self.button_frame, text="", width=350)
        self.file1_label.grid(row=1, column=2, pady=20, padx=10)

        # Import File 2
        self.file2_button = ctk.CTkButton(
            self.button_frame,
            text="Import File From Tool",
            command=self.import_file2,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.file2_button.grid(row=2, column=0, pady=10, padx=10, sticky="ew")
        self.file2_label = ctk.CTkLabel(self.button_frame, text="")
        self.file2_label.grid(row=2, column=2, pady=20, padx=10)

        # Select Template
        self.template_button = ctk.CTkButton(
            self.button_frame,
            text="Select Template File",
            command=self.import_template_file,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.template_button.grid(row=3, column=0, pady=10, padx=10, sticky="ew")
        self.template_label = ctk.CTkLabel(self.button_frame, text="")
        self.template_label.grid(row=3, column=2, pady=20, padx=10)
        if self.template_file_path:
            self.template_label.configure(
                text=os.path.basename(self.template_file_path), font=font_select
            )

        # Cancel, Logs, Theme buttons
        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self.cancel_process,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["button_red"],  # darker red
            text_color="#000000",  # black text
        )
        self.cancel_button.grid(row=4, column=0, pady=10, padx=10, sticky="ew")

        # View Logs button
        self.logs_button = ctk.CTkButton(
            self.button_frame,
            text="View Logs",
            command=self.show_log_viewer,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.logs_button.grid(row=4, column=1, pady=10, padx=10, sticky="ew")

        # Shared Log Button
        self.shared_log_button = ctk.CTkButton(
            self.button_frame,
            text="Shared Audit Log",
            command=self.show_shared_log_viewer,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.shared_log_button.grid(row=6, column=1, pady=10, padx=10, sticky="ew")

        # Toggle Dark Mode button
        self.toggle_theme_button = ctk.CTkButton(
            self.button_frame,
            text="Switch to Dark Mode",
            command=self.toggle_dark_mode,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.toggle_theme_button.grid(row=4, column=2, pady=10, padx=10, sticky="ew")

        # SHARx and EPLS LBL buttons
        self.sharx_lbl_button = ctk.CTkButton(
            self.button_frame,
            text="Generate SHARx LBL",
            command=self.sharx_lbl,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.sharx_lbl_button.grid(row=5, column=0, pady=10, padx=10, sticky="ew")
        self.epls_lbl_button = ctk.CTkButton(
            self.button_frame,
            text="Generate EPLS LBL",
            command=self.epls_lbl,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.epls_lbl_button.grid(row=5, column=1, pady=10, padx=10, sticky="ew")
        self.start_process_button = ctk.CTkButton(
            self.button_frame,
            text="Start Repricing",
            command=self.start_process_threaded,
            font=font_select,
            height=40,
            width=200,
            fg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.start_process_button.grid(row=5, column=2, pady=10, padx=10, sticky="ew")

        # Exit button (keep at bottom of button_frame)
        self.exit_button = ctk.CTkButton(
            self.button_frame,
            text="Exit",
            command=self.root.quit,
            font=font_select,
            height=40,
            fg_color=LIGHT_COLORS["button_red"],  # darker red
            text_color="#000000",  # black text
        )
        self.exit_button.grid(row=6, column=2, pady=10, padx=10, sticky="ew")

        # Apply theme colors after all widgets are created
        self.apply_theme_colors(LIGHT_COLORS)

    # Removed openmdf_tier and obsolete combobox/old disruption UI. All disruption actions now use run_disruption via the new buttons.

    # File import methods
    def import_file1(self):
        file_path = filedialog.askopenfilename(
            title="Select File Uploaded to Tool",
            filetypes=[
                ("All files", "*.*"),
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
            ],
        )
        if file_path:
            self.file1_path = file_path
            self.file1_label.configure(
                text=os.path.basename(file_path), font=font_select
            )
            self.check_template(file_path)
            write_shared_log("File1 imported", file_path)
        if not file_path:
            return  # User cancelled, do nothing
        df = pd.read_csv(file_path)
        if "GrossCost" in df.columns:
            if df["GrossCost"].isna().all() or (df["GrossCost"] == 0).all():
                messagebox.showinfo(
                    "Template Selection",
                    "The GrossCost column is blank or all zero. Please use the Blind template.",
                )
            else:
                messagebox.showinfo(
                    "Template Selection",
                    "The GrossCost column contains data. Please use the Standard template.",
                )

    def import_file2(self):
        file_path = filedialog.askopenfilename(
            title="Select File From Tool",
            filetypes=[
                ("All files", "*.*"),
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
            ],
        )
        if file_path:
            self.file2_path = file_path
            self.file2_label.configure(
                text=os.path.basename(file_path), font=font_select
            )
            write_shared_log("File2 imported", file_path)

    def import_template_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Template File", filetypes=[("Excel files", "*.xlsx")]
        )
        if file_path:
            self.template_file_path = file_path
            self.template_label.configure(
                text=os.path.basename(file_path), font=font_select
            )
            write_shared_log("Template file imported", file_path)
        if self.template_file_path:
            self.template_label.configure(
                text=os.path.basename(self.template_file_path), font=font_select
            )

    # Logging and notification methods
    # Removed duplicate write_audit_log method to resolve method name conflict.

    # Cancel during repricing
    def cancel_process(self):
        logger.info("Cancel pressed")
        write_shared_log("Process cancelled", "")
        messagebox.showinfo("Cancelled", "Repricing cancellation requested.")

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

    def toggle_dark_mode(self):
        current = ctk.get_appearance_mode().lower()

        if current == "light":
            # Switch *into* Dark mode
            ctk.set_appearance_mode("dark")
            self.apply_theme_colors(DARK_COLORS)
            # Now the button’s job is to switch *back* to Light
            self.toggle_theme_button.configure(text="Switch to Light Mode")

        else:
            # Switch *into* Light mode
            ctk.set_appearance_mode("light")
            self.apply_theme_colors(LIGHT_COLORS)
            # Now the button’s job is to switch *into* Dark
            self.toggle_theme_button.configure(text="Switch to Dark Mode")

    def update_progress(self, value=None, message=None):
        """
        Update the progress bar and label. If value is None, switch to indeterminate mode.
        If value is a float between 0 and 1, use determinate mode.
        Optionally, update the label with a custom message.
        """

        def do_update():
            if value is None:
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start()
                if message:
                    self.progress_label_var.set(message)
                else:
                    self.progress_label_var.set("Processing... (unknown duration)")
            else:
                if self.progress_bar.cget("mode") != "determinate":
                    self.progress_bar.stop()
                    self.progress_bar.configure(mode="determinate")
                self.progress_var.set(value)
                self.progress_bar.set(value)
                if message:
                    self.progress_label_var.set(message)
                else:
                    percent = int(value * 100)
                    elapsed = time.time() - self.start_time if self.start_time else 0
                    est = int((elapsed / value) * (1 - value)) if value > 0 else 0
                    self.progress_label_var.set(
                        f"Progress: {percent}% | Est. {est}s left"
                    )
            self.root.update_idletasks()  # Force UI update for real-time progress

        if threading.current_thread() is threading.main_thread():
            do_update()
        else:
            self.root.after(0, do_update)

    def write_audit_log(self, file1, file2, status):
        entry = [datetime.now().isoformat(), str(file1), str(file2), status]
        write_header = not AUDIT_LOG.exists()
        with open(AUDIT_LOG, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if write_header:
                writer.writerow(["Timestamp", "File1", "File2", "Status"])
            writer.writerow(entry)

    def show_log_viewer(self):
        log_win = tk.Toplevel(self.root)
        log_win.title("Live Log Viewer")
        text_area = scrolledtext.ScrolledText(log_win, width=100, height=30)
        text_area.pack(fill="both", expand=True)

        def update_logs():
            with open("repricing_log.log", "r") as f:
                text_area.delete(1.0, tk.END)
                text_area.insert(tk.END, f.read())
            log_win.after(3000, update_logs)

        update_logs()

    # Disruption and process methods
    # Removed select_disruption_type method since disruption_type_combobox does not exist.

    # Start disruption based on selected type
    def start_disruption(self, disruption_type=None):
        # If called from a button, disruption_type should be passed as an argument
        if disruption_type is None:
            disruption_type = self.selected_disruption_type.get().strip()
        program_files = {
            "Tier Disruption": "tier_disruption.py",
            "B/G Disruption": "bg_disruption.py",
            "OpenMDF (Tier)": "openmdf_tier.py",
            "OpenMDF (B/G)": "openmdf_bg.py",
            "Full Claims File": "full_claims.py",
        }
        if disruption_type in program_files:
            program_name = program_files[disruption_type]
            try:
                args = ["python", program_name]
                if self.template_file_path:
                    args.append(str(self.template_file_path))
                # Use multiprocessing to run the disruption script
                disruption_process = multiprocessing.Process(
                    target=subprocess.run, args=(args,), kwargs={"check": True}
                )
                disruption_process.start()
                messagebox.showinfo(
                    "Success",
                    f"{disruption_type} disruption started in a separate process.",
                )
            except Exception as e:
                logger.exception(
                    f"Failed to start {program_name} in a separate process"
                )
                messagebox.showerror(
                    "Error", f"{disruption_type} disruption failed: {e}"
                )

    def start_process_threaded(self):
        threading.Thread(target=self._start_process_internal).start()
        write_shared_log("Repricing process started", "")

    def finish_notification(self):
        if hasattr(notification, "notify") and callable(notification.notify):
            notification.notify(
                title="Repricing Automation",
                message="Batch processing completed.",
                timeout=5,
            )
        write_shared_log("Batch processing completed", "")
        messagebox.showinfo("Completed", "Batch processing finished!")

    # Repricing workflow methods
    def paste_into_template(self, processed_file):
        def run_in_background():
            try:
                import xlwings as xw
                import time

                start_time = time.time()

                self.root.after(
                    0,
                    lambda: self.update_progress(
                        None, "Preparing to paste into template..."
                    ),
                )

                if not self.template_file_path:
                    raise ValueError("Template file path is not set.")

                # Load and prep data
                df = pd.read_excel(processed_file)
                df = self.format_dataframe(df)
                data = df.values
                nrows, ncols = data.shape

                # Prepare paths
                template = self.template_file_path
                backup_name = Path(template).stem + BACKUP_SUFFIX
                backup_path = Path.cwd() / backup_name
                output_path = Path.cwd() / "_Rx Repricing_wf.xlsx"

                # Backup original template
                shutil.copy(template, backup_path)
                logger.info(f"Template backed up to {backup_path}")
                self.root.after(
                    0, lambda: self.update_progress(0.92, "Opening Excel template...")
                )

                # Remove old output if it exists
                if output_path.exists():
                    try:
                        os.remove(output_path)
                    except PermissionError:
                        raise RuntimeError(
                            f"Cannot overwrite {output_path} — please close it in Excel."
                        )

                shutil.copy(template, output_path)

                # Start Excel session
                app = xw.App(visible=False)
                wb = app.books.open(str(output_path))
                ws = wb.sheets["Claims Table"]

                # Batch read formulas
                formulas = ws.range((2, 1), (nrows + 1, ncols)).formula
                data_to_write = []

                for i in range(nrows):
                    row = []
                    for j in range(ncols):
                        if formulas[i][j] == "":
                            row.append(data[i][j])
                        else:
                            row.append(None)
                    data_to_write.append(row)

                    if i % 250 == 0 or i == nrows - 1:
                        percent = 0.94 + 0.04 * (i / max(1, nrows))
                        msg = f"Pasting row {i + 1} of {nrows}..."
                        self.root.after(
                            0, lambda v=percent, m=msg: self.update_progress(v, m)
                        )

                # Paste values
                ws.range((2, 1), (nrows + 1, ncols)).value = data_to_write

                # Save and close
                wb.save()
                wb.close()
                app.quit()

                elapsed = time.time() - start_time
                msg = f"Template updated successfully in {elapsed:.2f} seconds."
                logger.info(msg)
                self.root.after(0, lambda: self.update_progress(1.0, msg))
                self.root.after(0, lambda: self.show_toast(msg))
                # Show a Tkinter notification after pasting is complete
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Template Update Complete",
                        "Pasting into the template is complete. You may now review the updated file.",
                    ),
                )

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
        datetime_columns = df.select_dtypes(include=["datetime64"]).columns
        for col in datetime_columns:
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
        return df.fillna("")

    def show_toast(self, message, duration=3000):
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.configure(bg="black")

        # Position bottom-right
        self.root.update_idletasks()
        screen_width = toast.winfo_screenwidth()
        screen_height = toast.winfo_screenheight()
        x = screen_width - 320
        y = screen_height - 100
        toast.geometry(f"300x50+{x}+{y}")

        label = tk.Label(
            toast, text=message, bg="black", fg="white", font=("Arial", 11)
        )
        label.pack(fill="both", expand=True)

        toast.after(duration, toast.destroy)

    def start_process(self):
        threading.Thread(target=self._start_process_internal).start()
        write_shared_log("Repricing process started", "")

    def validate_merge_inputs(self):
        # Check if both file paths are set and files exist
        if not self.file1_path or not self.file2_path:
            messagebox.showerror("Error", "Both input files must be selected.")
            return False
        if not os.path.isfile(self.file1_path):
            messagebox.showerror("Error", f"File not found: {self.file1_path}")
            return False
        if not os.path.isfile(self.file2_path):
            messagebox.showerror("Error", f"File not found: {self.file2_path}")
            return False
        return True

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
        try:
            self.update_progress(0.55)
            open("repricing_log.log", "w").close()
            logging.basicConfig(
                filename="repricing_log.log",
                level=logging.INFO,
                format="%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            logging.info("Starting merged file processing")
            df = pd.read_excel(file_path)
            logging.info(f"Loaded {len(df)} records from {file_path}")

            self.update_progress(0.60)

            for col in [
                "DATEFILLED",
                "SOURCERECORDID",
                "QUANTITY",
                "DAYSUPPLY",
                "NDC",
                "MemberID",
                "Drug Name",
                "Pharmacy Name",
                "Total AWP (Historical)",
            ]:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")

            df = df.sort_values(by=["DATEFILLED", "SOURCERECORDID"], ascending=True)
            df["Logic"] = ""
            df["RowID"] = np.arange(len(df))

            self.update_progress(0.65)

            # Multiprocessing with mp_helpers.worker
            from modules import mp_helpers

            num_workers = min(4, max(1, multiprocessing.cpu_count() // 2))
            df_blocks = np.array_split(df, num_workers)
            out_queue = multiprocessing.Queue()
            processes = []
            for block in df_blocks:
                p = multiprocessing.Process(
                    target=mp_helpers.worker, args=(block, out_queue)
                )
                p.start()
                processes.append(p)
            results = [out_queue.get() for _ in processes]
            for p in processes:
                p.join()
            df = pd.concat(results)

            self.update_progress(0.75)

            df_sorted = pd.concat([df[df["Logic"] == ""], df[df["Logic"] == "OR"]])

            # All outputs should be saved in the current working directory (where merged_file is saved)
            output_dir = Path.cwd()
            output_file = output_dir / "merged_file_with_OR.xlsx"
            row_mapping = {
                row["RowID"]: i + 2 for i, (_, row) in enumerate(df_sorted.iterrows())
            }
            excel_rows_to_highlight = [
                row_mapping[rid] for rid in [] if rid in row_mapping
            ]  # Placeholder

            df_sorted.drop(columns=["RowID"], inplace=True, errors="ignore")
            # --- TEMP: Save to Parquet for large DataFrames before Excel export ---
            try:
                parquet_path = output_dir / "merged_file_with_OR.parquet"
                df_sorted.drop_duplicates().to_parquet(parquet_path, index=False)
                logger.info(f"Saved intermediate Parquet file: {parquet_path}")
            except Exception as e:
                logger.warning(f"Could not save Parquet: {e}")
            # --- Excel export ---
            df_sorted.drop_duplicates().to_excel(output_file, index=False)

            # --- Get opportunity name from second column of file1_path ---
            opportunity_name = "claims detail PCU"
            try:
                # Try reading as Excel first, fallback to CSV
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
            # -------------------------------------------------------------

            # Save as CSV in output_dir
            csv_path = output_dir / f"{opportunity_name} Claim Detail.csv"
            df_sorted.drop_duplicates().to_csv(csv_path, index=False)

            unmatched_path = output_dir / "unmatched_reversals.txt"
            with open(unmatched_path, "w") as f:
                f.write(",".join(map(str, excel_rows_to_highlight)))

            self.update_progress(0.80)

            self.highlight_unmatched_reversals(output_file)
            self.update_progress(0.85)

            messagebox.showinfo(
                "Success", f"Processing complete. File saved as {output_file}"
            )
            self.paste_into_template(output_file)
            self.update_progress(0.90)

            # DO NOT call LBL scripts here. LBL scripts are only called from run_disruption or the dedicated LBL buttons.

        except Exception as e:
            logger.error(f"Error processing merged file: {e}")
            messagebox.showerror("Error", f"Processing failed: {e}")

    def highlight_unmatched_reversals(self, excel_file):
        """
        Highlights unmatched reversals in the given Excel file.
        This is a placeholder implementation. You can update this method to highlight specific rows as needed.
        """
        try:
            wb = load_workbook(excel_file)
            ws = wb.active
            # Example: highlight the first row (after header) as unmatched
            fill = PatternFill(
                start_color="FFFF00", end_color="FFFF00", fill_type="solid"
            )
            # You can load row numbers from unmatched_reversals.txt if needed
            if ws is not None and os.path.exists("unmatched_reversals.txt"):
                with open("unmatched_reversals.txt", "r") as f:
                    rows = f.read().strip().split(",")
                    for row_str in rows:
                        if row_str.isdigit():
                            row_num = int(row_str)
                            if 1 <= row_num <= ws.max_row:
                                row = ws[row_num]
                                for cell in row:
                                    cell.fill = fill
            wb.save(excel_file)
            logger.info(f"Highlighted unmatched reversals in {excel_file}")
        except Exception as e:
            logger.error(f"Failed to highlight unmatched reversals: {e}")


warnings.filterwarnings("ignore", category=FutureWarning, message=".*swapaxes.*")
warnings.filterwarnings("ignore", category=FutureWarning, message=".*swapaxes.*")


def process_logic_block(df_block):
    # Vectorized numpy logic to mark 'OR' in 'Logic' for reversals with matching claims, and mark unmatched reversals as 'OR' as well
    arr = df_block.to_numpy()
    col_idx = {col: i for i, col in enumerate(df_block.columns)}
    qty = arr[:, col_idx["QUANTITY"]].astype(float)
    is_reversal = qty < 0
    is_claim = qty > 0
    ndc = arr[:, col_idx["NDC"]].astype(str)
    member = arr[:, col_idx["MemberID"]].astype(str)
    datefilled = pd.to_datetime(arr[:, col_idx["DATEFILLED"]], errors="coerce")
    abs_qty = np.abs(qty)
    if np.any(is_reversal):
        rev_idx = np.where(is_reversal)[0]
        claim_idx = (
            np.where(is_claim)[0] if np.any(is_claim) else np.array([], dtype=int)
        )
        for i in rev_idx:
            found_match = False
            if claim_idx.size > 0:
                matches = (
                    (ndc[claim_idx] == ndc[i])
                    & (member[claim_idx] == member[i])
                    & (abs_qty[claim_idx] == abs_qty[i])
                )
                date_diffs = np.abs((datefilled[claim_idx] - datefilled[i]).days)
                matches &= date_diffs <= 30
                if np.any(matches):
                    arr[i, col_idx["Logic"]] = "OR"
                    arr[claim_idx[matches][0], col_idx["Logic"]] = "OR"
                    found_match = True
            if not found_match:
                arr[i, col_idx["Logic"]] = "OR"
    return pd.DataFrame(arr, columns=df_block.columns)


if __name__ == "__main__":
    ctk.set_appearance_mode("light")  # Start in light mode
    root = ctk.CTk()  # or tk.Tk() if not using customtkinter
    app = App(root)
    root.mainloop()
