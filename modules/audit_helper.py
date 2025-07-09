import logging
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import write_shared_log


def make_audit_entry(script_name, message, status="INFO"):
    try:
        write_shared_log(script_name, message, status)
    except Exception as e:
        logging.error(f"[AUDIT FAIL] {script_name} audit failed: {e}")
        try:
            with open("local_fallback_log.txt", "a") as f:
                f.write(f"{script_name}: {message} [{status}]\n")
        except Exception as inner:
            logging.error(f"[FALLBACK FAIL] Could not write fallback log: {inner}")
