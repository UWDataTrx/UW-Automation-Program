import pandas as pd

# --- Load Combined Parquet File ---

# Use absolute path for Results_combined.parquet
parquet_path = r"C:\Users\DamionMorrison\OneDrive - True Rx Health Strategists\True Community - Data Analyst\UW Python Program\UW-Automation-Program\B.o.B\modules\Results_combined.parquet"
print(f"[INFO] Attempting to load Parquet file: {parquet_path}")
try:
    data = pd.read_parquet(parquet_path)
    if "affiliate_ingred_cost" in data.columns and "affiliate_disp_fee" in data.columns:
        data["gross_cost"] = data["affiliate_ingred_cost"].fillna(0) + data[
            "affiliate_disp_fee"
        ].fillna(0)
    else:
        print(
            "[WARNING] affiliate_ingred_cost or affiliate_disp_fee column missing; gross_cost will not be available."
        )
    print(f"[SUCCESS] Loaded Parquet file with {len(data)} rows.")
except Exception as e:
    data = pd.DataFrame()
    print(f"[ERROR] Failed to load Parquet file: {e}")

# --- Claims For Analysis CSV Integration ---
claims_path = r"C:\Users\DamionMorrison\OneDrive - True Rx Health Strategists\True Community - Data Analyst\UW Python Program\UW-Automation-Program\Claims For Analysis.csv"
print(f"[INFO] Attempting to read claims file: {claims_path}")
try:
    claims_df = pd.read_csv(claims_path, dtype=str)
    print(f"[SUCCESS] Claims file loaded with {len(claims_df)} rows.")
except Exception as e:
    print(f"[ERROR] Failed to read claims file: {e}")
    claims_df = None

if claims_df is not None and not data.empty:
    print(
        "[INFO] Processing claims file for pricing update (Drug Name or NDC match) using fast vectorized merge..."
    )
    # Normalize drug names and NDCs in both DataFrames
    claims_df["drug_name_norm"] = (
        claims_df["Drug Name"].astype(str).str.lower().str.strip()
    )
    import re

    def clean_ndc(val):
        if pd.isnull(val):
            return ""
        # Remove decimal and leading zeros
        s = str(val).strip()
        s = re.sub(r"\.0+$", "", s)  # Remove .0 if present
        s = s.lstrip("0")
        return s

    if "NDC" in claims_df.columns:
        claims_df["ndc_norm"] = claims_df["NDC"].apply(clean_ndc)
    data["drug_name_norm"] = data["drug_name"].astype(str).str.lower().str.strip()
    if "ndc" in data.columns:
        data["ndc_norm"] = data["ndc"].apply(clean_ndc)
    # Debug: Show samples of normalized keys
    print(
        "[DEBUG] Sample normalized drug_name_norm in claims:",
        claims_df["drug_name_norm"].drop_duplicates().head(10).tolist(),
    )
    if "ndc_norm" in claims_df.columns:
        print(
            "[DEBUG] Sample normalized ndc_norm in claims:",
            claims_df["ndc_norm"].drop_duplicates().head(10).tolist(),
        )
    print(
        "[DEBUG] Sample normalized drug_name_norm in data:",
        data["drug_name_norm"].drop_duplicates().head(10).tolist(),
    )
    if "ndc_norm" in data.columns:
        print(
            "[DEBUG] Sample normalized ndc_norm in data:",
            data["ndc_norm"].drop_duplicates().head(10).tolist(),
        )
    # Step 1: Try to match on NDC (most precise)
    merged = claims_df.copy()
    merged["gross_cost"] = None
    if "ndc_norm" in claims_df.columns and "ndc_norm" in data.columns:
        ndc_map = data.drop_duplicates("ndc_norm").set_index("ndc_norm")["gross_cost"]
        merged["gross_cost"] = merged["ndc_norm"].map(ndc_map)
        print(
            f"[DEBUG] Number of rows with matched gross_cost by NDC: {(~merged['gross_cost'].isna()).sum()} out of {len(merged)}"
        )
    # Step 2: For rows with no match, try to match on drug name
    mask_no_match = merged["gross_cost"].isna()
    drug_map = data.drop_duplicates("drug_name_norm").set_index("drug_name_norm")[
        "gross_cost"
    ]
    merged.loc[mask_no_match, "gross_cost"] = merged.loc[
        mask_no_match, "drug_name_norm"
    ].map(drug_map)
    print(
        f"[DEBUG] Number of rows with matched gross_cost after drug name fallback: {(~merged['gross_cost'].isna()).sum()} out of {len(merged)}"
    )
    # Fill Total Cost
    total_cost_col = None
    for col in claims_df.columns:
        if col.strip().lower().replace("_", "").replace(" ", "") == "totalcost":
            total_cost_col = col
            break
    if total_cost_col is None:
        print(
            "[ERROR] Could not find a 'Total Cost' column in Claims For Analysis.csv."
        )
    else:
        merged[total_cost_col] = merged["gross_cost"].where(
            merged["gross_cost"].notnull(), "N/A"
        )
        output_path = claims_path.replace(".csv", "_wf.csv")
        merged.drop(
            ["drug_name_norm", "ndc_norm", "gross_cost"],
            axis=1,
            inplace=True,
            errors="ignore",
        )
        merged.to_csv(output_path, index=False)
        print(
            f"[SUCCESS] Output written to '{output_path}' with {len(merged)} rows. 'Total Cost' column updated."
        )
