"""
Configuration module for the Repricing Automation application.
Contains configuration classes and constants.
"""

import multiprocessing
import json
import os
from pathlib import Path


class ProcessingConfig:
    """Configuration class for processing settings and validation."""

    REQUIRED_COLUMNS = [
        "DATEFILLED",
        "SOURCERECORDID",
        "QUANTITY",
        "DAYSUPPLY",
        "NDC",
        "MemberID",
        "Drug Name",
        "Pharmacy Name",
        "Total AWP (Historical)",
    ]

    FILE_TYPES = [
        ("All files", "*.*"),
        ("CSV files", "*.csv"),
        ("Excel files", "*.xlsx"),
    ]

    TEMPLATE_FILE_TYPES = [("Excel files", "*.xlsx")]

    DEFAULT_OPPORTUNITY_NAME = "claims detail PCU"

    @classmethod
    def get_multiprocessing_workers(cls):
        """Get the optimal number of workers for multiprocessing."""
        return min(4, max(1, multiprocessing.cpu_count() // 2))

    @classmethod
    def validate_required_columns(cls, df):
        """Validate that all required columns are present in the DataFrame."""
        missing_cols = [col for col in cls.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        return True


class DisruptionConfig:
    """Configuration for disruption types to reduce conditional complexity."""

    DISRUPTION_TYPES = {
        "Tier Disruption": {
            "module": "modules.tier_disruption",
            "file": "tier_disruption.py",
        },
        "B/G Disruption": {
            "module": "modules.bg_disruption",
            "file": "bg_disruption.py",
        },
        "OpenMDF (Tier)": {"module": "modules.openmdf_tier", "file": "openmdf_tier.py"},
        "OpenMDF (B/G)": {"module": "modules.openmdf_bg", "file": "openmdf_bg.py"},
        "Full Claims File": {"module": "modules.full_claims", "file": "full_claims.py"},
    }

    @classmethod
    def get_program_file(cls, disruption_type):
        """Get the program file for a disruption type."""
        config = cls.DISRUPTION_TYPES.get(disruption_type)
        return config["file"] if config else None

    @classmethod
    def get_disruption_labels(cls):
        """Get list of available disruption types (excluding Full Claims File)."""
        return [
            label
            for label in cls.DISRUPTION_TYPES.keys()
            if label != "Full Claims File"
        ]


class AppConstants:
    """Application constants and configuration values."""

    # Configuration and audit log files
    CONFIG_FILE = Path("config.json")
    AUDIT_LOG = Path("audit_log.csv")  # Default fallback

    @classmethod
    def get_audit_log_path(cls):
        """Get the audit log path from configuration."""
        try:
            config_path = Path(__file__).parent / "file_paths.json"
            with open(config_path, "r") as f:
                file_paths = json.load(f)
            return Path(os.path.expandvars(file_paths["audit_log"]))
        except (FileNotFoundError, KeyError):
            # Fallback to default if config is missing
            return cls.AUDIT_LOG

    # Template handling constants
    BACKUP_SUFFIX = "_backup.xlsx"
    UPDATED_TEMPLATE_NAME = "_Rx Repricing_wf.xlsx"

    # Welcome messages for different users
    WELCOME_MESSAGES = {
        "DamionMorrison": "Welcome back, Damion! Ready to reprice?",
        "DannyBushnell": "Hello Danny! Let's get started.",
        "BrettBauer": "Hi Brett, your automation awaits!",
        "BrendanReamer": "Welcome Brendan! Ready to optimize?",
    }

    # Emoji options for welcome message
    EMOJIS = [
        ":rocket:",
        ":sunglasses:",
        ":star:",
        ":tada:",
        ":computer:",
        ":chart_with_upwards_trend:",
    ]

    # Notes text for UI
    NOTES_TEXT = (
        "Note:\n\n"
        "Ensure FormularyTier is set before running disruption.\n"
        "Close any open Excel instances.\n"
        "Keep template name as _Rx Repricing_wf until done."
    )
