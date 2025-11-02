# UW Automation Program - Streamlit Web App

## 🌐 Live Demo
This app is deployed on Streamlit Community Cloud.

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.9 or higher
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/UWDataTrx/UW-Automation-Program.git
cd UW-Automation-Program
```

2. Install dependencies:
```bash
pip install -r requirements-streamlit.txt
```

3. Run the app:
```bash
streamlit run streamlit_app.py
```

4. Open your browser to `http://localhost:8501`

## 📋 Features

### Current Features
- ✅ **Claim File Repricing** - Upload and merge claim files with reversal matching
- ✅ **Real-time Processing** - See progress as files are processed
- ✅ **Download Results** - Get merged Excel and CSV files
- ✅ **Audit Logging** - Track all file processing activities

### Coming Soon
- 🚧 Tier Disruption Analysis
- 🚧 Brand/Generic Disruption Analysis
- 🚧 SHARx LBL Generator
- 🚧 EPLS LBL Generator

## 🎯 Usage

### Processing Claim Files

1. Navigate to **Claim Repricing** in the sidebar
2. Upload **File 1** (the file you uploaded to the tool)
3. Upload **File 2** (the file you received from the tool)
4. Optionally upload a template file
5. Click **Start Processing**
6. Wait for processing to complete (typically 2-5 minutes)
7. Download your results

### File Requirements
- **Accepted formats**: Excel (.xlsx) or CSV (.csv)
- **Maximum file size**: 200MB
- **Required columns**: See documentation for column requirements

## 🔒 Security & Privacy

- All file processing happens in temporary directories
- Files are automatically cleaned up after processing
- No data is permanently stored on the server
- Secure HTTPS connection (when deployed)

## 📦 Deployment to Streamlit Community Cloud

### Prerequisites
1. GitHub account
2. Streamlit Community Cloud account (free at streamlit.io)

### Steps

1. Fork or clone this repository to your GitHub account

2. Go to [share.streamlit.io](https://share.streamlit.io)

3. Click "New app"

4. Configure deployment:
   - **Repository**: UWDataTrx/UW-Automation-Program
   - **Branch**: main (or your branch)
   - **Main file path**: streamlit_app.py
   - **Python version**: 3.9

5. Click "Deploy!"

6. Wait for deployment (typically 2-5 minutes)

### Configuration Files

The following files configure the Streamlit deployment:

- `streamlit_app.py` - Main application file
- `requirements-streamlit.txt` - Python dependencies
- `.streamlit/config.toml` - Streamlit configuration

## 🛠️ Development

### Project Structure
```
UW-Automation-Program/
├── streamlit_app.py          # Main Streamlit app
├── requirements-streamlit.txt # Streamlit dependencies
├── .streamlit/
│   └── config.toml           # Streamlit config
├── modules/                  # Core business logic
│   ├── merge.py             # File merging
│   ├── audit_helper.py      # Audit logging
│   └── ...
├── utils/                    # Utility functions
└── config/                   # Configuration files
```

### Adding New Features

1. Create your feature in the appropriate module (e.g., `modules/`)
2. Add UI elements in `streamlit_app.py`
3. Test locally with `streamlit run streamlit_app.py`
4. Update requirements if needed
5. Commit and push to trigger redeployment

## 🐛 Troubleshooting

### Common Issues

**Issue**: "ModuleNotFoundError"
- **Solution**: Make sure all dependencies are in `requirements-streamlit.txt`

**Issue**: "File too large"
- **Solution**: Streamlit Cloud has a 200MB file limit. Process smaller files or use local deployment.

**Issue**: "Processing takes too long"
- **Solution**: Streamlit Cloud free tier has resource limits. Consider upgrading or local deployment.

### Logs

View logs in Streamlit Cloud:
1. Go to your app dashboard
2. Click "Manage app"
3. View logs in the terminal

## 📞 Support

For issues or questions:
1. Check the [User Guide](#)
2. Review [Troubleshooting](#)
3. Contact support

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Contributors

- **Damion Morrison** - Original Author
- **Ben Dillon** - Contributor

## 🙏 Acknowledgments

- Streamlit team for the amazing framework
- All contributors and testers

---

**Version**: 2.0 (Streamlit Web)  
**Last Updated**: November 2025
