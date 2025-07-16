@echo off
REM Generate PDF version of Troubleshooting Guide
REM This batch file creates a PDF from the troubleshooting markdown file

echo UW Automation Program - PDF Generator
echo =======================================
echo.
echo Generating PDF version of the Troubleshooting Guide...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or newer from https://python.org
    echo.
    pause
    exit /b 1
)

REM Install reportlab if needed
echo Checking for required packages...
python -c "import reportlab" 2>nul
if errorlevel 1 (
    echo Installing reportlab package...
    pip install reportlab
    if errorlevel 1 (
        echo ERROR: Failed to install reportlab package
        echo Please check your internet connection and try again
        echo.
        pause
        exit /b 1
    )
)

REM Generate the PDF
echo Generating PDF...
python generate_troubleshooting_pdf.py

REM Check if the PDF was created successfully
if exist "TROUBLESHOOTING_GUIDE.pdf" (
    echo.
    echo ✓ PDF generated successfully!
    echo File: TROUBLESHOOTING_GUIDE.pdf
    echo.
    echo Opening PDF viewer...
    start "" "TROUBLESHOOTING_GUIDE.pdf"
) else (
    echo.
    echo ERROR: PDF generation failed
    echo Please check the output above for error details
)

echo.
pause
