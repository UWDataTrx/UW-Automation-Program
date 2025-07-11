"""
Generate PDF from AUDIT_SYSTEM_GUIDE.md
"""

import markdown
from weasyprint import HTML
from pathlib import Path

def generate_audit_guide_pdf():
    """Generate PDF from the AUDIT_SYSTEM_GUIDE.md file."""
    
    # Get the current directory
    current_dir = Path(__file__).parent
    
    # Input and output file paths
    md_file = current_dir / "AUDIT_SYSTEM_GUIDE.md"
    pdf_file = current_dir / "AUDIT_SYSTEM_GUIDE.pdf"
    
    try:
        # Read the markdown file
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Convert markdown to HTML
        html_content = markdown.markdown(
            md_content, 
            extensions=['codehilite', 'fenced_code', 'tables', 'toc']
        )
        
        # Create a complete HTML document with styling
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Enhanced Audit and Error Logging System Guide</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    margin: 40px;
                    color: #333;
                    max-width: 800px;
                }}
                
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                    margin-top: 30px;
                }}
                
                h2 {{
                    color: #34495e;
                    border-bottom: 2px solid #ecf0f1;
                    padding-bottom: 5px;
                    margin-top: 25px;
                }}
                
                h3 {{
                    color: #2980b9;
                    margin-top: 20px;
                }}
                
                h4 {{
                    color: #27ae60;
                    margin-top: 15px;
                }}
                
                code {{
                    background-color: #f8f9fa;
                    padding: 2px 4px;
                    border-radius: 3px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    color: #d63384;
                }}
                
                pre {{
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 5px;
                    padding: 15px;
                    overflow-x: auto;
                    margin: 15px 0;
                }}
                
                pre code {{
                    background-color: transparent;
                    color: #212529;
                    padding: 0;
                }}
                
                ul, ol {{
                    margin: 10px 0;
                    padding-left: 25px;
                }}
                
                li {{
                    margin: 5px 0;
                }}
                
                blockquote {{
                    border-left: 4px solid #3498db;
                    margin: 15px 0;
                    padding: 10px 20px;
                    background-color: #f8f9fa;
                }}
                
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 15px 0;
                }}
                
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                
                .emoji {{
                    font-size: 1.2em;
                }}
                
                /* Page break before major sections */
                h1 {{
                    page-break-before: always;
                }}
                
                h1:first-child {{
                    page-break-before: avoid;
                }}
                
                /* Avoid breaking code blocks */
                pre {{
                    page-break-inside: avoid;
                }}
                
                @page {{
                    margin: 1in;
                    @bottom-center {{
                        content: "Page " counter(page) " of " counter(pages);
                        font-size: 10px;
                        color: #666;
                    }}
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Generate PDF using WeasyPrint
        HTML(string=full_html).write_pdf(str(pdf_file))
        
        print(f"✅ PDF generated successfully: {pdf_file}")
        print(f"📄 File size: {pdf_file.stat().st_size / 1024:.1f} KB")
        
        return str(pdf_file)
        
    except ImportError:
        print("❌ Missing required packages. Please install:")
        print("pip install markdown weasyprint")
        return None
        
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        return None

if __name__ == "__main__":
    generate_audit_guide_pdf()
