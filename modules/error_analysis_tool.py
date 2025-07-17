"""
Error Analysis and Support Helper
Provides tools to analyze audit logs and generate support reports for user assistance.
"""

import pandas as pd
import os
import json
from datetime import datetime, timedelta
from pathlib import Path


def get_audit_log_path():
    """Get the path to the audit log file from config."""
    config_path = Path(__file__).parent.parent / "config" / "file_paths.json"
    with open(config_path, "r") as f:
        file_paths = json.load(f)
    return os.path.expandvars(file_paths["audit_log"])


def get_user_errors(username=None, days_back=7, error_types=None):
    """
    Get errors for a specific user or all users within a date range.

    Args:
        username: Specific username to filter by (None for all users)
        days_back: Number of days to look back (default 7)
        error_types: List of error types to filter by (e.g., ['USER_ERROR', 'SYSTEM_ERROR'])

    Returns:
        DataFrame with filtered error entries
    """
    try:
        log_path = get_audit_log_path()
        if not os.path.exists(log_path):
            print(f"Audit log not found at: {log_path}")
            return pd.DataFrame()

        # Read the CSV file
        df = pd.read_csv(log_path)

        # Convert timestamp to datetime
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])

        # Filter by date range
        cutoff_date = datetime.now() - timedelta(days=days_back)
        df = df[df["Timestamp"] >= cutoff_date]

        # Filter by error types
        if error_types is None:
            error_types = ["USER_ERROR", "SYSTEM_ERROR", "FILE_ERROR", "DATA_ERROR"]
        df = df[df["Status"].isin(error_types)]

        # Filter by username if specified
        if username:
            df = df[df["User"].str.contains(username, case=False, na=False)]

        # Sort by timestamp (newest first)
        df = df.sort_values("Timestamp", ascending=False)

        return df

    except Exception as e:
        print(f"Error reading audit log: {e}")
        return pd.DataFrame()


def generate_user_support_report(username, days_back=30):
    """
    Generate a comprehensive support report for a specific user.

    Args:
        username: Username to generate report for
        days_back: Number of days to analyze (default 30)

    Returns:
        String containing formatted support report
    """
    try:
        log_path = get_audit_log_path()
        df = pd.read_csv(log_path)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])

        # Filter for the user and date range
        cutoff_date = datetime.now() - timedelta(days=days_back)
        user_df = df[
            (df["User"].str.contains(username, case=False, na=False))
            & (df["Timestamp"] >= cutoff_date)
        ]

        # Get error entries
        error_df = user_df[
            user_df["Status"].isin(
                ["USER_ERROR", "SYSTEM_ERROR", "FILE_ERROR", "DATA_ERROR"]
            )
        ]

        # Get session info
        session_df = user_df[user_df["Status"].isin(["START", "END", "ACCESS_GRANTED"])]

        # Generate report
        report = f"""
=== USER SUPPORT REPORT ===
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
User: {username}
Analysis Period: Last {days_back} days

=== SUMMARY ===
Total Sessions: {len(session_df[session_df["Status"] == "START"])}
Total Errors: {len(error_df)}
Error Types:
- User Errors: {len(error_df[error_df["Status"] == "USER_ERROR"])}
- System Errors: {len(error_df[error_df["Status"] == "SYSTEM_ERROR"])}
- File Errors: {len(error_df[error_df["Status"] == "FILE_ERROR"])}
- Data Errors: {len(error_df[error_df["Status"] == "DATA_ERROR"])}

=== RECENT SESSIONS ===
"""

        # Add recent sessions
        recent_sessions = session_df.head(5)
        for _, session in recent_sessions.iterrows():
            report += f"{session['Timestamp'].strftime('%Y-%m-%d %H:%M')} - {session['Status']}: {session['Message'][:100]}...\n"

        report += "\n=== RECENT ERRORS ===\n"

        # Add recent errors
        recent_errors = error_df.head(10)
        for _, error in recent_errors.iterrows():
            report += f"""
{error["Timestamp"].strftime("%Y-%m-%d %H:%M")} - {error["Status"]}
Script: {error["Script"]}
Error: {error["Message"][:200]}...
---
"""

        # Add error patterns
        if len(error_df) > 0:
            report += "\n=== ERROR PATTERNS ===\n"
            script_errors = error_df["Script"].value_counts()
            report += "Most Common Error Sources:\n"
            for script, count in script_errors.head(5).items():
                report += f"- {script}: {count} errors\n"

        report += "\n=== RECOMMENDATIONS ===\n"

        # Generate recommendations based on error patterns
        if len(error_df[error_df["Status"] == "FILE_ERROR"]) > 0:
            report += (
                "- Multiple file errors detected. Check file permissions and paths.\n"
            )
        if len(error_df[error_df["Status"] == "USER_ERROR"]) > 0:
            report += "- User errors present. Consider additional training or UI improvements.\n"
        if len(error_df[error_df["Status"] == "SYSTEM_ERROR"]) > 0:
            report += (
                "- System errors detected. Review system resources and dependencies.\n"
            )

        report += "\n=== END REPORT ===\n"

        return report

    except Exception as e:
        return f"Error generating support report: {e}"


