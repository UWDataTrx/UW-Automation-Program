# Python -m Flag Cheat Sheet

## What is the `-m` flag?
The `-m` flag tells Python to run a module or package as a script, using dot (`.`) notation instead of slashes or backslashes.

## Why use it?
- Ensures all imports work correctly in multi-file projects.
- Avoids `ModuleNotFoundError` for local modules.
- Runs code as part of the package, not as a standalone script.

## How to use
1. **Open a terminal and navigate to your project root folder.**
   ```powershell
   cd "C:\path\to\your\project-root"
   ```
2. **Run a module using the -m flag:**
   ```powershell
   python -m modules.bg_disruption
   ```
   - Use dots (`.`) for folders and file names (no `.py` extension).
   - Example for a script in `modules/tier_disruption.py`:
     ```powershell
     python -m modules.tier_disruption
     ```
   - Example for a script in the root folder (`app.py`):
     ```powershell
     python -m app
     ```

## commands for your modules

Run these from your project root:

```powershell
python -m modules.bg_disruption
python -m modules.audit_helper
python -m modules.check_audit
python -m modules.epls_lbl
python -m modules.data_processor
python -m modules.profile_runner
python -m modules.process_manager
python -m modules.openmdf_tier
python -m modules.openmdf_bg
python -m modules.mp_helpers
python -m modules.merge
python -m modules.log_manager
python -m modules.file_processor
python -m modules.error_reporter
python -m modules.error_analysis_tool
python -m modules.safe_error_analysis
python -m modules.template_processor
python -m modules.tier_disruption
python -m modules.ui_builder
```

- **Don't use slashes or backslashes:**
  - ❌ `python -m modules/bg_disruption`
  - ✅ `python -m modules.bg_disruption`
- **Don't include the `.py` extension:**
  - ❌ `python -m modules.bg_disruption.py`
  - ✅ `python -m modules.bg_disruption`

## Summary
- Always run from the project root.
- Use dot notation for module paths.
- The `-m` flag is the best way to run scripts in multi-file Python projects.
