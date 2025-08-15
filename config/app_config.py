import getpass
import json
import multiprocessing
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# Helper function to resolve file paths with user-based fallback
def resolve_path(one_drive_template, fallback_template):
    user = getpass.getuser()
    one_drive_path = one_drive_template.replace(
        "%OneDrive%", f"C:/Users/{user}/OneDrive"
    )
    fallback_path = fallback_template.replace("{user}", user)
    one_drive_path = os.path.expandvars(one_drive_path)
    fallback_path = os.path.expandvars(fallback_path)
    one_drive_path = Path(one_drive_path)
    fallback_path = Path(fallback_path)
    if one_drive_path.exists():
        return one_drive_path
    elif fallback_path.exists():
        return fallback_path
    else:
        raise FileNotFoundError(f"Neither {one_drive_path} nor {fallback_path} exists.")


# Example usage for all file_paths.json keys
def get_all_paths():
    return {
        "medi_span": resolve_path(
            "%OneDrive%/True Community - Data Analyst/Repricing Templates/Medispan Export 6.27.25.xlsx",
            "C:/Users/{user}/OneDrive - True Rx Health Strategist/True Rx Management Services/Data Analyst/Medispan Export 6.27.25.xlsx",
        ),
        "e_disrupt": resolve_path(
            "%OneDrive%/True Community - Data Analyst/Repricing Templates/Disruption/Formulary Tiers References/Copy of Exclusive - Formulary Reference Guide.xlsx",
            "C:/Users/{user}/OneDrive - True Rx Health Strategist/True Rx Management Services/Data Analyst/Repricing Templates/Disruption/Formulary Tiers References/Copy of Exclusive - Formulary Reference Guide.xlsx",
        ),
        "u_disrupt": resolve_path(
            "%OneDrive%/True Community - Data Analyst/Repricing Templates/Disruption/Formulary Tiers References/Copy of Universal - Formulary Reference Guide.xlsx",
            "C:/Users/{user}/OneDrive - True Rx Health Strategist/True Rx Management Services/Data Analyst/Repricing Templates/Disruption/Formulary Tiers References/Copy of Universal - Formulary Reference Guide.xlsx",
        ),
        "mdf_disrupt": resolve_path(
            "%OneDrive%/True Community - Data Analyst/Repricing Templates/Disruption/Formulary Tiers References/Copy of Open MDF - Formulary Reference Guide.xlsx",
            "C:/Users/{user}/OneDrive - True Rx Health Strategist/True Rx Management Services/Data Analyst/Repricing Templates/Disruption/Formulary Tiers References/Copy of Open MDF - Formulary Reference Guide.xlsx",
        ),
        "n_disrupt": resolve_path(
            "%OneDrive%/True Community - Data Analyst/Repricing Templates/Disruption/Pharmacy Disruption/Rx Sense Pharmacy Network 7.25.xlsx",
            "C:/Users/{user}/OneDrive - True Rx Health Strategist/True Rx Management Services/Data Analyst/Repricing Templates/Disruption/Pharmacy Disruption/Rx Sense Pharmacy Network 7.25.xlsx",
        ),
        "reprice": resolve_path(
            "_Rx Repricing_wf.xlsx",
            "C:/Users/{user}/OneDrive - True Rx Health Strategist/True Rx Management Services/Data Analyst/_Rx Repricing_wf.xlsx",
        ),
        "sharx": resolve_path(
            "%OneDrive%/True Community - Data Analyst/Repricing Templates/SHARx/Template_Rx Claims for SHARx.xlsx",
            "C:/Users/{user}/OneDrive - True Rx Health Strategist/True Rx Management Services/Data Analyst/Repricing Templates/SHARx/Template_Rx Claims for SHARx.xlsx",
        ),
        "epls": resolve_path(
            "%OneDrive%/True Community - Data Analyst/Repricing Templates/EPLS/Client Name_Rx Claims for EPLS.xlsx",
            "C:/Users/{user}/OneDrive - True Rx Health Strategist/True Rx Management Services/Data Analyst/Repricing Templates/EPLS/Client Name_Rx Claims for EPLS.xlsx",
        ),
        "pharmacy_validation": resolve_path(
            "%OneDrive%/True Community - Data Analyst/UW Python Program/Logs/Pharmacy_RxSense Validation.xlsx",
            "C:/Users/{user}/OneDrive - True Rx Health Strategist/True Rx Management Services/Data Analyst/UW Python Program/Logs/Pharmacy_RxSense Validation.xlsx",
        ),
        "audit_log": resolve_path(
            "%OneDrive%/True Community - Data Analyst/UW Python Program/Logs/Shared_Log.csv",
            "C:/Users/{user}/OneDrive - True Rx Health Strategist/True Rx Management Services/Data Analyst/UW Python Program/Logs/Shared_Log.csv",
        ),
        "diagnostic_reports": resolve_path(
            "%OneDrive%/True Community - Data Analyst/UW Python Program/Diagnostic Reports",
            "C:/Users/{user}/OneDrive - True Rx Health Strategist/True Rx Management Services/Data Analyst/UW Python Program/Diagnostic Reports",
        ),
    }


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

    @classmethod
    def get_diagnostic_reports_path(cls):
        """Get the diagnostic reports directory path from configuration using pathlib."""
        try:
            config_path = Path(__file__).parent / "file_paths.json"
            file_paths = json.loads(config_path.read_text(encoding="utf-8"))
            return Path(os.path.expandvars(file_paths["diagnostic_reports"]))
        except (FileNotFoundError, KeyError):
            # Fallback to default if config is missing
            return Path(
                r"C:\Users\DamionMorrison\OneDrive - True Rx Health Strategists\UW Automation Program\Diagnostic Reports"
            )


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
        """Get the audit log path from configuration using pathlib."""
        try:
            config_path = Path(__file__).parent / "file_paths.json"
            file_paths = json.loads(config_path.read_text(encoding="utf-8"))
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
