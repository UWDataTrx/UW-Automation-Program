# 🚀 Streamlit Deployment Guide

## Quick Deployment to Streamlit Community Cloud

### Step 1: Prepare Your Repository

✅ **Files Required** (already created):
- `streamlit_app.py` - Main application
- `requirements-streamlit.txt` - Python dependencies
- `.streamlit/config.toml` - App configuration
- `packages.txt` - System dependencies (if any)

### Step 2: Push to GitHub

```bash
# Make sure all changes are committed
git add .
git commit -m "Add Streamlit web application"
git push origin main
```

### Step 3: Deploy to Streamlit Cloud

1. **Go to Streamlit Community Cloud**
   - Visit: https://share.streamlit.io
   - Sign in with your GitHub account

2. **Create New App**
   - Click "New app" button
   - Select your repository: `UWDataTrx/UW-Automation-Program`
   - Select branch: `copilot/convert-gui-to-web-app` (or `main` after merge)
   - Main file path: `streamlit_app.py`
   - App URL: Choose a custom URL (e.g., `uw-repricing-tool`)

3. **Advanced Settings** (Optional)
   - Python version: 3.9 or 3.10
   - Secrets: Add any API keys or credentials (none needed for basic app)

4. **Click "Deploy!"**
   - Deployment typically takes 2-5 minutes
   - You'll see build logs in real-time
   - Once complete, your app will be live!

### Step 4: Access Your App

Your app will be available at:
```
https://[your-app-name].streamlit.app
```

## 🔧 Local Testing (Before Deployment)

Test locally to ensure everything works:

```bash
# Install dependencies
pip install streamlit pandas openpyxl xlsxwriter pyarrow

# Run the app
streamlit run streamlit_app.py

# Open browser to http://localhost:8501
```

## 📋 Deployment Checklist

Before deploying, verify:

- [x] `streamlit_app.py` exists and runs without errors
- [x] `requirements-streamlit.txt` contains all dependencies
- [x] `.streamlit/config.toml` has correct configuration
- [x] All changes committed and pushed to GitHub
- [x] Repository is public or you have Streamlit Cloud permissions
- [x] No hardcoded secrets or credentials in code

## 🎨 Customization

### Change App Theme

Edit `.streamlit/config.toml`:

```toml
[theme]
primaryColor="#0066cc"          # Main accent color
backgroundColor="#FFFFFF"        # Background
secondaryBackgroundColor="#f0f8ff"  # Secondary background
textColor="#262730"             # Text color
```

### Add Secrets

For API keys or sensitive data:

1. In Streamlit Cloud dashboard, go to app settings
2. Click "Secrets"
3. Add your secrets in TOML format:

```toml
# Example secrets
database_url = "postgresql://..."
api_key = "your-api-key"
```

Access in your app:
```python
import streamlit as st
api_key = st.secrets["api_key"]
```

## 🐛 Troubleshooting

### Common Deployment Issues

**Error: "Requirements file not found"**
- Ensure `requirements-streamlit.txt` is in repository root
- Check file name spelling

**Error: "Module not found"**
- Add missing package to `requirements-streamlit.txt`
- Redeploy the app

**Error: "App is slow or crashes"**
- Check file size limits (200MB max)
- Optimize data processing
- Consider caching with `@st.cache_data`

**Error: "Port already in use" (local)**
- Stop other Streamlit instances
- Or specify different port: `streamlit run streamlit_app.py --server.port 8502`

### View Logs

In Streamlit Cloud:
1. Go to app dashboard
2. Click "Manage app"
3. View logs for debugging

## 🔄 Updating Your App

Changes pushed to GitHub automatically redeploy:

```bash
# Make changes to streamlit_app.py
git add streamlit_app.py
git commit -m "Update feature X"
git push

# Streamlit Cloud will auto-detect and redeploy
```

Manual redeployment:
1. Go to app dashboard
2. Click "Reboot app"

## 📊 Monitoring

Streamlit Cloud provides:
- **Usage metrics** - Viewer count, session duration
- **Error logs** - Runtime errors and exceptions
- **Performance stats** - Load times, resource usage

Access from the app dashboard.

## 🎯 Next Steps

After deployment:

1. **Test thoroughly** - Upload sample files and verify processing
2. **Share with users** - Send them the app URL
3. **Collect feedback** - Use Streamlit's built-in feedback tools
4. **Monitor usage** - Check logs and metrics
5. **Iterate** - Add features based on user feedback

## 📞 Support

- **Streamlit Docs**: https://docs.streamlit.io
- **Community Forum**: https://discuss.streamlit.io
- **GitHub Issues**: Report bugs in your repository

## 🎉 Success Criteria

Your deployment is successful when:

✅ App loads without errors  
✅ File upload works correctly  
✅ Processing completes successfully  
✅ Download buttons provide correct files  
✅ UI is responsive and user-friendly  
✅ No performance issues with typical file sizes  

---

**Ready to deploy?** Follow the steps above and your app will be live in minutes! 🚀
