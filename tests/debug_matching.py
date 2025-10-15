"""Debug script to trace through the exact matching logic."""
import pandas as pd
from config.config_loader import ConfigLoader
from utils.utils import vectorized_resolve_pharmacy_exclusion

# Load files
fp = ConfigLoader.load_file_paths()

# Load network
print("=" * 80)
print("LOADING NETWORK FILE")
print("=" * 80)
network = pd.read_csv(fp['n_disrupt'], usecols=['pharmacy_nabp', 'pharmacy_npi', 'pharmacy_is_excluded'], dtype=str)
print(f"Network shape: {network.shape}")
print("\nFirst 5 network rows:")
print(network.head())

# Load repricing (tier disruption sheet)
print("\n" + "=" * 80)
print("LOADING REPRICING FILE")
print("=" * 80)
repricing = pd.read_excel(fp['repricing'], sheet_name="Tier Disruption", dtype=str)
print(f"Repricing shape: {repricing.shape}")
print(f"\nRepricing columns: {repricing.columns.tolist()}")

# Check for NABP/NPI columns
if 'NABP' in repricing.columns:
    print("\nFirst 5 NABP values from repricing:")
    print(repricing['NABP'].head())
else:
    print("\nNABP column NOT FOUND!")

if 'PHARMACYNPI' in repricing.columns:
    print("\nFirst 5 PHARMACYNPI values from repricing:")
    print(repricing['PHARMACYNPI'].head())
else:
    print("\nPHARMACYNPI column NOT FOUND!")

# Test the vectorized resolver with a small sample
print("\n" + "=" * 80)
print("TESTING VECTORIZED RESOLVER")
print("=" * 80)
sample_df = repricing.head(10).copy()
result = vectorized_resolve_pharmacy_exclusion(sample_df, network, use_cache=False)

print("\nResolver results for first 10 rows:")
for i, (idx, row) in enumerate(sample_df.iterrows()):
    nabp = row.get('NABP', 'N/A')
    npi = row.get('PHARMACYNPI', 'N/A')
    resolved = result.iloc[i]
    print(f"Row {i}: NABP={nabp}, NPI={npi} -> {resolved}")

# Manual check: does the first NABP exist in network?
if 'NABP' in repricing.columns and not repricing['NABP'].isna().all():
    test_nabp = str(repricing['NABP'].dropna().iloc[0]).strip().upper()
    network_nabps_clean = network['pharmacy_nabp'].astype(str).str.strip().str.upper()
    match = network[network_nabps_clean == test_nabp]
    print("\n" + "=" * 80)
    print(f"MANUAL MATCH TEST FOR NABP: {test_nabp}")
    print("=" * 80)
    print(f"Matches found: {len(match)}")
    if len(match) > 0:
        print("Match details:")
        print(match)
