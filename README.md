# Repricing Automation Tool

A Python-based application designed to automate pharmacy claims repricing, generate disruption analysis (Tier, B/G, Open MDF), and produce formatted outputs including SHARx and EPLS LBL files. Built with a GUI interface using `customtkinter` for ease of use across different user roles.

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
├── app.py                     # Main GUI entry point
├── merge.py                  # Claim file merger logic
├── bg_disruption.py          # Brand/Generic disruption script
├── tier_disruption.py        # Tier-based disruption logic
├── openmdf_bg.py             # Open MDF B/G disruption
├── openmdf_tier.py           # Open MDF Tier disruption
├── sharx_lbl.py              # SHARx LBL generator
├── epls_lbl.py               # EPLS LBL generator
├── utils.py                  # Shared utility functions
├── file_paths.json           # Excel file paths configuration
├── config.json               # App state configuration
├── .gitignore                # Ignored files and folders
└── README.md                 # Project documentation
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

1. Launch the app:
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
