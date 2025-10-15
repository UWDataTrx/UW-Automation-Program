"""Quick diagnostic script to test standardization functions."""
import pandas as pd
from config.config_loader import ConfigLoader
from utils.utils import standardize_pharmacy_ids, standardize_network_ids

# Load file paths
file_paths = ConfigLoader.load_file_paths()

# Load claims data
try:
    claims_df = pd.read_excel(file_paths["reprice"], sheet_name="Claims Table")
except Exception:
    claims_df = pd.read_excel(file_paths["reprice"], sheet_name=0)
print("\n=== CLAIMS DATA BEFORE STANDARDIZATION ===")
print(f"Total rows: {len(claims_df)}")
print("\nNABP sample (first 10):")
print(claims_df["NABP"].head(10).tolist())
print(f"\nNABP dtypes: {claims_df['NABP'].dtype}")
print("\nPHARMACYNPI sample (first 10):")
print(claims_df["PHARMACYNPI"].head(10).tolist())
print(f"\nPHARMACYNPI dtypes: {claims_df['PHARMACYNPI'].dtype}")
print(f"\nNABP NaN count: {claims_df['NABP'].isna().sum()}")
print(f"PHARMACYNPI NaN count: {claims_df['PHARMACYNPI'].isna().sum()}")

# Standardize
standardized_claims = standardize_pharmacy_ids(claims_df.copy())
print("\n=== CLAIMS DATA AFTER STANDARDIZATION ===")
print("\nNABP sample (first 10):")
print(standardized_claims["NABP"].head(10).tolist())
print(f"\nNABP dtypes: {standardized_claims['NABP'].dtype}")
print("\nPHARMACYNPI sample (first 10):")
print(standardized_claims["PHARMACYNPI"].head(10).tolist())
print(f"\nPHARMACYNPI dtypes: {standardized_claims['PHARMACYNPI'].dtype}")

# Load network data
network_df = pd.read_csv(file_paths["n_disrupt"])
print("\n\n=== NETWORK DATA BEFORE STANDARDIZATION ===")
print(f"Total rows: {len(network_df)}")
print("\npharmacy_nabp sample (first 10):")
print(network_df["pharmacy_nabp"].head(10).tolist())
print(f"\npharmacy_nabp dtypes: {network_df['pharmacy_nabp'].dtype}")
print("\npharmacy_npi sample (first 10):")
print(network_df["pharmacy_npi"].head(10).tolist())
print(f"\npharmacy_npi dtypes: {network_df['pharmacy_npi'].dtype}")
print(f"\npharmacy_nabp NaN count: {network_df['pharmacy_nabp'].isna().sum()}")
print(f"pharmacy_npi NaN count: {network_df['pharmacy_npi'].isna().sum()}")

# Standardize
standardized_network = standardize_network_ids(network_df.copy())
print("\n=== NETWORK DATA AFTER STANDARDIZATION ===")
print("\npharmacy_nabp sample (first 10):")
print(standardized_network["pharmacy_nabp"].head(10).tolist())
print("\npharmacy_nabp dtypes: {standardized_network['pharmacy_nabp'].dtype}")
print("\npharmacy_npi sample (first 10):")  # noqa: F541
print(standardized_network["pharmacy_npi"].head(10).tolist())
print(f"\npharmacy_npi dtypes: {standardized_network['pharmacy_npi'].dtype}")

# Check for matches
print("\n\n=== MATCHING TEST ===")
# Try to match first 5 claims NABPs with network
for idx, nabp in enumerate(standardized_claims["NABP"].head(5).tolist()):
    matches = standardized_network[standardized_network["pharmacy_nabp"] == nabp]
    print(f"\nClaim NABP: '{nabp}' | Matches in network: {len(matches)}")
    if len(matches) > 0:
        print(f"  Network pharmacy_nabp values that matched: {matches['pharmacy_nabp'].tolist()}")
        print(f"  Network pharmacy_is_excluded values: {matches['pharmacy_is_excluded'].tolist()}")
