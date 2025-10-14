import os
import datetime
from fpdf import FPDF

ROOT_DIR = "C:/Users/DamionMorrison/OneDrive - True Rx Health Strategists/True Community - Data Analyst/UW Python Program/UW-Automation-Program"
PDF_PATH = "code_updates_today.pdf"
today = datetime.date.today()

# Map file paths to verbal documentation (fill in as needed)
verbal_docs = {
    "utils/utils.py": "Enhanced caching implementation, refactored exclusion resolver for performance and maintainability, added persistent cache helpers.",
    "modules/tier_disruption.py": "Updated to use centralized, vectorized pharmacy exclusion logic for consistency and speed.",
    "modules/bg_disruption.py": "Refactored exclusion logic to use shared utility, improving maintainability.",
    "modules/openmdf_bg.py": "Applied vectorized exclusion resolver for robust matching.",
    "modules/openmdf_tier.py": "Centralized exclusion logic, reduced code duplication.",
    "tests/test_pharmacy_exclusion.py": "Added pytest unit tests to validate mapping and cache behavior.",
    # Add more as needed
}

updated_files = []
for foldername, subfolders, filenames in os.walk(ROOT_DIR):
    for filename in filenames:
        filepath = os.path.join(foldername, filename)
        try:
            mtime = datetime.date.fromtimestamp(os.path.getmtime(filepath))
            if mtime == today and filename.endswith(('.py', '.txt', '.md')):
                updated_files.append(filepath)
        except Exception:
            continue

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.cell(0, 10, f"Code Updates for {today}", ln=True, align="C")

if not updated_files:
    pdf.cell(0, 10, "No files updated today.", ln=True)
else:
    for f in updated_files:
        rel_path = os.path.relpath(f, ROOT_DIR).replace("\\", "/")
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"File: {rel_path}", ln=True)
        pdf.set_font("Arial", size=10)
        doc = verbal_docs.get(rel_path, "Updated for bugfixes, refactoring, or feature enhancement.")
        pdf.multi_cell(0, 5, f"Summary: {doc}")
        pdf.ln(5)

pdf.output(PDF_PATH)
print(f"PDF generated: {PDF_PATH}")