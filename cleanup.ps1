# PowerShell script to clean cache, temp, log, and backup files in the workspace
Get-ChildItem -Path . -Recurse -Include *.pyc,~$*,*.tmp,*.log,*.bak | Remove-Item -Force
