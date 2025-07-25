# Troubleshooting Guide: UW-Automation-Program

## Common Issues & Solutions

### 1. Python Not Found or Wrong Version
- **Symptom:** `python` or `python3` not recognized, or version < 3.9
- **Solution:**
  - Install Python 3.9 or higher from [python.org](https://www.python.org/downloads/)
  - Ensure Python is added to your system PATH

### 2. Missing Dependencies
- **Symptom:** `ModuleNotFoundError` for `pandas`, `customtkinter`, etc.
- **Solution:**
  - Activate your virtual environment
  - Run `pip install -r requirements.txt` or `poetry install`

### 3. OneDrive Path Issues
- **Symptom:** Errors about missing OneDrive environment variable or files not found
- **Solution:**
  - Make sure OneDrive is installed and running
  - Ensure the `OneDrive` environment variable is set (log out/in if needed)
  - Check your `file_paths.json` for correct paths

### 4. Excel File Errors
- **Symptom:** `PermissionError`, `FileNotFoundError`, or Excel file is locked
- **Solution:**
  - Close all open Excel files before running scripts
  - Ensure you have write permissions to the output directory

### 5. GUI Not Launching
- **Symptom:** No window appears or errors about `customtkinter`
- **Solution:**
  - Ensure all dependencies are installed
  - Try running with `python app.py` from the project root

### 6. Windows COM Errors
- **Symptom:** Errors related to Excel COM automation
- **Solution:**
  - Install `pywin32` (`pip install pywin32`)
  - Ensure Excel is installed and properly licensed

### 7. Configuration Issues
- **Symptom:** Errors about missing or invalid config files
- **Solution:**
  - Check that `config/config.json` and `config/file_paths.json` exist and are valid JSON
  - Use provided example files if available

### 8. Updating Issues
- **Symptom:** Changes from GitHub are not reflected
- **Solution:**
  - Run `git pull origin main` to update
  - If you have local changes, commit or stash them first

---

If your issue is not listed here, please open an issue on the GitHub repository or contact the maintainer.
