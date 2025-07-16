#!/usr/bin/env python3
"""
Generate PDF version of the Troubleshooting Guide
=================================================

This script converts the TROUBLESHOOTING.md file to a professional PDF document.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from pathlib import Path
import re
from datetime import datetime

class TroubleshootingPDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        self.story = []
        
    def setup_custom_styles(self):
        """Setup custom paragraph styles for the PDF."""
        
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=HexColor('#2E86AB'),
            fontName='Helvetica-Bold'
        )
        
        # Main heading style
        self.heading1_style = ParagraphStyle(
            'CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            spaceBefore=20,
            textColor=HexColor('#2E86AB'),
            fontName='Helvetica-Bold',
            borderWidth=1,
            borderColor=HexColor('#2E86AB'),
            borderPadding=5
        )
        
        # Subheading style
        self.heading2_style = ParagraphStyle(
            'CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=15,
            spaceBefore=15,
            textColor=HexColor('#A23B72'),
            fontName='Helvetica-Bold'
        )
        
        # Subheading 3 style
        self.heading3_style = ParagraphStyle(
            'CustomHeading3',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
            textColor=HexColor('#F18F01'),
            fontName='Helvetica-Bold'
        )
        
        # Body text style
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        )
        
        # Code style
        self.code_style = ParagraphStyle(
            'Code',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Courier',
            textColor=HexColor('#C73E1D'),
            backColor=HexColor('#F5F5F5'),
            borderWidth=1,
            borderColor=HexColor('#CCCCCC'),
            borderPadding=8,
            spaceAfter=10
        )
        
        # List item style
        self.list_style = ParagraphStyle(
            'ListItem',
            parent=self.styles['Normal'],
            fontSize=11,
            leftIndent=20,
            bulletIndent=10,
            spaceAfter=6,
            fontName='Helvetica'
        )
        
        # Issue style (for problem descriptions)
        self.issue_style = ParagraphStyle(
            'Issue',
            parent=self.styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=HexColor('#C73E1D'),
            spaceAfter=8,
            spaceBefore=8
        )
        
        # Fix style (for solutions)
        self.fix_style = ParagraphStyle(
            'Fix',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=HexColor('#2E8B57'),
            spaceAfter=12,
            fontName='Helvetica'
        )

    def parse_markdown_file(self, filepath):
        """Parse the markdown file and convert to PDF elements."""
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
                
            # Main title (# )
            if line.startswith('# '):
                title = line[2:].strip()
                self.story.append(Paragraph(title, self.title_style))
                self.story.append(Spacer(1, 0.3*inch))
                
            # Heading 1 (## )
            elif line.startswith('## '):
                heading = line[3:].strip()
                self.story.append(Paragraph(heading, self.heading1_style))
                
            # Heading 2 (### )
            elif line.startswith('### '):
                heading = line[4:].strip()
                # Check if this is an issue/fix pattern
                if heading.startswith('Issue:'):
                    self.story.append(Paragraph(heading, self.issue_style))
                else:
                    self.story.append(Paragraph(heading, self.heading2_style))
                
            # Code blocks (```)
            elif line.startswith('```'):
                i += 1
                code_lines = []
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                
                if code_lines:
                    code_text = '\n'.join(code_lines)
                    # Escape HTML characters
                    code_text = code_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    self.story.append(Paragraph(f'<pre>{code_text}</pre>', self.code_style))
                
            # Lists (starting with numbers or -)
            elif re.match(r'^\d+\.', line) or line.startswith('- '):
                # Handle numbered or bulleted lists
                if re.match(r'^\d+\.', line):
                    text = re.sub(r'^\d+\.\s*', '', line)
                else:
                    text = line[2:].strip()
                
                # Convert markdown formatting
                text = self.convert_markdown_formatting(text)
                self.story.append(Paragraph(f'• {text}', self.list_style))
                
            # **Fix:** pattern
            elif line.startswith('**Fix:**'):
                fix_text = line[8:].strip()
                self.story.append(Paragraph(f'<b>Fix:</b> {fix_text}', self.fix_style))
                
            # Regular paragraph
            elif line and not line.startswith('#'):
                # Convert markdown formatting
                text = self.convert_markdown_formatting(line)
                
                # Special handling for checkmarks
                if '✅' in text:
                    text = text.replace('✅', '✓')
                
                self.story.append(Paragraph(text, self.body_style))
            
            i += 1
            
        # Add footer
        self.add_footer()

    def convert_markdown_formatting(self, text):
        """Convert basic markdown formatting to HTML."""
        # Bold text
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # Italic text
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        
        # Code spans
        text = re.sub(r'`(.*?)`', r'<font name="Courier" color="#C73E1D">\1</font>', text)
        
        # Links (basic)
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<link href="\2">\1</link>', text)
        
        return text

    def add_footer(self):
        """Add footer information."""
        self.story.append(Spacer(1, 0.5*inch))
        
        # Add separator line
        separator_style = ParagraphStyle(
            'Separator',
            parent=self.styles['Normal'],
            borderWidth=1,
            borderColor=HexColor('#CCCCCC'),
            spaceAfter=15
        )
        self.story.append(Paragraph('', separator_style))
        
        # Footer text
        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=HexColor('#666666'),
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        )
        
        footer_text = f"""
        <b>UW Automation Program - Troubleshooting Guide</b><br/>
        Generated on {datetime.now().strftime('%B %d, %Y')}<br/>
        For technical support, please run the diagnostic tool and include the report with your inquiry.
        """
        
        self.story.append(Paragraph(footer_text, footer_style))

    def generate_pdf(self, output_file):
        """Generate the PDF document."""
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            str(output_file),  # Convert Path to string
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Build the PDF
        doc.build(self.story)
        print(f"PDF generated successfully: {output_file}")

def main():
    """Main function to generate the PDF."""
    
    # Check if required packages are available
    try:
        import importlib.util
        spec = importlib.util.find_spec("reportlab")
        if spec is None:
            raise ImportError("reportlab not found")
    except ImportError:
        print("Error: reportlab package is required to generate PDF")
        print("Install it with: pip install reportlab")
        return False
    
    # File paths
    current_dir = Path(__file__).parent
    markdown_file = current_dir / "resources" / "TROUBLESHOOTING.md"
    output_file = current_dir / "TROUBLESHOOTING_GUIDE.pdf"
    
    # Check if markdown file exists
    if not markdown_file.exists():
        print(f"Error: Markdown file not found: {markdown_file}")
        return False
    
    try:
        # Generate PDF
        generator = TroubleshootingPDFGenerator()
        generator.parse_markdown_file(markdown_file)
        generator.generate_pdf(output_file)
        
        print("✓ Troubleshooting Guide PDF generated successfully!")
        print(f"Location: {output_file.absolute()}")
        return True
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    
    # Keep window open on Windows
    import platform
    if platform.system() == 'Windows':
        input("\nPress Enter to continue...")
