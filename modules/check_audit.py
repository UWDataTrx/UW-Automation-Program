import os
import csv
import json
from pathlib import Path

# Load the audit log path from config
config_path = Path(__file__).parent.parent / "config" / "file_paths.json"
with open(config_path, 'r') as f:
    file_paths = json.load(f)
log_path = os.path.expandvars(file_paths["audit_log"])

print(f"Audit log path: {log_path}")
print(f"File exists: {os.path.exists(log_path)}")

if os.path.exists(log_path):
    print(f"File size: {os.path.getsize(log_path)} bytes")
    
    try:
        with open(log_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
        print(f"Total rows: {len(rows)}")
        
        if len(rows) > 0:
            print(f"Header: {rows[0]}")
            
        if len(rows) > 5:
            print("\nLast 5 entries:")
            for i, row in enumerate(rows[-5:], start=len(rows)-4):
                print(f"Row {i}: {row}")
        else:
            print("\nAll entries:")
            for i, row in enumerate(rows, start=1):
                print(f"Row {i}: {row}")
                
    except Exception as e:
        print(f"Error reading CSV: {e}")
        
        # Try reading as text
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"Raw content (last 500 chars):\n{content[-500:]}")
        except Exception as e2:
            print(f"Error reading as text: {e2}")
