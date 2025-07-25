# User Setup Guide for UW-Automation-Program

## 1. Prerequisites
- Python 3.9 or higher (3.13+ recommended)
- Git (for cloning the repository)
- (Recommended) A virtual environment tool: `venv` or `Poetry`

## 2. Clone the Repository
```bash
git clone https://github.com/UWDataTrx/UW-Automation-Program.git
cd UW-Automation-Program
```

## 3. Set Up a Virtual Environment
### Using venv (pip):
```bash
python -m venv venv
# Activate (Windows)
venv\Scripts\activate
# Activate (Mac/Linux)
source venv/bin/activate
```

### Using Poetry:
```bash
pip install poetry
poetry install
poetry shell
```

## 4. Install Dependencies
### With pip:
```bash
pip install -r requirements.txt
```
### With Poetry:
```bash
poetry install
```

## 5. Configuration
- Copy or edit the config files in the `config/` directory as needed.
- Ensure `file_paths.json` and `config.json` are present and correctly set up for your environment.
- If your workflow uses OneDrive, make sure the OneDrive environment variable is set up on your system.

## 6. Running the Application
- For the GUI: `python app.py`
- For disruption scripts: `python bg_disruption.py`, `python tier_disruption.py`, etc.
- For LBL generation: `python sharx_lbl.py` or `python epls_lbl.py`

## 7. Updating
- To get the latest changes:
```bash
git pull origin main
```

## 8. Additional Notes
- For Windows users, you may need to install `pywin32` for Excel COM features.
- If you encounter issues, see `TROUBLESHOOTING.md`.
