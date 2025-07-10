"""
Robust Error Analysis Tool
Handles CSV parsing issues and provides comprehensive error analysis.
"""

import os
from datetime import datetime, timedelta
import csv

def safe_read_audit_log():
    """
    Safely read the audit log with error handling for malformed CSV entries.
    
    Returns:
        List of dictionaries containing log entries
    """
    log_path = os.path.expandvars(
        r"%OneDrive%/True Community - Data Analyst/Python Repricing Automation Program/Logs/audit_log.csv"
    )
    
    entries = []
    
    try:
        with open(log_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header row
            
            for line_num, row in enumerate(reader, start=2):
                try:
                    # Handle rows with different field counts
                    if len(row) >= 5:
                        # Take first 5 fields and join any extra fields to message
                        if len(row) > 5:
                            # Join extra fields to the message field
                            message_with_extra = " ".join(row[3:])
                            cleaned_row = row[:3] + [message_with_extra] + [row[-1]]
                        else:
                            cleaned_row = row
                        
                        # Create entry dictionary
                        entry = {
                            'line_number': line_num,
                            'timestamp': cleaned_row[0],
                            'user': cleaned_row[1],
                            'script': cleaned_row[2],
                            'message': cleaned_row[3],
                            'status': cleaned_row[4] if len(cleaned_row) > 4 else 'UNKNOWN'
                        }
                        entries.append(entry)
                        
                except Exception as e:
                    print(f"Warning: Skipped malformed line {line_num}: {e}")
                    continue
                    
    except Exception as e:
        print(f"Error reading audit log: {e}")
        return []
    
    return entries

def get_recent_errors(days_back=7, error_types=None):
    """Get recent errors with safe CSV parsing."""
    if error_types is None:
        error_types = ['USER_ERROR', 'SYSTEM_ERROR', 'FILE_ERROR', 'DATA_ERROR']
    
    entries = safe_read_audit_log()
    if not entries:
        return []
    
    # Filter for errors within date range
    cutoff_date = datetime.now() - timedelta(days=days_back)
    recent_errors = []
    
    for entry in entries:
        try:
            # Parse timestamp
            entry_time = datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M:%S')
            
            # Check if within date range and is an error
            if entry_time >= cutoff_date and entry['status'] in error_types:
                recent_errors.append(entry)
                
        except ValueError:
            # Skip entries with invalid timestamps
            continue
    
    # Sort by timestamp (newest first)
    recent_errors.sort(key=lambda x: x['timestamp'], reverse=True)
    return recent_errors

def get_user_errors_safe(username, days_back=7):
    """Get errors for a specific user with safe parsing."""
    all_errors = get_recent_errors(days_back)
    user_errors = [error for error in all_errors if username.lower() in error['user'].lower()]
    return user_errors

def generate_error_summary():
    """Generate a comprehensive error summary."""
    print("=== AUDIT LOG ERROR ANALYSIS ===")
    print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get all entries first to check log health
    all_entries = safe_read_audit_log()
    print(f"Total log entries processed: {len(all_entries)}")
    
    # Get recent errors
    recent_errors = get_recent_errors(days_back=7)
    print(f"Errors in last 7 days: {len(recent_errors)}")
    
    if recent_errors:
        # Error type breakdown
        error_types = {}
        users_with_errors = set()
        scripts_with_errors = {}
        
        for error in recent_errors:
            # Count error types
            error_type = error['status']
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            # Track users with errors
            users_with_errors.add(error['user'])
            
            # Track scripts with errors
            script = error['script']
            scripts_with_errors[script] = scripts_with_errors.get(script, 0) + 1
        
        print("\nError Types:")
        for error_type, count in sorted(error_types.items()):
            print(f"  {error_type}: {count}")
        
        print(f"\nUsers with errors: {len(users_with_errors)}")
        for user in sorted(users_with_errors):
            user_error_count = len([e for e in recent_errors if e['user'] == user])
            print(f"  {user}: {user_error_count} errors")
        
        print("\nScripts with most errors:")
        sorted_scripts = sorted(scripts_with_errors.items(), key=lambda x: x[1], reverse=True)
        for script, count in sorted_scripts[:5]:
            print(f"  {script}: {count}")
        
        print("\nMost Recent Errors:")
        for i, error in enumerate(recent_errors[:5], 1):
            print(f"\n{i}. {error['timestamp']} - {error['user']}")
            print(f"   Type: {error['status']} | Script: {error['script']}")
            print(f"   Message: {error['message'][:100]}...")
    
    else:
        print("\nNo errors found in the last 7 days.")
    
    # Check for successful operations
    recent_success = []
    for entry in all_entries[-50:]:  # Check last 50 entries
        if entry['status'] in ['INFO', 'START', 'END', 'ACCESS_GRANTED', 'IMPORTED']:
            recent_success.append(entry)
    
    print(f"\nRecent successful operations: {len(recent_success)}")
    if recent_success:
        latest_success = recent_success[-1]
        print(f"Latest: {latest_success['timestamp']} - {latest_success['user']} - {latest_success['status']}")

if __name__ == "__main__":
    generate_error_summary()
