"""Debug script to check why exclusion matching is failing."""
import pandas as pd
from pathlib import Path
from config.config_loader import ConfigLoader

# Load config
file_paths = ConfigLoader.load_file_paths()

# Load network
network_path = Path(file_paths["pharmacy_network"])
print(f"Loading network from: {network_path}")
network = pd.read_csv(
    network_path,
    usecols=["pharmacy_nabp", "pharmacy_npi", "pharmacy_is_excluded"],
    dtype=str,
    low_memory=False
)

print(f"\nNetwork shape: {network.shape}")
print(f"Network columns: {network.columns.tolist()}")
print("\nFirst 10 network rows:")
print(network.head(10))
print("\nNetwork value_counts for pharmacy_is_excluded:")
print(network["pharmacy_is_excluded"].value_counts(dropna=False))

# Load repricing
repricing_path = Path(file_paths["repricing"])
print(f"\n\nLoading repricing from: {repricing_path}")
repricing = pd.read_excel(repricing_path, sheet_name="Tier Disruption", dtype=str)

print(f"\nRepricing shape: {repricing.shape}")
print(f"Repricing columns: {repricing.columns.tolist()}")

# Check if NABP/PHARMACYNPI columns exist
if "NABP" in repricing.columns:
    print("\nFirst 10 NABP values from repricing:")
    print(repricing["NABP"].head(10))
    print("\nNABP value_counts (top 10):")
    print(repricing["NABP"].value_counts().head(10))
else:
    print("\nNABP column NOT FOUND in repricing!")

if "PHARMACYNPI" in repricing.columns:
    print("\nFirst 10 PHARMACYNPI values from repricing:")
    print(repricing["PHARMACYNPI"].head(10))
    print("\nPHARMACYNPI value_counts (top 10):")
    print(repricing["PHARMACYNPI"].value_counts().head(10))
else:
    print("\nPHARMACYNPI column NOT FOUND in repricing!")

# Sample match test
if "NABP" in repricing.columns and not repricing.empty:
    sample_nabp = repricing["NABP"].iloc[0]
    print("\n\nSample match test:")
    print(f"Sample NABP from repricing: '{sample_nabp}'")
    
    # Clean it
    sample_cleaned = str(sample_nabp).strip().upper()
    print(f"Cleaned sample NABP: '{sample_cleaned}'")
    
    # Check if it exists in network
    network_nabps = network["pharmacy_nabp"].astype(str).str.strip().str.upper()
    match = network_nabps == sample_cleaned
    if match.any():
        matched_row = network[match].iloc[0]
        print("MATCH FOUND in network!")
        print(f"Network row: {matched_row.to_dict()}")
    else:
        print(f"NO MATCH in network for '{sample_cleaned}'")
        print(f"First 5 network NABPs: {network_nabps.head().tolist()}")
