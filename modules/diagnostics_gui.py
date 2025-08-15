import getpass
import json
import os
import tkinter as tk
import urllib.request
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from modules.diagnostic_tool import DiagnosticTool


class DiagnosticsGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Diagnostics Report")
        self.geometry("650x540")
        self.resizable(False, False)
        self.create_widgets()
        self.run_diagnostics()

    def create_widgets(self):
        self.header = ctk.CTkLabel(
            self, text="System Diagnostics", font=("Arial", 22, "bold")
        )
        self.header.pack(pady=10)

        self.report_box = ctk.CTkTextbox(
            self, width=560, height=320, font=("Consolas", 12)
        )
        self.report_box.pack(pady=10)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)

        self.refresh_btn = ctk.CTkButton(
            btn_frame, text="Re-run Diagnostics", command=self.run_diagnostics
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=10)

        self.report_issue_btn = ctk.CTkButton(
            btn_frame, text="Report an Issue", command=self.open_report_issue_popup
        )
        self.report_issue_btn.pack(side=tk.LEFT, padx=10)

        self.update_btn = ctk.CTkButton(
            btn_frame, text="Check for Updates", command=self.check_for_updates
        )
        self.update_btn.pack(side=tk.LEFT, padx=10)

        # Dark/Light mode toggle
        mode_frame = ctk.CTkFrame(self)
        mode_frame.pack(pady=5)
        self.mode_var = tk.StringVar(value=ctk.get_appearance_mode())
        self.mode_toggle = ctk.CTkSwitch(
            mode_frame,
            text="Dark Mode",
            command=self.toggle_mode,
            variable=self.mode_var,
            onvalue="Dark",
            offvalue="Light",
        )
        self.mode_toggle.pack(side=tk.LEFT, padx=10)
        if ctk.get_appearance_mode() == "Dark":
            self.mode_toggle.select()

    def open_report_issue_popup(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Report an Issue")
        popup.geometry("420x370")
        popup.resizable(False, False)

        # Category dropdown
        cat_label = ctk.CTkLabel(popup, text="Category/Type:", font=("Arial", 12))
        cat_label.pack(pady=(10, 0))
        categories = ["Bug", "Data Issue", "Feature Request", "Performance", "Other"]
        cat_var = tk.StringVar(value=categories[0])
        cat_dropdown = ctk.CTkOptionMenu(popup, variable=cat_var, values=categories)
        cat_dropdown.pack(pady=(0, 10))

        label = ctk.CTkLabel(popup, text="Describe the issue:", font=("Arial", 14))
        label.pack(pady=5)

        text_box = ctk.CTkTextbox(popup, width=360, height=150, font=("Consolas", 12))
        text_box.pack(pady=5)

        def submit_issue():
            user_name = getpass.getuser()
            user_report = text_box.get("1.0", tk.END).strip()
            category = cat_var.get()
            if user_report:
                self.save_issue_report(user_report, user_name, category)
                popup.destroy()
                messagebox.showinfo(
                    "Submitted", f"Your issue has been saved as {user_name}."
                )
            else:
                messagebox.showerror("Error", "Please enter a description.")

        submit_btn = ctk.CTkButton(popup, text="Submit", command=submit_issue)
        submit_btn.pack(pady=10)

    def save_issue_report(self, user_report, user_name, category):
        # Load diagnostic_reports path from config/file_paths.json
        try:
            with open(os.path.join("config", "file_paths.json"), "r") as f:
                paths = json.load(f)
            diag_dir = paths.get("diagnostic_reports")
            # Expand %OneDrive% if present
            if diag_dir and "%OneDrive%" in diag_dir:
                onedrive = os.environ.get("OneDrive")
                if onedrive:
                    diag_dir = diag_dir.replace("%OneDrive%", onedrive)
            if not diag_dir:
                raise Exception("diagnostic_reports path not found in config.")
            diag_dir = os.path.expanduser(diag_dir)
            Path(diag_dir).mkdir(parents=True, exist_ok=True)
            # Create unique filename
            timestamp = self.get_timestamp().replace(":", "-").replace(" ", "_")
            filename = f"report_{user_name}_{timestamp}.txt"
            file_path = os.path.join(diag_dir, filename)
            # Write report
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("Diagnostics GUI - User Issue Report\n")
                f.write(f"From: {user_name}\n")
                f.write(f"Category: {category}\n")
                f.write(f"Timestamp: {self.get_timestamp()}\n\n")
                f.write(f"Report:\n{user_report}\n")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save report: {e}")

    def check_for_updates(self):
        # Example: check a version file on GitHub or a URL
        current_version = "1.0.0"
        version_url = "https://raw.githubusercontent.com/UWDataTrx/UW-Automation-Program/main/VERSION.txt"
        try:
            with urllib.request.urlopen(version_url, timeout=5) as response:
                latest_version = response.read().decode().strip()
            if latest_version > current_version:
                messagebox.showinfo(
                    "Update Available",
                    f"A new version ({latest_version}) is available.",
                )
            else:
                messagebox.showinfo("Up to Date", "You are using the latest version.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check for updates: {e}")

    def toggle_mode(self):
        # Toggle between dark and light mode
        new_mode = "Dark" if self.mode_var.get() == "Light" else "Light"
        ctk.set_appearance_mode(new_mode)
        self.mode_var.set(new_mode)

    def get_timestamp(self):
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def run_diagnostics(self):
        self.report_box.delete("1.0", tk.END)
        # Run the diagnostic tool and get the report
        tool = DiagnosticTool()
        tool.run_diagnosis()
        report = "\n".join(tool.report_lines)
        self.report_box.insert(tk.END, report)

    # generate_report is no longer needed; using DiagnosticTool for full diagnostics


if __name__ == "__main__":
    app = DiagnosticsGUI()
    app.mainloop()
