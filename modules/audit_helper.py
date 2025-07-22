import logging
import os
import sys
import getpass
import platform
import socket
from datetime import datetime

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import write_audit_log, create fallback if not available
try:
    from utils.utils import write_audit_log
except ImportError:
    # Fallback function if utils.utils is not available
    def write_audit_log(script_name, message, status="INFO"):
        """Fallback logging function when utils.utils is not available"""
        print(f"[{status}] {script_name}: {message}")


def make_audit_entry(script_name, message, status="INFO"):
    """Enhanced audit entry with better error handling and user tracking."""
    try:
        try:
            username = os.getlogin()
        except Exception:
            username = os.environ.get("USERNAME") or os.environ.get("USER") or "UnknownUser"
        message = f"User: {username} | {message}"
        write_audit_log(script_name, message, status)
    except Exception as e:
        logging.error(f"[AUDIT FAIL] {script_name} audit failed: {e}")
        try:
            with open("local_fallback_log.txt", "a") as f:
                f.write(f"{script_name}: {message} [{status}]\n")
        except Exception as inner:
            logging.error(f"[FALLBACK FAIL] Could not write fallback log: {inner}")


def log_user_session_start(script_name="Application"):
    """Log comprehensive user session start information."""
    try:
        try:
            username = os.getlogin()
        except Exception:
            username = os.environ.get("USERNAME") or os.environ.get("USER") or "UnknownUser"
        computer_name = socket.gethostname()
        python_version = platform.python_version()
        os_info = f"{platform.system()} {platform.release()}"

        session_info = (
            f"User: {username} | Computer: {computer_name} | "
            f"Python: {python_version} | OS: {os_info}"
        )

        make_audit_entry(script_name, f"Session started - {session_info}", "START")
        logging.info(f"Session started for user: {username}")

    except Exception as e:
        logging.error(f"Failed to log session start: {e}")
        make_audit_entry(script_name, f"Session start logging failed: {e}", "ERROR")


def log_user_session_end(script_name="Application"):
    """Log user session end information."""
    try:
        try:
            username = os.getlogin()
        except Exception:
            username = os.environ.get("USERNAME") or os.environ.get("USER") or "UnknownUser"
        computer_name = socket.gethostname()
        make_audit_entry(script_name, f"Session ended for user: {username} on {computer_name}", "END")
        logging.info(f"Session ended for user: {username}")
    except Exception as e:
        logging.error(f"Failed to log session end: {e}")
        make_audit_entry(script_name, f"Session end logging failed: {e}", "ERROR")


def log_file_access(script_name, file_path, operation):
    """Log file access with user information."""
    try:
        try:
            username = os.getlogin()
        except Exception:
            username = os.environ.get("USERNAME") or os.environ.get("USER") or "UnknownUser"
        make_audit_entry(script_name, f"User: {username} | File: {file_path} | Operation: {operation}", "FILE_ACCESS")
        logging.info(f"File access by user: {username} | {file_path} | {operation}")
    except Exception as e:
        logging.error(f"Failed to log file access: {e}")
        make_audit_entry(script_name, f"File access logging failed: {e}", "ERROR")


def log_process_action(script_name, action, details=""):
    """Log process actions with user information."""
    try:
        username = getpass.getuser()
        message = f"Process {action} by {username}"
        if details:
            message += f" - {details}"
        make_audit_entry(script_name, message, "PROCESS")

    except Exception as e:
        logging.error(f"Failed to log process action: {e}")
        make_audit_entry(script_name, f"Process action logging failed: {e}", "ERROR")


def validate_user_access():
    """Validate user access and log the attempt."""
    try:
        username = getpass.getuser()
        computer_name = socket.gethostname()

        # Log access attempt
        make_audit_entry(
            "UserValidation",
            f"Access attempt by {username} on {computer_name}",
            "ACCESS_ATTEMPT",
        )

        # You can add additional validation logic here
        # For example, check against a list of authorized users
        # authorized_users = ["user1", "user2", "admin"]
        # if username not in authorized_users:
        #     make_audit_entry("UserValidation", f"UNAUTHORIZED access attempt by {username}", "SECURITY_VIOLATION")
        #     return False

        make_audit_entry(
            "UserValidation", f"Access granted to {username}", "ACCESS_GRANTED"
        )
        return True

    except Exception as e:
        logging.error(f"Failed to validate user access: {e}")
        make_audit_entry("UserValidation", f"User validation failed: {e}", "ERROR")
        return False


