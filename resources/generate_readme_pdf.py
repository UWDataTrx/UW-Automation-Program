from fpdf import FPDF
import re

with open("README.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()


def clean_text(text):
    # Replace en dash and other unicode dashes with hyphen
    text = re.sub(r"[\u2013\u2014\u2012]", "-", text)
    # Replace curly quotes with straight quotes
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    # Remove emoji and non-ascii characters
    text = re.sub(r"[^\x00-\x7F]+", "", text)
    return text


pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.set_font("Arial", size=12)

for line in lines:
    line = clean_text(line)
    if line.startswith("# "):
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, line[2:].strip(), ln=True)
        pdf.set_font("Arial", size=12)
    elif line.startswith("## "):
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, line[3:].strip(), ln=True)
        pdf.set_font("Arial", size=12)
    elif line.startswith("### "):
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, line[4:].strip(), ln=True)
        pdf.set_font("Arial", size=12)
    elif line.startswith("- ") or line.startswith("1.") or line.startswith("    "):
        pdf.multi_cell(0, 8, line.strip())
    elif line.strip() == "":
        pdf.ln(2)
    else:
        pdf.multi_cell(0, 8, line.strip())

pdf.output("README.pdf")
print("PDF created: README.pdf")
