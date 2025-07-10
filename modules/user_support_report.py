from safe_error_analysis import get_user_errors_safe

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
