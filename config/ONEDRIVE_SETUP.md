# Setting Up Your OneDrive Path for This Project

This project uses a placeholder `%OneDrive%` in its configuration to support different OneDrive folder names and locations. If you get a "Could not find OneDrive folder" or "FileNotFoundError", follow these steps:

## 1. Find Your OneDrive Folder
- Open File Explorer.
- Navigate to your user folder (e.g., `C:\Users\<YourName>\`).
- Look for a folder named `OneDrive`, `OneDrive - <Your Company>`, or similar.
- Open it and make sure it contains your project files (e.g., `True Community - Data Analyst/Medispan Export 6.27.25.xlsx`).

## 2. Set Your OneDrive Path
You have two options:

### Option A: Environment Variable
- Open PowerShell.
- Run:
  ```powershell
  $env:USER_ONEDRIVE_PATH = 'C:\Users\<YourName>\OneDrive - <Your Company>'
  ```
- To make this permanent, add it to your system/user environment variables.

### Option B: Config File
- In the `config` folder of this project, create a file named `user_onedrive_path.txt`.
- Put the full path to your OneDrive folder in that file, for example:
  ```
  C:\Users\<YourName>\OneDrive - <Your Company>
  ```

## 3. Re-run the Program
The program will now use your specified OneDrive path to resolve all file locations.

---

If you still get errors, double-check the path and make sure the required files exist in the specified location. If you need help, provide the exact error message and your OneDrive folder path.
