from fpdf import FPDF

CHECKLIST = [
    "General Improvements (All Files)",
    "- Group imports: standard library, third-party, local modules.",
    "- Remove unused or duplicate imports.",
    "- Use absolute imports for clarity.",
    "- Add type hints to all function and method signatures.",
    "- Add/complete docstrings for all public functions, methods, and classes.",
    "- Move magic numbers and strings to named constants.",
    "- Use context managers for all file I/O.",
    "- Validate DataFrame columns before accessing.",
    "- Use .copy() when modifying DataFrames.",
    "- Prefer vectorized DataFrame operations over loops.",
    "- Use more specific exception types (not just Exception).",
    "- Always log or raise in exception blocks; avoid silent failures.",
    "- Use logger.exception() for full tracebacks.",
    "- Use a consistent logger name and configuration.",
    "- Consider rotating file handlers for logs.",
    "- Guard multiprocessing code with if __name__ == '__main__':.",
    "- Split large files/classes into smaller, focused modules/classes.",
    "- Group related functions into classes or modules.",
    "- Add/complete docstrings for test functions.",
    "- Use fixtures for setup/teardown in tests.",
    "",
    "app.py",
    "- Remove duplicate imports (e.g., import sys, from pathlib import Path).",
    "- Group imports and use import ... as ... for long module names.",
    "- Consider warning (not hard fail) for Python version mismatch.",
    "- Use a single config loader and cache config values.",
    "- Move UI logic out of business logic classes for better separation.",
    "- Debounce frequent UI updates.",
    "- Add type hints to all methods.",
    "- Move magic numbers (e.g., 39 for columns) to named constants.",
    "- Use context managers for all file operations.",
    "- Add context to error messages for easier debugging.",
    "- Use more specific exception types.",
    "- Refactor large classes into smaller, focused classes if possible.",
    "",
    "modules/tier_disruption.py, bg_disruption.py, openmdf_bg.py, openmdf_tier.py",
    "- Use consistent logging and error handling.",
    "- Refactor nested functions (e.g., map_excluded) to top-level for reuse.",
    "- Validate DataFrame columns before accessing.",
    "- Use config file or constants for sheet names and column lists.",
    "- Add type hints and docstrings to all functions.",
    "- Use .copy() when modifying DataFrames.",
    "- Prefer vectorized DataFrame operations.",
    "- Use more specific exception types.",
    "- Move magic numbers to named constants.",
    "",
    "modules/audit_helper.py, log_manager.py",
    "- Centralize fallback logic for audit logging.",
    "- Use more specific exception types for file/session operations.",
    "- Add type hints and docstrings.",
    "",
    "modules/file_processor.py, data_processor.py, template_processor.py",
    "- Add type hints and docstrings for all public methods.",
    "- Refactor repeated logic (e.g., file path handling) into utility functions.",
    "- Use context managers for file I/O.",
    "",
    "modules/mp_helpers.py, merge.py",
    "- Guard multiprocessing helpers with if __name__ == '__main__':.",
    "- Add comments and docstrings for clarity.",
    "",
    "modules/diagnostic_tool.py, error_reporter.py, error_analysis_tool.py",
    "- Use consistent error reporting and logging.",
    "- Add more context to error messages.",
    "- Add type hints and docstrings.",
    "",
    "modules/ui_builder.py",
    "- Separate UI logic from business logic for maintainability.",
    "- Use type hints for widget references.",
    "- Add docstrings.",
    "",
    "modules/__init__.py",
    "- Only import what is necessary for package initialization.",
    "- Add docstring describing the module/package purpose.",
    "",
    "Testing (tests/modules/*.py)",
    "- Add/complete docstrings for test functions.",
    "- Use fixtures for setup/teardown.",
    "- Ensure all test functions validate expected outcomes.",
]

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Code Quality & Maintainability Checklist', ln=True, align='C')
        self.ln(5)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, ln=True)
        self.ln(2)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        for line in body:
            if line.strip() == '':
                self.ln(3)
            elif not line.startswith('-'):
                self.chapter_title(line)
            else:
                self.multi_cell(0, 8, line)
        self.ln(2)


def generate_checklist_pdf(filename="code_quality_checklist.pdf"):
    pdf = PDF()
    pdf.add_page()
    pdf.chapter_body(CHECKLIST)
    pdf.output(filename)
    print(f"Checklist PDF generated: {filename}")

if __name__ == "__main__":
    try:
        from fpdf import FPDF
    except ImportError:
        print("Please install fpdf: pip install fpdf")
        exit(1)
    generate_checklist_pdf()
