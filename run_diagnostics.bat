@echo off
REM UW Automation Program - Diagnostic Tool Launcher
REM This batch file runs the diagnostic tool to help troubleshoot issues

echo UW Automation Program - Diagnostic Tool
echo =========================================
echo.
echo This tool will collect system information to help diagnose issues.
echo The report will be saved as 'diagnostic_report.txt'.
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

REM Check for required packages and install if needed
echo Checking for required packages...
python -c "import psutil" 2>nul
if errorlevel 1 (
    echo Installing psutil package...
    pip install psutil
    if errorlevel 1 (
        echo WARNING: Could not install psutil - some system checks will be limited
        echo Continuing with diagnostic...
    )
)

REM Run the diagnostic tool
echo Running diagnostic checks...
echo.
python diagnostic_tool.py

REM Check if the tool ran successfully
if errorlevel 1 (
    echo.
    echo ERROR: Diagnostic tool encountered an error
    echo Please check the output above for details
) else (
    echo.
    echo Diagnostic completed successfully!
    echo Report saved as 'diagnostic_report.txt'
)

echo.
echo To get help with any issues found:
echo 1. Check the output above to confirm if your report was uploaded to support
echo 2. If upload succeeded, your report is automatically available to support
echo 3. If upload failed, please manually send the 'diagnostic_report.txt' file
echo 4. For immediate assistance, contact support with details about:
echo    - What you were trying to do when the problem occurred
echo    - Any specific error messages you saw
echo    - When the problem started
echo.
pause