def log_user_error(
    script_name, error_type, error_message, user_action="", file_context=""
):
    """Log user errors with comprehensive context for support assistance."""
    try:
        username = getpass.getuser()
        computer_name = socket.gethostname()
        python_version = platform.python_version()
        os_info = f"{platform.system()} {platform.release()}"

        # Build comprehensive error context
        error_context = {
            "user": username,
            "computer": computer_name,
            "python_version": python_version,
            "os": os_info,
            "error_type": error_type,
            "user_action": user_action,
            "file_context": file_context,
        }

        # Create detailed error message for support
        support_message = (
            f"USER ERROR - {error_type} | "
            f"User: {username} on {computer_name} | "
            f"Python: {python_version} | OS: {os_info} | "
            f"Action: {user_action} | File: {file_context} | "
            f"Error: {error_message}"
        )

        make_audit_entry(script_name, support_message, "USER_ERROR")
        logging.error(f"User error for {username}: {error_message}")

        return error_context

    except Exception as e:
        logging.error(f"Failed to log user error: {e}")
        make_audit_entry(script_name, f"Error logging failed: {e}", "SYSTEM_ERROR")


def log_system_error(script_name, error_message, stack_trace="", context=""):
    """Log system/application errors with full diagnostic information."""
    try:
        username = getpass.getuser()
        computer_name = socket.gethostname()
        python_version = platform.python_version()
        os_info = f"{platform.system()} {platform.release()}"

        # Create detailed system error message
        system_message = (
            f"SYSTEM ERROR - {script_name} | "
            f"User: {username} on {computer_name} | "
            f"Python: {python_version} | OS: {os_info} | "
            f"Context: {context} | "
            f"Error: {error_message}"
        )

        if stack_trace:
            system_message += (
                f" | Stack: {stack_trace[:500]}..."  # Limit stack trace length
            )

        make_audit_entry(script_name, system_message, "SYSTEM_ERROR")
        logging.error(f"System error: {error_message}")

    except Exception as e:
        logging.error(f"Failed to log system error: {e}")


def log_file_error(script_name, file_path, error_message, operation=""):
    """Log file-related errors with file context."""
    try:
        username = getpass.getuser()

        file_info = "Unknown"
        try:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                file_info = f"Size: {file_size} bytes"
            else:
                file_info = "File not found"
        except Exception:
            file_info = "Cannot access file info"

        error_context = (
            f"FILE ERROR - {operation} | "
            f"User: {username} | "
            f"File: {file_path} | "
            f"File Info: {file_info} | "
            f"Error: {error_message}"
        )

        make_audit_entry(script_name, error_context, "FILE_ERROR")
        logging.error(f"File error for {username}: {error_message}")

    except Exception as e:
        logging.error(f"Failed to log file error: {e}")


def log_data_processing_error(script_name, error_message, data_context="", row_count=0):
    """Log data processing errors with data context."""
    try:
        username = getpass.getuser()

        processing_context = (
            f"DATA ERROR - Processing | "
            f"User: {username} | "
            f"Data Context: {data_context} | "
            f"Rows Processed: {row_count} | "
            f"Error: {error_message}"
        )

        make_audit_entry(script_name, processing_context, "DATA_ERROR")
        logging.error(f"Data processing error for {username}: {error_message}")

    except Exception as e:
        logging.error(f"Failed to log data processing error: {e}")


def create_error_report(username, error_type, error_details):
    """Create a formatted error report for support assistance."""
    try:
        computer_name = socket.gethostname()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""
=== ERROR REPORT FOR SUPPORT ===
Timestamp: {timestamp}
User: {username}
Computer: {computer_name}
Error Type: {error_type}
Python Version: {platform.python_version()}
OS: {platform.system()} {platform.release()}

Error Details:
{error_details}

System Information:
- Platform: {platform.platform()}
- Processor: {platform.processor()}
- Architecture: {platform.architecture()[0]}

=== END REPORT ===
"""

        # Log the formatted report
        make_audit_entry(
            "ErrorReport", f"Support report generated for {username}", "SUPPORT_REPORT"
        )

        return report

    except Exception as e:
        logging.error(f"Failed to create error report: {e}")
        return f"Error report generation failed: {e}"
