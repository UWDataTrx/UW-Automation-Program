# Repricing Automation Tool

A Python-based application designed to automate pharmacy claims repricing, generate disruption analysis (Tier, B/G, Open MDF), and produce formatted outputs including SHARx and EPLS LBL files.

## 🎯 Available Interfaces

This application provides multiple interfaces:

- **Desktop GUI** (`app.py`) - Built with `customtkinter` for local Windows environments
- **Web API** (`fastapi_app.py`) - RESTful API with web interface using FastAPI
- **Legacy Web** (`streamlit_app.py`) - Streamlit-based web application (deprecated, use FastAPI instead)

**Recommended:** Use the FastAPI web application for modern deployments. See [README_FASTAPI.md](README_FASTAPI.md) for details.

---

## 🧩 Features

- 🔄 **Claim File Merging** – Match reversals with origin claims and apply logic tagging.
- 📊 **Disruption Analysis** – Tier-based and brand/generic evaluations for:
  - Tier Disruption
  - B/G Disruption
  - Open MDF (Tier and B/G)
- 📥 **Template Integration** – Automatically populates `_Rx Repricing_wf.xlsx` with processed results.
- 📤 **SHARx & EPLS Line-by-Line Generators** – Create formatted `.xlsx` output from claim data.
- 🌗 **Light/Dark Theme Toggle** – Built-in UI theming for accessibility.
- 📈 **Progress Tracking & Audit Log** – Displays process progress and stores audit entries.

---

## 🗂️ Folder Structure

```
.
├── app.py                     # Desktop GUI entry point (customtkinter)
├── fastapi_app.py             # FastAPI web application (recommended)
├── streamlit_app.py           # Streamlit web app (deprecated, use FastAPI)
├── client_code/               # Core business logic modules
│   ├── merge.py              # Claim file merger logic
│   ├── bg_disruption.py      # Brand/Generic disruption script
│   ├── tier_disruption.py    # Tier-based disruption logic
│   ├── audit_helper.py       # Audit logging utilities
│   └── ...
├── modules/                   # Legacy module imports (compatibility layer)
├── utils/                     # Shared utility functions
├── config/                    # Configuration files
├── static/                    # Static web assets (HTML, CSS, JS)
├── file_paths.json           # Excel file paths configuration
├── config.json               # App state configuration
├── requirements.txt          # Core dependencies
├── requirements-fastapi.txt  # FastAPI-specific dependencies
├── pyproject.toml            # Poetry project configuration
├── .gitignore                # Ignored files and folders
├── README.md                 # This file
└── README_FASTAPI.md         # FastAPI documentation
```

---

## 🚀 Getting Started

### ✅ Requirements
- Python 3.9+
- pip dependencies (see below)

### 📦 Install Dependencies

Run this from the terminal:

```bash
pip install pandas openpyxl customtkinter plyer xlsxwriter
```

(You may also need `pywin32` if using Excel COM features on Windows.)

---

## 🖥️ Usage

### Desktop GUI

1. Launch the desktop app:
   ```bash
   python app.py
   ```

2. In the GUI:
   - Import `File 1` and `File 2`
   - Choose the disruption type
   - Select template `_Rx Repricing_wf.xlsx`
   - Start processing

3. Use the **SHARx LBL** or **EPLS LBL** buttons to generate line-by-line outputs.

4. Check `LBL for Disruption.xlsx` and `*_Claim Detail.csv` for results.

### Web API (FastAPI)

1. Launch the web application:
   ```bash
   python fastapi_app.py
   ```
   
   Or with uvicorn:
   ```bash
   uvicorn fastapi_app:app --reload --host 0.0.0.0 --port 8000
   ```

2. Open browser to `http://localhost:8000`

3. Upload files through the web interface or use the REST API

4. See [README_FASTAPI.md](README_FASTAPI.md) for complete API documentation

---

## 📁 Configuration

Customize Excel paths in `file_paths.json`:

```json
{
  "reprice": "./_Rx Repricing_wf.xlsx",
  "medi_span": "...",
  "u_disrupt": "...",
  ...
}
```

---

## 🔒 Access Control

This repo is **private**. Only authorized users with read access can view content. Write access is restricted to the owner.

---

## 📝 Audit Trail

Every run logs:
- File names
- Status
- Timestamp

Stored in `audit_log.csv`

---

## 🧼 .gitignore

This project includes a `.gitignore` to exclude:
- Logs
- Output files
- Temporary Excel or cache files

---

## 📌 Author

**Damion Morrison**  

## 📌 Contributor

**Ben Dillon**
---


## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.
