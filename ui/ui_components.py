"""
UI Components module for the Repricing Automation application.
This module contains UI-related classes and utilities to improve code organization.
"""

import customtkinter as ctk

# UI styling variables
FONT_SELECT = ("Cambria", 20, "bold")

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


class UIFactory:
    """Factory class to create UI components and reduce code duplication."""

    @staticmethod
    def _create_button_base(parent, text, command, fg_color):
        """Base method for creating buttons with common styling."""
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            font=FONT_SELECT,
            height=40,
            bg_color=fg_color,
            text_color="#000000",
        )

    @staticmethod
    def create_standard_button(parent, text, command):
        """Create a standardized button with common styling."""
        return UIFactory._create_button_base(
            parent, text, command, LIGHT_COLORS["mint"]
        )

    @staticmethod
    def create_red_button(parent, text, command):
        """Create a red button (for cancel/exit actions)."""
        return UIFactory._create_button_base(
            parent, text, command, LIGHT_COLORS["button_red"]
        )

    @staticmethod
    def create_standard_frame(parent):
        """Create a standardized frame with common styling."""
        return ctk.CTkFrame(parent, bg_color=LIGHT_COLORS["grey_blue"])

    @staticmethod
    def create_standard_label(parent, text, width=None):
        """Create a standardized label."""
        if width:
            return ctk.CTkLabel(parent, text=text, font=FONT_SELECT, width=width)
        return ctk.CTkLabel(parent, text=text, font=FONT_SELECT)


class ThemeManager:
    """Manages theme colors and application of themes to UI components."""

    @staticmethod
    def apply_theme_colors(app_instance, colors):
        """Apply theme colors to all UI components."""
        ThemeManager._apply_root_colors(app_instance, colors)
        ThemeManager._apply_frame_colors(app_instance, colors)
        ThemeManager._apply_button_colors(app_instance, colors)
        ThemeManager._apply_special_component_colors(app_instance, colors)

    @staticmethod
    def _apply_root_colors(app_instance, colors):
        """Apply colors to the root window."""
        try:
            app_instance.root.configure(bg_color=colors["dark_blue"])
        except Exception:
            app_instance.root.configure(bg=colors["dark_blue"])

    @staticmethod
    def _apply_frame_colors(app_instance, colors):
        """Apply colors to frames."""
        frames = ["button_frame", "notes_frame", "dis_frame", "prog_frame"]
        for frame_name in frames:
            frame = getattr(app_instance, frame_name, None)
            if frame:
                frame.configure(bg_color=colors["grey_blue"])

    @staticmethod
    def _apply_button_colors(app_instance, colors):
        """Apply colors to standard buttons."""
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
            btn = getattr(app_instance, btn_name, None)
            if btn:
                btn.configure(bg_color=colors["mint"], text_color="#000000")

    @staticmethod
    def _apply_special_component_colors(app_instance, colors):
        """Apply colors to special components."""
        # Apply colors to special buttons
        if hasattr(app_instance, "exit_button"):
            app_instance.exit_button.configure(
                bg_color=colors["button_red"], text_color="#000000"
            )

        # Apply colors to progress components
        if hasattr(app_instance, "progress_label"):
            app_instance.progress_label.configure(
                bg_color=colors["grey_blue"], text_color="#000000"
            )


class ProgressManager:
    """Manages progress bar updates and calculations."""

    @staticmethod
    def calculate_time_estimates(value, start_time):
        """Calculate progress percentage and time estimates."""
        import time

        percent = int(value * 100)
        elapsed = time.time() - start_time if start_time else 0
        est = int((elapsed / value) * (1 - value)) if value > 0 else 0
        return percent, est

    @staticmethod
    def format_progress_message(percent, estimated_seconds):
        """Format progress message with percentage and time estimate."""
        return f"Progress: {percent}% | Est. {estimated_seconds}s left"
