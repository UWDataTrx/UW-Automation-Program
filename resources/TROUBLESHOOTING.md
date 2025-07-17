# UW Automation Program - Troubleshooting Guide

## For Users Experiencing Problems

If you're having issues with the UW Automation Program, please follow these steps to help us diagnose the problem:

### Step 1: Run the Diagnostic Tool

1. **Navigate to the program folder** where you have the UW Automation Program files
2. **Double-click on `run_diagnostics.bat`** (Windows users)
   - OR run `python diagnostic_tool.py` from command line
3. **Wait for the diagnostic to complete** (usually 30-60 seconds)
4. **Find the generated `diagnostic_report.txt` file** in the same folder

### Step 2: Review the Report

The diagnostic tool will check for:
- ✅ Python installation and version
- ✅ Required packages (pandas, xlwings, etc.)
- ✅ Excel COM interface availability
- ✅ System resources (disk space, memory)
- ✅ File permissions
- ✅ Running processes that might conflict
- ✅ Configuration files
- ✅ Recent error logs

### Step 3: Automatic Report Submission

✅ **Your diagnostic report is automatically sent to support!**

When you run the diagnostic tool, it will:
- Generate a detailed report of your system
- **Automatically upload it to the support team**
- Create a summary file for quick review
- Show you a unique filename for reference

If you need immediate assistance, please contact support with:

1. **The unique filename** shown in the diagnostic results
2. **Specific error messages** you're seeing (screenshots help!)
3. **What you were trying to do** when the problem occurred
4. **When the problem started** (today, last week, after an update, etc.)

## Common Issues and Quick Fixes

### Issue: "Excel COM interface unavailable"
**Fix:** 
- Ensure Microsoft Excel is installed
- Run: `pip install xlwings`
- Then run: `xlwings addin install`

### Issue: "Missing packages"
**Fix:** Install missing packages using pip:
```
pip install pandas numpy openpyxl xlwings customtkinter
```

### Issue: "Low disk space"
**Fix:** 
- Free up at least 1GB of disk space
- Delete temporary files
- Move large files to external storage

### Issue: "Excel files are locked"
**Fix:**
- Close Excel completely
- End any Excel processes in Task Manager
- Make sure no other programs are using the Excel files

### Issue: "Permission denied" errors
**Fix:**
- Run as Administrator
- OR move files to a folder you have write access to (like Documents)

### Issue: "Multiple Excel processes detected"
**Fix:**
- Open Task Manager (Ctrl+Shift+Esc)
- End all Excel.exe processes
- Wait 30 seconds before running the automation again

### Issue: Python version too old
**Fix:**
- Download and install Python 3.8 or newer from https://python.org
- Make sure to check "Add Python to PATH" during installation

## Getting Additional Help

If the diagnostic tool shows issues but you can't resolve them:

1. **Email the diagnostic report** to: [your support email]
2. **Include screenshots** of any error messages
3. **Describe your system setup**: Windows version, Excel version, etc.
4. **List recent changes**: New software installs, Windows updates, etc.

## Running the Diagnostic Tool Manually

If the batch file doesn't work, you can run the diagnostic manually:

1. Open Command Prompt or PowerShell
2. Navigate to the program folder:
   ```
   cd "C:\path\to\UW-Automation-Program"
   ```
3. Run the diagnostic:
   ```
   python diagnostic_tool.py
   ```

## System Requirements Reminder

- **Operating System:** Windows 10 or newer
- **Python:** Version 3.8 or newer
- **Microsoft Excel:** 2016 or newer (with COM interface enabled)
- **Memory:** 4GB RAM minimum, 8GB recommended
- **Disk Space:** 2GB free space minimum
- **Permissions:** Administrator rights may be required for some operations

## Prevention Tips

To avoid common issues:

1. **Keep Excel closed** when running the automation
2. **Run only one instance** of the automation at a time
3. **Ensure adequate disk space** before processing large files
4. **Keep Python and packages updated** regularly
5. **Don't modify template files** unless instructed
6. **Use recommended file formats** (XLSX for Excel files)

---

*This diagnostic tool was created to help identify and resolve common issues with the UW Automation Program. If you continue to experience problems after following these steps, please contact support with your diagnostic report.*
