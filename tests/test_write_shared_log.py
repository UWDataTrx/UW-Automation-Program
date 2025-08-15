import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils_functions import write_audit_log


def test_write_audit_log():
    script_name = "test_script"
    message = "This is a test log entry."
    status = "INFO"
    write_audit_log(script_name, message, status)
    print("Log entry written. Check your Logs/{username}/Audit_Log.csv file.")


if __name__ == "__main__":
    test_write_audit_log()
