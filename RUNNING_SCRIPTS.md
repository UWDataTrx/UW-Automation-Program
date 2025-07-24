# Running the Automation Program

To ensure all imports work correctly, you must run processing scripts (such as `bg_disruption.py`) using the `-m` flag from the project root directory.

**Example:**

```powershell
python -m modules.bg_disruption
```

**Why?**
- This ensures Python treats the project as a package, so all internal imports (like `from utils.utils import ...`) work correctly.
- Running scripts directly (e.g., `python modules/bg_disruption.py`) may result in `ModuleNotFoundError` for local imports.

**Steps:**
1. Open a terminal and navigate to the project root folder:
   ```powershell
   cd "C:\Users\DamionMorrison\OneDrive - True Rx Health Strategists\True Community - Data Analyst\UW Python Program\UW-Automation-Program"
   ```
2. Run the script with the `-m` flag as shown above.

If you have questions, contact the project maintainer.
