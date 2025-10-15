# Pharmacy Exclusion Standardization - Implementation Summary

## Date: October 15, 2025

## Problem Identified

All pharmacy exclusion logic across multiple modules was incorrectly marking valid pharmacy matches as "REVIEW" instead of properly resolving to "yes" or "no" values.

### Root Cause

**Type Conversion Bug in Network Data:**
- Network `pharmacy_nabp` values were stored as floats (e.g., `1822750.0`)
- Direct float → string conversion preserved decimals: `'1822750.0'`
- Claims `NABP` values were integers converted to strings: `'1822750'`
- **These values never matched**, causing all pharmacies to default to "REVIEW"

**Additional Issues:**
- NaN values converted to string `'nan'` then padded to `'0000000nan'`
- Inconsistent type handling between claims and network data
- Duplicated exclusion logic across 4 different modules

---

## Solution Implemented

### 1. Created Centralized Standardization Functions

**File:** `utils/utils.py`

#### `standardize_pharmacy_ids(df)`
Standardizes claims data:
- Replaces NaN/None with empty string BEFORE conversion
- Converts to string (avoiding 'nan' strings)
- Pads PHARMACYNPI to 10 digits
- Pads NABP to 7 digits

#### `standardize_network_ids(network)`
Standardizes network data with critical fix:
- Replaces NaN/None with 0
- **Converts float → int → string** (removes `.0` decimal!)
- Pads pharmacy_npi to 10 digits
- Pads pharmacy_nabp to 7 digits

**Key Fix:**
```python
# OLD (BROKEN):
network["pharmacy_nabp"] = network["pharmacy_nabp"].astype(str).str.zfill(7)
# 1822750.0 → '1822750.0' (no match!)

# NEW (WORKING):
network["pharmacy_nabp"] = network["pharmacy_nabp"].replace([np.nan, None], 0).astype(int).astype(str).str.zfill(7)
# 1822750.0 → 1822750 → '1822750' (matches!)
```

### 2. Updated All Disruption Modules

Applied standardization to 4 modules:

#### ✅ `modules/tier_disruption.py`
- Added import: `standardize_pharmacy_ids, standardize_network_ids`
- Calls standardization before `vectorized_resolve_pharmacy_exclusion()`
- Removed inline type conversion code

#### ✅ `modules/bg_disruption.py`
- Added import: `standardize_pharmacy_ids, standardize_network_ids`
- Replaced 30+ lines of inline exclusion logic
- Now uses centralized functions

#### ✅ `modules/openmdf_bg.py`
- Added import: `standardize_pharmacy_ids, standardize_network_ids`
- Replaced inline exclusion logic
- Now uses centralized functions

#### ✅ `modules/openmdf_tier.py`
- Added import: `standardize_pharmacy_ids, standardize_network_ids`
- Replaced inline exclusion logic
- Now uses centralized functions

---

## Implementation Pattern

All modules now follow this consistent pattern:

```python
# 1. Import standardization functions
from utils.utils import (
    vectorized_resolve_pharmacy_exclusion,
    standardize_pharmacy_ids,
    standardize_network_ids
)

# 2. After merging reference data, standardize IDs
df = standardize_pharmacy_ids(df)
network = standardize_network_ids(network)

# 3. Use centralized vectorized resolver
df["pharmacy_is_excluded"] = vectorized_resolve_pharmacy_exclusion(df, network)
```

**Old code removed (30+ lines per module):**
- Manual `.astype(str).str.strip()` conversions
- Manual lookup dictionaries (`nabp_lookup`, `npi_lookup`)
- Inline `normalize_excluded()` functions
- Inline `resolve_exclusion()` functions

---

## Validation Results

### Before Fix:
```
pharmacy_is_excluded value counts: {None: 1328}
Vector resolve -> True: 0, False: 0, REVIEW: 1328
```
**All pharmacies marked as REVIEW!** ❌

### After Fix:
```
pharmacy_is_excluded value counts: {False: 1280, True: 48}
Vector resolve -> True: 105, False: 3953, REVIEW: 0
Excluded pharmacies: 48
Non-excluded pharmacies: 1280
```
**Proper exclusion resolution!** ✅

---

## Benefits

### 1. **Correctness**
- Pharmacy matching now works correctly
- No more false "REVIEW" results
- Proper handling of NaN values

### 2. **Consistency**
- All 4 modules use identical standardization logic
- Centralized functions ensure uniform behavior
- Single source of truth for ID formatting

### 3. **Maintainability**
- Removed ~120 lines of duplicated code (30 lines × 4 modules)
- Bugs fixed once in utils.utils apply everywhere
- Easier to test and validate

### 4. **Performance**
- Vectorized operations (no row-by-row iteration)
- Persistent caching with SHA256 signatures
- Faster processing for large datasets

---

## Files Modified

| File | Changes |
|------|---------|
| `utils/utils.py` | ✅ Fixed `standardize_network_ids()` (int conversion) |
| `modules/tier_disruption.py` | ✅ Updated to use centralized functions |
| `modules/bg_disruption.py` | ✅ Updated to use centralized functions |
| `modules/openmdf_bg.py` | ✅ Updated to use centralized functions |
| `modules/openmdf_tier.py` | ✅ Updated to use centralized functions |

---

## Testing

### Test Script Created:
`debug_standardization.py` - Validates ID standardization and matching

**Sample Output:**
```
=== NETWORK DATA BEFORE ===
pharmacy_nabp sample: [1822750.0, 5746649.0, ...]
pharmacy_nabp dtypes: float64

=== NETWORK DATA AFTER ===
pharmacy_nabp sample: ['1822750', '5746649', ...]
pharmacy_nabp dtypes: object

=== MATCHING TEST ===
Claim NABP: '1825655' | Matches in network: 2
  pharmacy_is_excluded values: ['no', 'no']
```

---

## Future Maintenance

### When Adding New Modules:
1. Import `standardize_pharmacy_ids` and `standardize_network_ids`
2. Call standardization BEFORE exclusion resolution
3. Use `vectorized_resolve_pharmacy_exclusion()` for matching
4. DO NOT write custom type conversion or matching logic

### Cache Management:
```python
from utils.utils import clear_pharmacy_exclusion_cache

# Clear cache if network data changes
clear_pharmacy_exclusion_cache()
```

---

## Technical Notes

### Type Conversion Sequence:
- **Claims (int → string):** `1825655 → '1825655'`
- **Network (float → int → string):** `1822750.0 → 1822750 → '1822750'`
- Both now produce matching string formats

### NaN Handling:
- Claims: NaN → empty string → '0000000000'
- Network: NaN → 0 → '0000000000'
- Consistent handling prevents 'nan' string issues

### Caching:
- SHA256 signature based on network data
- Persistent cache stored in `build/pharmacy_exclusion_cache.pkl`
- Automatic invalidation when network data changes

---

## Conclusion

All disruption modules now use consistent, correct pharmacy ID standardization. The float-to-string conversion bug has been fixed, and all inline exclusion logic has been replaced with centralized functions. This ensures reliable pharmacy matching across all pipelines.

**Status:** ✅ Complete and Validated
