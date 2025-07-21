#!/usr/bin/env python3
"""
Script to update all references from write_shared_log to write_audit_log across the codebase
"""

import os
import re
from pathlib import Path

def update_file(file_path):
    """Update a single file to replace write_shared_log with write_audit_log"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Track if any changes were made
        original_content = content
        
        # Replace function calls
        content = re.sub(r'\bwrite_shared_log\b', 'write_audit_log', content)
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            return True
        return False
        
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Main function to update all Python files"""
    
    # Find all Python files in modules directory
    modules_dir = Path("modules")
    
    files_to_update = []
    
    # Add specific files that we know need updating
    for py_file in modules_dir.glob("*.py"):
        files_to_update.append(py_file)
    
    # Also check other directories
    for py_file in Path("tests").glob("*.py"):
        files_to_update.append(py_file)
        
    for py_file in Path("utils").glob("*.py"):
        if py_file.name != "utils.py":  # Skip the main utils.py since we already updated it
            files_to_update.append(py_file)
    
    updated_count = 0
    for file_path in files_to_update:
        if update_file(file_path):
            updated_count += 1
    
    print(f"Updated {updated_count} files total")

if __name__ == "__main__":
    main()
