import sys
import traceback
from datetime import datetime
from pathlib import Path


# Dynamically load error log path from file_paths.json


def get_error_log_path():
    try:
        from config.config_loader import ConfigLoader

        paths = ConfigLoader.load_file_paths()
        error_log_path = paths.get("error_log")
        if error_log_path:
            # Expand environment variables and user
            import os

            error_log_path = os.path.expandvars(error_log_path)
            error_log_path = os.path.expanduser(error_log_path)
            return Path(error_log_path)
    except Exception as e:
        print(f"Failed to load error_log path from config: {e}")
    # Fallback to previous hardcoded path
    return Path(
        r"C:\Users\DamionMorrison\OneDrive - True Rx Health Strategists\True Community - Data Analyst\UW Python Program\Logs\error_log.txt"
    )


ERROR_LOG_PATH = get_error_log_path()


def log_error_to_file(exc_type, exc_value, exc_traceback):
    """Logs error details to the shared OneDrive file."""
    try:
        # Ensure the log directory exists
        log_dir = ERROR_LOG_PATH.parent
        log_dir.mkdir(parents=True, exist_ok=True)
        with ERROR_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Script: {Path(sys.argv[0]).name}\n")
            f.write(f"Exception type: {exc_type.__name__}\n")
            f.write(f"Exception message: {exc_value}\n")
            f.write("Traceback:\n")
            traceback.print_tb(exc_traceback, file=f)
            f.write(f"{'=' * 60}\n")
    except Exception as log_exc:
        print(f"Failed to log error: {log_exc}")


# Set the global exception hook
def setup_error_logging():
    sys.excepthook = log_error_to_file


# Optionally, call setup_error_logging() automatically when imported
setup_error_logging()
