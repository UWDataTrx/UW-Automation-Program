"""
UW Automation Program - Streamlit Web Application (DEPRECATED)
Pharmacy Claims Repricing and Disruption Analysis Tool

⚠️ DEPRECATION NOTICE:
This Streamlit application is deprecated and will be removed in a future release.
Please use the FastAPI application (fastapi_app.py) instead.

For migration instructions and FastAPI documentation, see:
- README_FASTAPI.md
- https://fastapi.tiangolo.com/

The FastAPI application provides:
- Better performance and scalability
- RESTful API endpoints
- Modern web interface
- Background task processing
- Improved error handling
"""

import streamlit as st
import sys
from pathlib import Path
import tempfile
import os
import pandas as pd
import logging
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import modules
from modules.merge import merge_files
from modules.audit_helper import log_file_access, make_audit_entry
from utils.utils import write_audit_log

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="UW Repricing Tool",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #0066cc;
        color: white;
        font-weight: bold;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
    }
    .stButton>button:hover {
        background-color: #0052a3;
    }
    .upload-box {
        border: 2px dashed #0066cc;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        background-color: #f0f8ff;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .deprecation-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #ffe6e6;
        border: 2px solid #ff4444;
        color: #cc0000;
        margin: 1rem 0;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Display deprecation warning
st.markdown("""
<div class="deprecation-box">
    ⚠️ <strong>DEPRECATION NOTICE</strong><br>
    This Streamlit interface is deprecated. Please use the FastAPI application instead:<br>
    <code>python fastapi_app.py</code> or <code>uvicorn fastapi_app:app --reload</code><br>
    See <a href="https://github.com/UWDataTrx/UW-Automation-Program/blob/main/README_FASTAPI.md" style="color: #cc0000; text-decoration: underline;">README_FASTAPI.md</a> for details.
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'output_file' not in st.session_state:
    st.session_state.output_file = None
if 'csv_file' not in st.session_state:
    st.session_state.csv_file = None

# Header
st.markdown("# 🏥 UW Pharmacy Repricing Automation")
st.markdown("---")

# Sidebar for navigation
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/0066cc/ffffff?text=UW+Automation", use_container_width=True)
    st.markdown("### Navigation")
    page = st.radio(
        "Select Process",
        ["🏠 Home", "📊 Claim Repricing", "📈 Tier Disruption", "🔄 B/G Disruption", 
         "📋 SHARx LBL", "📋 EPLS LBL", "📜 Audit Logs"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### 📌 Quick Info")
    st.info("💡 **Tips:**\n- Upload files in Excel or CSV format\n- Max file size: 200MB\n- Processing takes 2-5 minutes")
    
    st.markdown("---")
    st.markdown("### 🔒 Security")
    st.caption("All data is processed securely and not stored permanently")

# Main content area
if page == "🏠 Home":
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("## Welcome to UW Repricing Tool")
        st.markdown("""
        This application automates pharmacy claims repricing and disruption analysis.
        
        ### 🧩 Key Features:
        - **Claim File Merging** – Match reversals with origin claims
        - **Disruption Analysis** – Tier-based and brand/generic evaluations
        - **Template Integration** – Auto-populate Excel templates
        - **SHARx & EPLS Generators** – Create formatted outputs
        - **Audit Trail** – Track all processing activities
        
        ### 🚀 Getting Started:
        1. Select **Claim Repricing** from the sidebar
        2. Upload your files (File 1 and File 2)
        3. Optionally upload a template
        4. Click **Start Processing**
        5. Download your results
        """)
    
    with col2:
        st.markdown("### 📊 Quick Stats")
        st.metric("Version", "2.0 (Web)")
        st.metric("Status", "✅ Online")
        st.metric("Users Active", "N/A")
        
        st.markdown("---")
        st.markdown("### 📖 Resources")
        st.markdown("- [User Guide](#)")
        st.markdown("- [Troubleshooting](#)")
        st.markdown("- [Support](#)")

elif page == "📊 Claim Repricing":
    st.markdown("## 📊 Claim File Repricing")
    
    st.markdown('<div class="info-box">Upload the files from your tool to merge and process claims data.</div>', 
                unsafe_allow_html=True)
    
    st.markdown("### 📁 File Upload")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### File 1 (Uploaded to Tool)")
        file1 = st.file_uploader(
            "Select file uploaded to the tool",
            type=['xlsx', 'csv'],
            key="file1",
            help="This is the file you uploaded to the tool initially"
        )
        if file1:
            st.success(f"✅ {file1.name} uploaded ({file1.size / 1024:.1f} KB)")
    
    with col2:
        st.markdown("#### File 2 (From Tool)")
        file2 = st.file_uploader(
            "Select file from the tool",
            type=['xlsx', 'csv'],
            key="file2",
            help="This is the file you received from the tool"
        )
        if file2:
            st.success(f"✅ {file2.name} uploaded ({file2.size / 1024:.1f} KB)")
    
    st.markdown("---")
    
    # Optional template upload
    with st.expander("📋 Optional: Upload Template File"):
        template = st.file_uploader(
            "Upload _Rx Repricing_wf.xlsx template (optional)",
            type=['xlsx'],
            key="template",
            help="Template file for populating results"
        )
        if template:
            st.success(f"✅ Template: {template.name}")
    
    st.markdown("---")
    
    # Processing section
    if file1 and file2:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Start Processing", key="process_btn", use_container_width=True):
                st.session_state.processing_complete = False
                
                with st.spinner("Processing files... This may take a few minutes."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Create temporary directory for processing
                        with tempfile.TemporaryDirectory() as tmpdir:
                            tmpdir_path = Path(tmpdir)
                            
                            # Save uploaded files
                            status_text.text("📥 Saving uploaded files...")
                            progress_bar.progress(10)
                            
                            file1_path = tmpdir_path / file1.name
                            file2_path = tmpdir_path / file2.name
                            
                            with open(file1_path, 'wb') as f:
                                f.write(file1.getbuffer())
                            with open(file2_path, 'wb') as f:
                                f.write(file2.getbuffer())
                            
                            # Log file access
                            log_file_access("StreamlitApp", str(file1_path), "UPLOADED")
                            log_file_access("StreamlitApp", str(file2_path), "UPLOADED")
                            
                            # Process files
                            status_text.text("⚙️ Merging claim files...")
                            progress_bar.progress(30)
                            
                            success = merge_files(str(file1_path), str(file2_path))
                            
                            progress_bar.progress(70)
                            status_text.text("🔄 Processing merged data...")
                            
                            if success:
                                # Check for output files
                                merged_file = Path("merged_file_with_OR.xlsx")
                                csv_file = None
                                
                                # Look for CSV file (pattern: *_Claim Detail.csv)
                                csv_files = list(Path(".").glob("*Claim Detail.csv"))
                                if csv_files:
                                    csv_file = csv_files[0]
                                
                                progress_bar.progress(100)
                                status_text.text("✅ Processing complete!")
                                
                                st.session_state.processing_complete = True
                                st.session_state.output_file = merged_file if merged_file.exists() else None
                                st.session_state.csv_file = csv_file
                                
                                st.balloons()
                                
                            else:
                                st.error("❌ Processing failed. Please check your files and try again.")
                                make_audit_entry("StreamlitApp", "Processing failed", "ERROR")
                    
                    except Exception as e:
                        logger.error(f"Error during processing: {str(e)}")
                        st.error(f"❌ An error occurred: {str(e)}")
                        make_audit_entry("StreamlitApp", f"Error: {str(e)}", "ERROR")
    
    else:
        st.warning("⚠️ Please upload both File 1 and File 2 to continue")
    
    # Display results if processing is complete
    if st.session_state.processing_complete:
        st.markdown("---")
        st.markdown('<div class="success-box"><h3>✅ Processing Complete!</h3><p>Your files have been processed successfully. Download the results below.</p></div>', 
                    unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.output_file and st.session_state.output_file.exists():
                with open(st.session_state.output_file, 'rb') as f:
                    st.download_button(
                        label="📥 Download Merged File (Excel)",
                        data=f,
                        file_name=st.session_state.output_file.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
        
        with col2:
            if st.session_state.csv_file and st.session_state.csv_file.exists():
                with open(st.session_state.csv_file, 'rb') as f:
                    st.download_button(
                        label="📥 Download Claim Detail (CSV)",
                        data=f,
                        file_name=st.session_state.csv_file.name,
                        mime="text/csv",
                        use_container_width=True
                    )
        
        # Option to process new files
        if st.button("🔄 Process New Files"):
            st.session_state.processing_complete = False
            st.session_state.output_file = None
            st.session_state.csv_file = None
            st.rerun()

elif page == "📈 Tier Disruption":
    st.markdown("## 📈 Tier Disruption Analysis")
    st.info("🚧 This feature will analyze tier-based disruptions in your pharmacy claims.")
    
    st.markdown("""
    ### Coming Soon
    This module will provide:
    - Tier movement analysis
    - Product-level disruption details
    - Member impact assessment
    - Automated reporting
    
    Please use the **Claim Repricing** module for now.
    """)

elif page == "🔄 B/G Disruption":
    st.markdown("## 🔄 Brand/Generic Disruption Analysis")
    st.info("🚧 This feature will analyze brand vs generic disruptions.")
    
    st.markdown("""
    ### Coming Soon
    This module will provide:
    - Brand to generic switches
    - Generic to brand switches
    - Cost impact analysis
    - Member notification lists
    
    Please use the **Claim Repricing** module for now.
    """)

elif page == "📋 SHARx LBL":
    st.markdown("## 📋 SHARx Line-by-Line Generator")
    st.info("🚧 This feature will generate SHARx formatted output files.")
    
    st.markdown("""
    ### Coming Soon
    This module will generate:
    - SHARx formatted Excel files
    - Line-by-line claim details
    - Automated formatting
    
    Please use the **Claim Repricing** module for now.
    """)

elif page == "📋 EPLS LBL":
    st.markdown("## 📋 EPLS Line-by-Line Generator")
    st.info("🚧 This feature will generate EPLS formatted output files.")
    
    st.markdown("""
    ### Coming Soon
    This module will generate:
    - EPLS formatted Excel files
    - Line-by-line claim details
    - Automated formatting
    
    Please use the **Claim Repricing** module for now.
    """)

elif page == "📜 Audit Logs":
    st.markdown("## 📜 Audit Logs")
    
    st.markdown("### Recent Activity")
    
    # Check if audit log exists
    audit_file = Path("audit_log.csv")
    if audit_file.exists():
        try:
            df = pd.read_csv(audit_file)
            
            # Display last 50 entries
            st.dataframe(
                df.tail(50).sort_values('Timestamp', ascending=False),
                use_container_width=True,
                hide_index=True
            )
            
            # Download audit log
            with open(audit_file, 'rb') as f:
                st.download_button(
                    label="📥 Download Full Audit Log",
                    data=f,
                    file_name="audit_log.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"Error loading audit log: {str(e)}")
    else:
        st.info("No audit log available yet. Process some files to generate audit entries.")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("© 2025 UW Automation Program")
with col2:
    st.caption("Version 2.0 (Streamlit Web)")
with col3:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d')}")
