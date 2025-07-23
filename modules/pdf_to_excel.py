import pdfplumber
import pandas as pd
import shutil

pdf_path = r"Prescription Drug Utilizatoin Top 50.pdf"
csv_path = r"Prescription_Drug_Utilization_Top_50.csv"
template_path = r"C:\Users\DamionMorrison\OneDrive - True Rx Health Strategists\True Community - Data Analyst\Repricing Templates\Savings Analysis\Claims For Analysis Template.xlsx"
output_path = (
    "Claims For Analysis Output.xlsx"  # Will be placed in the same directory as app.py
)


# Extract all tables from PDF and save as CSV
def pdf_to_csv(pdf_path, csv_path):
    # Try extracting raw text from PDF
    all_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            all_text += page.extract_text() or ""
    print("First 100 lines of extracted PDF text:")
    for i, line in enumerate(all_text.splitlines()[:100]):
        print(f"Line {i + 1}: {line}")
    # Save all text to a .txt file for manual inspection
    txt_path = "Prescription_Drug_Utilization_Top_50.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(all_text)
    print(f"Extracted PDF text saved to {txt_path}")

    # Parse lines for drug data
    import re

    drug_rows = []
    # Improved parsing: split by any whitespace and extract columns by position
    debug_count = 0
    for line in all_text.splitlines():
        # Skip header and empty lines
        if not line.strip() or line.startswith("Brand Drugs"):
            continue
        # Heuristic: line contains $ and at least two numbers
        if "$" in line and re.search(r"\b\d+\b.*\b\d+\b", line):
            parts = line.strip().split()
            if debug_count < 10:
                print(f"DEBUG LINE: {line}")
                print(f"DEBUG SPLIT: {parts}")
                debug_count += 1
            # ...existing extraction logic...
            try:
                ind_idx = next(i for i, p in enumerate(parts) if p in ["Y", "N"])
                drug_name = " ".join(parts[:ind_idx])
                num_scripts = parts[ind_idx + 2]
                paid_claims = parts[ind_idx + 4]
                paid_claims_clean = paid_claims.replace("$", """).replace(",",""")
                if drug_name and num_scripts.isdigit() and paid_claims_clean.isdigit():
                    drug_rows.append([drug_name, num_scripts, "$" + paid_claims_clean])
            except Exception:
                continue
    # Save to CSV
    df = pd.DataFrame(drug_rows, columns=["Drug Name", "Rxs", "Total Cost"])
    df.to_csv(csv_path, index=False)
    print(f"Drug data extracted and saved to {csv_path}")
    return csv_path


# Map CSV columns to Excel template columns
def csv_to_excel_template(csv_path, template_path, output_path):
    df = pd.read_csv(csv_path)
    # Copy template to output path in app.py directory
    app_dir = "c:\\Users\\DamionMorrison\\OneDrive - True Rx Health Strategists\\UW Automation Program"
    output_path_full = app_dir + "\\Claims For Analysis Output.xlsx"
    shutil.copy(template_path, output_path_full)
    # Load copied template
    template = pd.read_excel(output_path_full)
    # Insert data into template columns
    template["Drug Name"] = df["Drug Name"]
    template["Rxs"] = df["Rxs"]
    template["Total Cost"] = df["Total Cost"]
    template.to_excel(output_path_full, index=False)
    print(f"Output written to {output_path_full}")


if __name__ == "__main__":
    csv_path = pdf_to_csv(pdf_path, csv_path)
    csv_to_excel_template(csv_path, template_path, output_path)
