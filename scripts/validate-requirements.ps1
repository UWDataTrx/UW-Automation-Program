<#
Local helper to validate Python requirements on Windows (PowerShell).

Usage (PowerShell):
  .\scripts\validate-requirements.ps1

This script will:
 - create a virtual environment in `.venv`
 - upgrade pip
 - install `requirements-streamlit.txt` (if present)
 - install `requirements.txt`
 - run `pip check` to show dependency conflicts
#>


param(
  [string]$PythonExe = "python"
)

# Check Python executable version before creating venv
try {
  $pv = & $PythonExe --version 2>&1
} catch {
  Write-Error "Failed to run '$PythonExe --version'. Ensure the specified Python executable exists or provide a full path using -PythonExe."
  exit 1
}

Write-Host "Detected Python: $pv"
if ($pv -notlike 'Python 3.13.5*') {
  Write-Warning "This project requires Python 3.13.5. Proceeding anyway may produce different results. To use a specific Python, pass -PythonExe 'C:\path\to\python.exe'."
}

Write-Host "Creating virtual environment .venv using $PythonExe..."
& $PythonExe -m venv .venv

Write-Host "Activating virtual environment..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

if (Test-Path "requirements-streamlit.txt") {
    Write-Host "Installing requirements-streamlit.txt..."
    pip install -r requirements-streamlit.txt
}

Write-Host "Installing requirements.txt..."
pip install -r requirements.txt

Write-Host "Running pip check to detect dependency conflicts..."
pip check

Write-Host "Done. If 'pip check' reported issues, fix version pinning or remove incompatible packages."