def get_error_summary(days_back=7):
    """
    Get a summary of all errors across all users.

    Args:
        days_back: Number of days to analyze

    Returns:
        Dictionary with error summary statistics
    """
    try:
        error_df = get_user_errors(days_back=days_back)

        if error_df.empty:
            return {
                "total_errors": 0,
                "message": "No errors found in the specified period",
            }

        summary = {
            "total_errors": len(error_df),
            "error_types": error_df["Status"].value_counts().to_dict(),
            "users_with_errors": error_df["User"].nunique(),
            "most_affected_user": error_df["User"].value_counts().index[0]
            if len(error_df) > 0
            else None,
            "most_common_script": error_df["Script"].value_counts().index[0]
            if len(error_df) > 0
            else None,
            "date_range": f"Last {days_back} days",
            "latest_error": error_df.iloc[0]["Timestamp"].strftime("%Y-%m-%d %H:%M")
            if len(error_df) > 0
            else None,
        }

        return summary

    except Exception as e:
        return {"error": f"Failed to generate error summary: {e}"}


def export_user_errors_to_csv(username, output_file=None, days_back=30):
    """
    Export a user's errors to a CSV file for detailed analysis.

    Args:
        username: Username to export errors for
        output_file: Output file path (defaults to username_errors.csv)
        days_back: Number of days to look back

    Returns:
        Path to the exported file or None if failed
    """
    try:
        error_df = get_user_errors(username=username, days_back=days_back)

        if error_df.empty:
            print(f"No errors found for user {username} in the last {days_back} days")
            return None

        if output_file is None:
            output_file = f"{username}_errors_{datetime.now().strftime('%Y%m%d')}.csv"

        error_df.to_csv(output_file, index=False)
        print(f"Exported {len(error_df)} error entries to {output_file}")
        return output_file

    except Exception as e:
        print(f"Failed to export errors: {e}")
        return None


if __name__ == "__main__":
    # Example usage
    print("=== ERROR ANALYSIS TOOL ===")
    print("\n1. Error Summary (Last 7 days):")
    summary = get_error_summary(7)
    for key, value in summary.items():
        print(f"   {key}: {value}")

    print("\n2. Recent Errors for All Users:")
    recent_errors = get_user_errors(days_back=7)
    if not recent_errors.empty:
        for _, error in recent_errors.head(3).iterrows():
            print(
                f"   {error['Timestamp'].strftime('%Y-%m-%d %H:%M')} - {error['User']} - {error['Status']}"
            )
            print(f"      {error['Message'][:100]}...")
    else:
        print("   No recent errors found")
