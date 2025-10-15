"""Quick test to verify exclusion logic handles 'no' correctly."""
import pandas as pd
import sys
from pathlib import Path
from utils.utils import vectorized_resolve_pharmacy_exclusion

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Create test data
network = pd.DataFrame({
    "pharmacy_nabp": ["1234567", "7654321", "1111111"],
    "pharmacy_npi": ["9876543210", "0123456789", "5555555555"],
    "pharmacy_is_excluded": ["no", "yes", "no"]
})

claims = pd.DataFrame({
    "NABP": ["1234567", "7654321", "1111111", "9999999"],
    "PHARMACYNPI": ["9876543210", "0123456789", "5555555555", "0000000000"]
})

# Test with cache disabled to ensure fresh calculation
result = vectorized_resolve_pharmacy_exclusion(claims, network, use_cache=False)

print("Test Results:")
print(f"Row 0 (NABP 1234567, should be False/not excluded): {result.iloc[0]}")
print(f"Row 1 (NABP 7654321, should be True/excluded): {result.iloc[1]}")
print(f"Row 2 (NABP 1111111, should be False/not excluded): {result.iloc[2]}")
print(f"Row 3 (unmatched, should be REVIEW): {result.iloc[3]}")

# Verify
assert not result.iloc[0], f"Expected False, got {result.iloc[0]}"
assert result.iloc[1], f"Expected True, got {result.iloc[1]}"
assert not result.iloc[2], f"Expected False, got {result.iloc[2]}"
assert result.iloc[3] == "REVIEW", f"Expected REVIEW, got {result.iloc[3]}"

print("\n✅ All tests passed! 'no' values are correctly mapped to False (not excluded)")
