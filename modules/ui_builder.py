import customtkinter as ctk
from tkinter import messagebox
import getpass
import sys
from pathlib import Path
# Ensure project root is in sys.path before importing project_settings
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from project_settings import PROJECT_ROOT  # noqa: E402
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from ui.ui_components import UIFactory, LIGHT_COLORS, DARK_COLORS  # noqa: E402
from config.app_config import DisruptionConfig, AppConstants  # noqa: E402


class UIBuilder:
    """Handles the construction of the main application UI."""

    def __init__(self, app_instance):
        self.app = app_instance

    def build_complete_ui(self):
        """Build the complete user interface."""
        self._setup_window()
        self._build_ui_components()
        self._setup_default_template()
        self._show_welcome_message()

    def _setup_window(self):
        """Configure the main window properties."""
        self.app.root.title("Reprice Automation")
        # Use bg_color for CTk root window if fg_color is not supported
        try:
            self.app.root.configure(bg_color=LIGHT_COLORS["dark_blue"])
        except Exception:
            # Fallback for standard Tk root
            self.app.root.configure(bg=LIGHT_COLORS["dark_blue"])
        self.app.root.resizable(True, True)
        self.app.root.geometry("900x900")

    def _build_ui_components(self):
        """Build all UI components."""
        self._create_title()
        self._create_button_frame()
        self._create_notes_frame()
        self._create_disruption_frame()
        self._create_progress_frame()

    def _create_title(self):
        """Create the title label."""
        self.app.title_label = ctk.CTkLabel(
            self.app.root, text="Repricing Automation", font=("Cambria", 26, "bold")
        )
        self.app.title_label.grid(row=0, column=0, sticky="w", pady=20, padx=20)

    def _create_button_frame(self):
        """Create the main button frame with all action buttons."""
        self.app.button_frame = UIFactory.create_standard_frame(self.app.root)
        self.app.button_frame.grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=10, padx=10
        )

        # Headers
        file_name_title = UIFactory.create_standard_label(
            self.app.button_frame, "File Name"
        )
        file_name_title.grid(row=0, column=2, pady=10, padx=10)

        # Create sub-components
        self._create_file_import_buttons()
        self._create_action_buttons()
        self._create_process_buttons()

    def _create_file_import_buttons(self):
        """Create file import buttons and labels."""
        # Import File 1
        self.app.file1_button = UIFactory.create_standard_button(
            self.app.button_frame, "Import File Uploaded to Tool", self.app.import_file1
        )
        self.app.file1_button.grid(row=1, column=0, pady=10, padx=10, sticky="ew")
        self.app.file1_label = UIFactory.create_standard_label(
            self.app.button_frame, "", width=350
        )
        self.app.file1_label.grid(row=1, column=2, pady=20, padx=10)

        # Import File 2
        self.app.file2_button = UIFactory.create_standard_button(
            self.app.button_frame, "Import File From Tool", self.app.import_file2
        )
        self.app.file2_button.grid(row=2, column=0, pady=10, padx=10, sticky="ew")
        self.app.file2_label = UIFactory.create_standard_label(
            self.app.button_frame, ""
        )
        self.app.file2_label.grid(row=2, column=2, pady=20, padx=10)

        # Select Template
        self.app.template_button = UIFactory.create_standard_button(
            self.app.button_frame, "Select Template File", self.app.import_template_file
        )
        self.app.template_button.grid(row=3, column=0, pady=10, padx=10, sticky="ew")
        self.app.template_label = UIFactory.create_standard_label(
            self.app.button_frame, ""
        )
        self.app.template_label.grid(row=3, column=2, pady=20, padx=10)

    def _create_action_buttons(self):
        """Create action buttons (cancel, logs, theme)."""
        # Cancel button
        self.app.cancel_button = UIFactory.create_red_button(
            self.app.button_frame, "Cancel", self.app.cancel_process
        )
        self.app.cancel_button.grid(row=4, column=0, pady=10, padx=10, sticky="ew")

        # View Logs button
        self.app.logs_button = UIFactory.create_standard_button(
            self.app.button_frame, "View Logs", self.app.show_log_viewer
        )
        self.app.logs_button.grid(row=4, column=1, pady=10, padx=10, sticky="ew")

        # Toggle Dark Mode button
        self.app.toggle_theme_button = UIFactory.create_standard_button(
            self.app.button_frame, "Switch to Dark Mode", self.toggle_dark_mode
        )
        self.app.toggle_theme_button.grid(
            row=4, column=2, pady=10, padx=10, sticky="ew"
        )

        # Audit Log Button
        self.app.shared_log_button = UIFactory.create_standard_button(
            self.app.button_frame, "Shared Audit Log", self.app.show_shared_log_viewer
        )
        self.app.shared_log_button.grid(row=6, column=1, pady=10, padx=10, sticky="ew")

        # Exit button
        self.app.exit_button = UIFactory.create_red_button(
            self.app.button_frame, "Exit", self.app.on_closing
        )
        self.app.exit_button.grid(row=6, column=2, pady=10, padx=10, sticky="ew")

    def _create_process_buttons(self):
        """Create processing and LBL generation buttons."""
        # SHARx LBL button
        self.app.sharx_lbl_button = UIFactory.create_standard_button(
            self.app.button_frame, "Generate SHARx LBL", self.app.sharx_lbl
        )
        self.app.sharx_lbl_button.grid(row=5, column=0, pady=10, padx=10, sticky="ew")

        # EPLS LBL button
        self.app.epls_lbl_button = UIFactory.create_standard_button(
            self.app.button_frame, "Generate EPLS LBL", self.app.epls_lbl
        )
        self.app.epls_lbl_button.grid(row=5, column=1, pady=10, padx=10, sticky="ew")

        # Start Process button
        self.app.start_process_button = ctk.CTkButton(
            self.app.button_frame,
            text="Start Repricing",
            command=self.app.start_process_threaded,
            font=("Cambria", 20, "bold"),
            height=40,
            width=200,
            bg_color=LIGHT_COLORS["mint"],
            text_color="#000000",
        )
        self.app.start_process_button.grid(
            row=5, column=2, pady=10, padx=10, sticky="ew"
        )

    def _create_notes_frame(self):
        """Create the notes frame with important information."""
        self.app.notes_frame = UIFactory.create_standard_frame(self.app.root)
        self.app.notes_frame.grid(
            row=3, column=0, columnspan=4, sticky="ew", pady=10, padx=10
        )
        notes = UIFactory.create_standard_label(
            self.app.notes_frame, AppConstants.NOTES_TEXT
        )
        notes.configure(justify="left")
        notes.pack(padx=20, pady=10)

    def _create_disruption_frame(self):
        """Create the disruption type selector frame."""
        self.app.dis_frame = UIFactory.create_standard_frame(self.app.root)
        self.app.dis_frame.grid(
            row=4, column=0, columnspan=4, sticky="ew", pady=10, padx=10
        )

        # Create disruption buttons using configuration
        disruption_labels = DisruptionConfig.get_disruption_labels()
        for idx, label in enumerate(disruption_labels):
            btn = UIFactory.create_standard_button(
                self.app.dis_frame,
                label,
                lambda label_text=label: self.app.start_disruption(label_text),
            )
            btn.grid(row=0, column=idx, padx=10, pady=10, sticky="ew")

    def _create_progress_frame(self):
        """Create the progress bar frame."""
        self.app.prog_frame = UIFactory.create_standard_frame(self.app.root)
        self.app.prog_frame.grid(
            row=5, column=0, columnspan=4, sticky="ew", pady=10, padx=10
        )
        self.app.progress_bar = ctk.CTkProgressBar(
            self.app.prog_frame, orientation="horizontal", mode="determinate"
        )
        self.app.progress_bar.set(self.app.progress_var.get())
        self.app.progress_bar.pack(padx=10, pady=(10, 5), fill="x")
        self.app.progress_label = ctk.CTkLabel(
            self.app.prog_frame, textvariable=self.app.progress_label_var
        )
        self.app.progress_label.pack(padx=10, pady=(0, 10), anchor="w")

    def _setup_default_template(self):
        """Set up default template if it exists using pathlib."""
        default_template = Path("_Rx Repricing_wf.xlsx").resolve()
        if default_template.exists():
            self.app.template_file_path = str(default_template)
            if hasattr(self.app, "template_label"):
                self.app.template_label.configure(text=default_template.name)
        else:
            self.app.template_file_path = None

    def _show_welcome_message(self):
        """Show a personalized welcome message with a random joke and emoji."""
        user = getpass.getuser()
        welcome_messages = AppConstants.WELCOME_MESSAGES

        msg = welcome_messages.get(
            user, f"Welcome, {user}! Ready to use the Repricing Automation Toolkit?"
        )

        # Show after UI is built (no joke or emoji)
        self.app.root.after(500, lambda: messagebox.showinfo("Welcome", msg))

    def toggle_dark_mode(self):
        """Toggle between light and dark modes."""
        current = ctk.get_appearance_mode().lower()

        if current == "light":
            self._switch_to_dark_mode()
        else:
            self._switch_to_light_mode()

    def _switch_to_dark_mode(self):
        """Switch to dark mode."""
        ctk.set_appearance_mode("dark")
        self.app.apply_theme_colors(DARK_COLORS)
        if self.app.toggle_theme_button:
            self.app.toggle_theme_button.configure(text="Switch to Light Mode")

    def _switch_to_light_mode(self):
        """Switch to light mode."""
        ctk.set_appearance_mode("light")
        self.app.apply_theme_colors(LIGHT_COLORS)
        if self.app.toggle_theme_button:
            self.app.toggle_theme_button.configure(text="Switch to Dark Mode")
