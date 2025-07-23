import sys
import os
import modules.error_reporter
from safe_error_analysis import get_user_errors_safe
# Ensure project root is in sys.path for module imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Explicitly initialize error logging to use the import
modules.error_reporter.setup_error_logging()

def generate_user_support_report(username):
    """Generate a support report for a specific user."""
    print(f"=== SUPPORT REPORT FOR {username.upper()} ===")

    errors = get_user_errors_safe(username, 30)
    print(f"Errors found in last 30 days: {len(errors)}")

    if errors:
        print("\nRecent errors:")
        for i, error in enumerate(errors[:5], 1):
            print(f"\n{i}. {error['timestamp']} - {error['status']}")
            print(f"   Script: {error['script']}")
            print(f"   Error: {error['message'][:150]}...")
    else:
        print(f"\nNo errors found for {username} in the last 30 days.")


if __name__ == "__main__":
    generate_user_support_report("DamionMorrison")
