"""
Generate PDF from repricing_walkthrough.md using reportlab for consistent formatting
"""

import re
from datetime import datetime
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer)


def generate_walkthrough_pdf():
    """Generate PDF from the repricing_walkthrough.md file using ReportLab."""

    # Get the current directory
    current_dir = Path(__file__).parent

    # Input and output file paths
    md_file = current_dir / "repricing_walkthrough.md"
    pdf_file = current_dir / "repricing_walkthrough.pdf"

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
            bottomMargin=72,
        )

        # Get styles
        styles = getSampleStyleSheet()

        # Create custom styles matching your project documentation
        title_style = ParagraphStyle(
            "WalkthroughTitle",
            parent=styles["Title"],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor("#2c3e50"),
            alignment=1,  # Center
        )

        subtitle_style = ParagraphStyle(
            "Subtitle",
            parent=styles["Heading1"],
            fontSize=14,
            spaceAfter=20,
            textColor=HexColor("#7f8c8d"),
            alignment=1,  # Center
        )

        heading1_style = ParagraphStyle(
            "CustomHeading1",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=15,
            spaceBefore=25,
            textColor=HexColor("#2c3e50"),
            borderWidth=2,
            borderColor=HexColor("#3498db"),
            borderPadding=5,
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

        bullet_style = ParagraphStyle(
            "BulletList",
            parent=styles["Normal"],
            leftIndent=20,
            bulletIndent=10,
            spaceAfter=5,
        )

        # Story to hold document content
        story = []

        # Title page
        story.append(Paragraph("UW Automation Program", title_style))
        story.append(Paragraph("Repricing Walkthrough Guide", subtitle_style))
        story.append(Spacer(1, 20))
        story.append(
            Paragraph(
                f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
                styles["Normal"],
            )
        )
        story.append(PageBreak())

        # Split content into lines
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                story.append(Spacer(1, 6))
                i += 1
                continue

            # Clean text function
            line = clean_text(line)

            # Handle headings
            if line.startswith("# "):
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

            # Handle bullet points and numbered lists
            elif line.startswith("- ") or line.startswith("* "):
                bullet_text = line[2:].strip()
                # Handle markdown formatting in bullets
                bullet_text = format_markdown_text(bullet_text)
                story.append(Paragraph(f"• {bullet_text}", bullet_style))
            elif re.match(r"^\d+\.\s", line):
                # Numbered list
                list_text = re.sub(r"^\d+\.\s", "", line)
                list_text = format_markdown_text(list_text)
                story.append(
                    Paragraph(f"{line.split('.')[0]}. {list_text}", bullet_style)
                )

            # Handle indented content
            elif line.startswith("    "):
                indented_text = line[4:]
                indented_text = format_markdown_text(indented_text)
                story.append(Paragraph(f"    {indented_text}", styles["Normal"]))

            # Handle regular text
            else:
                # Format markdown text
                text = format_markdown_text(line)
                if text:
                    story.append(Paragraph(text, styles["Normal"]))

            i += 1

        # Build PDF
        doc.build(story)

        print("✅ Repricing walkthrough PDF generated successfully!")
        print(f"📄 File: {pdf_file}")
        print(f"📊 Size: {pdf_file.stat().st_size / 1024:.1f} KB")

        return str(pdf_file)

    except Exception as e:
        print(f"❌ Error generating walkthrough PDF: {e}")
        return None


def clean_text(text):
    """Clean text by replacing unicode characters with standard ones."""
    # Replace en dash and other unicode dashes with hyphen
    text = re.sub(r"[\u2013\u2014\u2012]", "-", text)
    # Replace curly quotes with straight quotes
    text = text.replace(""", '"').replace(""", '"').replace("'", "'").replace("'", "'")
    return text


def format_markdown_text(text):
    """Format basic markdown syntax in text - simplified to avoid conflicts."""
    # Just clean the text and handle basic bold
    text = clean_text(text)

    # Only handle non-overlapping bold text
    text = re.sub(r"\*\*([^*]+?)\*\*", r"<b>\1</b>", text)

    # Remove other markdown formatting to avoid conflicts
    text = re.sub(r"`([^`]+?)`", r"\1", text)  # Remove code backticks
    text = re.sub(r"[*_]", "", text)  # Remove remaining asterisks and underscores

    return text


if __name__ == "__main__":
    generate_walkthrough_pdf()
