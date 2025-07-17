"""
Generate PDF from AUDIT_SYSTEM_GUIDE.md using reportlab
"""

import re
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor


def generate_audit_guide_pdf():
    """Generate PDF from the AUDIT_SYSTEM_GUIDE.md file using ReportLab."""

    # Get the current directory
    current_dir = Path(__file__).parent

    # Input and output file paths
    md_file = current_dir / "AUDIT_SYSTEM_GUIDE.md"
    pdf_file = current_dir / "AUDIT_SYSTEM_GUIDE.pdf"

    try:
        # Read the markdown file
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Create PDF document
        doc = SimpleDocTemplate(
            str(pdf_file),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        # Get styles
        styles = getSampleStyleSheet()

        # Create custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=20,
            spaceAfter=20,
            textColor=HexColor("#2c3e50"),
            alignment=1,  # Center
        )

        heading1_style = ParagraphStyle(
            "CustomHeading1",
            parent=styles["Heading1"],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=HexColor("#2c3e50"),
        )

        heading2_style = ParagraphStyle(
            "CustomHeading2",
            parent=styles["Heading2"],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=HexColor("#34495e"),
        )

        heading3_style = ParagraphStyle(
            "CustomHeading3",
            parent=styles["Heading3"],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=12,
            textColor=HexColor("#2980b9"),
        )

        code_style = ParagraphStyle(
            "Code",
            parent=styles["Code"],
            fontSize=9,
            fontName="Courier",
            backColor=HexColor("#f8f9fa"),
            borderColor=HexColor("#e9ecef"),
            borderWidth=1,
            borderPadding=10,
            leftIndent=10,
            rightIndent=10,
            spaceAfter=10,
        )

        # Story to hold document content
        story = []

        # Split content into lines
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                story.append(Spacer(1, 6))
                i += 1
                continue

            # Handle headings
            if line.startswith("# "):
                if line == "# Enhanced Audit and Error Logging System":
                    story.append(Paragraph(line[2:], title_style))
                else:
                    story.append(Paragraph(line[2:], heading1_style))
            elif line.startswith("## "):
                story.append(Paragraph(line[3:], heading2_style))
            elif line.startswith("### "):
                story.append(Paragraph(line[4:], heading3_style))
            elif line.startswith("#### "):
                story.append(Paragraph(line[5:], heading3_style))

            # Handle code blocks
            elif line.startswith("```"):
                # Find end of code block
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1

                if code_lines:
                    code_text = "\n".join(code_lines)
                    story.append(Preformatted(code_text, code_style))

            # Handle bullet points
            elif line.startswith("- "):
                bullet_text = line[2:]
                # Handle emojis and formatting
                bullet_text = re.sub(r"[✅🔧📊🆘📍🔍⚡]", "", bullet_text).strip()
                bullet_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", bullet_text)
                bullet_text = re.sub(
                    r"`(.*?)`", r'<font name="Courier">\1</font>', bullet_text
                )
                story.append(Paragraph(f"• {bullet_text}", styles["Normal"]))

            # Handle regular text
            else:
                # Clean up markdown formatting
                text = line
                text = re.sub(r"[✅🔧📊🆘📍🔍⚡]", "", text).strip()
                text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
                text = re.sub(r"`(.*?)`", r'<font name="Courier">\1</font>', text)

                if text:
                    story.append(Paragraph(text, styles["Normal"]))

            i += 1

        # Build PDF
        doc.build(story)

        print(f"✅ PDF generated successfully: {pdf_file}")
        print(f"📄 File size: {pdf_file.stat().st_size / 1024:.1f} KB")

        return str(pdf_file)

    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        return None


if __name__ == "__main__":
    generate_audit_guide_pdf()
