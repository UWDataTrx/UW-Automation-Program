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
echo 1. Send the 'diagnostic_report.txt' file to support
echo 2. Include any specific error messages you're seeing
echo 3. Describe what you were trying to do when the problem occurred
echo.
pause
