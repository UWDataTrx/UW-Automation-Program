import json
import os

with open("config/file_paths.json", "r") as f:
    paths = json.load(f)

print("Checking file paths in config/file_paths.json...\n")
for key, path in paths.items():
    expanded_path = os.path.expandvars(path).strip()
    exists = os.path.exists(expanded_path)
    print(f"{key}: {expanded_path} -> {'FOUND' if exists else 'NOT FOUND'}")
