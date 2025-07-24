import csv
import json
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load the audit log path from config

config_path = Path(__file__).parent.parent / "config" / "file_paths.json"
with config_path.open("r") as f:
    file_paths = json.load(f)

# Expand environment variables in the audit_log path using Path and os-independent method
log_path_str = file_paths["audit_log"]
if log_path_str.startswith("$") or "${" in log_path_str:
    # If the path contains environment variables, expand them manually
    import os

    log_path_str = os.path.expandvars(log_path_str)
log_path = Path(log_path_str)


print(f"Audit log path: {log_path}")
print(f"File exists: {log_path.exists()}")

if log_path.exists():
    print(f"File size: {log_path.stat().st_size} bytes")

    try:
        with log_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        print(f"Total rows: {len(rows)}")

        if len(rows) > 0:
            print(f"Header: {rows[0]}")

        if len(rows) > 5:
            print("\nLast 5 entries:")
            for i, row in enumerate(rows[-5:], start=len(rows) - 4):
                print(f"Row {i}: {row}")
        else:
            print("\nAll entries:")
            for i, row in enumerate(rows, start=1):
                print(f"Row {i}: {row}")

    except Exception as e:
        print(f"Error reading CSV: {e}")

        # Try reading as text
        try:
            with log_path.open("r", encoding="utf-8") as f:
                content = f.read()
            print(f"Raw content (last 500 chars):\n{content[-500:]}")
        except Exception as e2:
            print(f"Error reading as text: {e2}")
