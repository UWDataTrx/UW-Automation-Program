"""
Generate comprehensive PDF documentation for the entire UW Automation Program directory
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Preformatted,
    PageBreak,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.units import inch
from datetime import datetime


def generate_project_documentation_pdf():
    """Generate comprehensive PDF documentation for the entire project."""

    # Get the project root directory (one level up from resources)
    current_dir = Path(__file__).parent
    project_root = current_dir.parent

    # Output file
    pdf_file = current_dir / "UW_Automation_Program_Documentation.pdf"

    try:
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

        # Create custom styles
        title_style = ParagraphStyle(
            "ProjectTitle",
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

        section_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=15,
            spaceBefore=25,
            textColor=HexColor("#2c3e50"),
            borderWidth=2,
            borderColor=HexColor("#3498db"),
            borderPadding=5,
        )

        # subsection_style is not used and has been removed

        file_header_style = ParagraphStyle(
            "FileHeader",
            parent=styles["Heading3"],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=12,
            textColor=HexColor("#2980b9"),
            backColor=HexColor("#ecf0f1"),
            borderWidth=1,
            borderColor=HexColor("#bdc3c7"),
            borderPadding=5,
        )

        code_style = ParagraphStyle(
            "CodeBlock",
            parent=styles["Code"],
            fontSize=8,
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

        # Title page
        story.append(Paragraph("UW Automation Program", title_style))
        story.append(Paragraph("Complete Project Documentation", subtitle_style))
        story.append(Spacer(1, 20))
        story.append(
            Paragraph(
                f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Project Location: {project_root}", styles["Normal"]))
        story.append(PageBreak())

        # Table of Contents
        story.append(Paragraph("Table of Contents", section_style))
        toc_data = [
            ["Section", "Description"],
            ["1. Project Overview", "High-level project structure and purpose"],
            ["2. Configuration Files", "JSON configs and settings"],
            ["3. Main Application", "Core application files (app.py)"],
            ["4. Modules", "Individual processing modules"],
            ["5. Utilities", "Helper functions and utilities"],
            ["6. User Interface", "UI components and builders"],
            ["7. Tests", "Test files and test configurations"],
            ["8. Resources", "Documentation and guides"],
            ["9. File Structure", "Complete directory tree"],
        ]

        toc_table = Table(toc_data, colWidths=[2 * inch, 4 * inch])
        toc_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#3498db")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), HexColor("#f8f9fa")),
                    ("GRID", (0, 0), (-1, -1), 1, black),
                ]
            )
        )
        story.append(toc_table)
        story.append(PageBreak())

        # 1. Project Overview
        story.append(Paragraph("1. Project Overview", section_style))
        story.append(
            Paragraph(
                "The UW Automation Program is a comprehensive Python-based application designed for healthcare repricing automation. It provides tools for data processing, file merging, template operations, and audit logging.",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 10))

        # Get project statistics
        total_files = 0
        python_files = 0
        config_files = 0
        test_files = 0

        for root, dirs, files in os.walk(project_root):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if not file.endswith(".pyc"):
                    total_files += 1
                    if file.endswith(".py"):
                        python_files += 1
                    elif file.endswith((".json", ".md", ".txt")):
                        config_files += 1
                    elif "test" in file.lower():
                        test_files += 1

        stats_data = [
            ["Metric", "Count"],
            ["Total Files", str(total_files)],
            ["Python Files", str(python_files)],
            ["Configuration Files", str(config_files)],
            ["Test Files", str(test_files)],
        ]

        stats_table = Table(stats_data, colWidths=[2 * inch, 1 * inch])
        stats_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#27ae60")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, black),
                ]
            )
        )
        story.append(stats_table)
        story.append(PageBreak())

        # Define file categories
        categories = {
            "2. Configuration Files": {
                "patterns": ["*.json", "*.cfg", "*.ini"],
                "directories": ["config"],
                "description": "Configuration files that control application behavior",
            },
            "3. Main Application": {
                "patterns": ["app.py", "main.py"],
                "directories": [],
                "description": "Core application entry points and main logic",
            },
            "4. Modules": {
                "patterns": ["*.py"],
                "directories": ["modules"],
                "description": "Individual processing modules and components",
            },
            "5. Utilities": {
                "patterns": ["*.py"],
                "directories": ["utils"],
                "description": "Helper functions and utility modules",
            },
            "6. User Interface": {
                "patterns": ["*.py"],
                "directories": ["ui"],
                "description": "User interface components and builders",
            },
            "7. Tests": {
                "patterns": ["test_*.py", "*_test.py"],
                "directories": ["tests"],
                "description": "Test files and test configurations",
            },
            "8. Resources": {
                "patterns": ["*.md", "*.txt", "*.pdf"],
                "directories": ["resources", "docs"],
                "description": "Documentation, guides, and resource files",
            },
        }

        # Process each category
        for category_name, category_info in categories.items():
            story.append(Paragraph(category_name, section_style))
            story.append(Paragraph(category_info["description"], styles["Normal"]))
            story.append(Spacer(1, 10))

            # Find files in this category
            category_files = []

            # Check specific directories
            for dir_name in category_info["directories"]:
                dir_path = project_root / dir_name
                if dir_path.exists():
                    for file_path in dir_path.rglob("*"):
                        if file_path.is_file() and not file_path.name.endswith(".pyc"):
                            category_files.append(file_path)

            # Check patterns in root directory
            if not category_info["directories"]:
                for pattern in category_info["patterns"]:
                    for file_path in project_root.glob(pattern):
                        if file_path.is_file():
                            category_files.append(file_path)

            # Sort files
            category_files.sort(key=lambda x: x.name)

            # Add files to documentation
            for file_path in category_files[
                :15
            ]:  # Limit to first 15 files per category
                add_file_to_story(
                    story,
                    file_path,
                    project_root,
                    file_header_style,
                    code_style,
                    styles,
                )

            if len(category_files) > 15:
                story.append(
                    Paragraph(
                        f"... and {len(category_files) - 15} more files in this category",
                        styles["Italic"],
                    )
                )

            story.append(PageBreak())

        # 9. Complete File Structure
        story.append(Paragraph("9. Complete File Structure", section_style))
        story.append(
            Paragraph("Complete directory tree of the project:", styles["Normal"])
        )
        story.append(Spacer(1, 10))

        tree_text = generate_directory_tree(project_root)
        story.append(Preformatted(tree_text, code_style))

        # Build PDF
        doc.build(story)

        print("✅ Comprehensive project documentation generated successfully!")
        print(f"📄 File: {pdf_file}")
        print(f"📊 Size: {pdf_file.stat().st_size / 1024:.1f} KB")
        print(f"📋 Documented {total_files} files across {len(categories)} categories")

        return str(pdf_file)

    except Exception as e:
        print(f"❌ Error generating documentation: {e}")
        return None


def add_file_to_story(
    story, file_path, project_root, file_header_style, code_style, styles
):
    """Add a file's content to the documentation story."""
    relative_path = file_path.relative_to(project_root)

    # File header
    story.append(Paragraph(f"📄 {relative_path}", file_header_style))

    try:
        # Read file content
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Limit content length
        if len(content) > 3000:
            content = content[:3000] + "\n\n... (content truncated) ..."

        # Add content based on file type
        if file_path.suffix == ".py":
            # Python files - show with syntax
            story.append(Paragraph("<b>Type:</b> Python Module", styles["Normal"]))
            story.append(Spacer(1, 5))
            story.append(Preformatted(content, code_style))
        elif file_path.suffix == ".json":
            # JSON files
            story.append(Paragraph("<b>Type:</b> Configuration File", styles["Normal"]))
            story.append(Spacer(1, 5))
            story.append(Preformatted(content, code_style))
        elif file_path.suffix in [".md", ".txt"]:
            # Markdown/text files
            story.append(Paragraph("<b>Type:</b> Documentation", styles["Normal"]))
            story.append(Spacer(1, 5))
            # Convert basic markdown to paragraphs
            for line in content.split("\n"):
                if line.strip():
                    if line.startswith("#"):
                        text = line.lstrip("#").strip()
                        story.append(Paragraph(f"<b>{text}</b>", styles["Heading4"]))
                    else:
                        story.append(Paragraph(line, styles["Normal"]))
                else:
                    story.append(Spacer(1, 6))
        else:
            story.append(
                Paragraph(
                    f"<b>Type:</b> {file_path.suffix.upper()} File", styles["Normal"]
                )
            )
            story.append(
                Paragraph(
                    "Binary or special file - content not displayed", styles["Italic"]
                )
            )

        story.append(Spacer(1, 15))

    except Exception as e:
        story.append(
            Paragraph(f"<b>Error reading file:</b> {str(e)}", styles["Normal"])
        )
        story.append(Spacer(1, 10))


def generate_directory_tree(path, prefix="", max_depth=3, current_depth=0):
    """Generate a text representation of the directory tree."""
    if current_depth >= max_depth:
        return ""

    tree = ""
    path = Path(path)

    try:
        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))

        for i, item in enumerate(items):
            if item.name.startswith(".") or item.name == "__pycache__":
                continue

            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            tree += f"{prefix}{current_prefix}{item.name}\n"

            if item.is_dir() and current_depth < max_depth - 1:
                extension = "    " if is_last else "│   "
                tree += generate_directory_tree(
                    item, prefix + extension, max_depth, current_depth + 1
                )

    except PermissionError:
        tree += f"{prefix}└── [Permission Denied]\n"

    return tree


if __name__ == "__main__":
    generate_project_documentation_pdf()
