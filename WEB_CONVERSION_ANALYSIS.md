# Web Application Conversion Analysis
## UW Automation Program - Pharmacy Claims Repricing Tool

**Date**: November 2, 2025  
**Analysis By**: GitHub Copilot Coding Agent  
**Current Version**: Desktop GUI (CustomTkinter-based)

---

## Executive Summary

This document provides a comprehensive analysis and recommendation for converting the **UW Automation Program** from a desktop GUI application into a web application while maintaining all current functionality. The application currently automates pharmacy claims repricing, disruption analysis, and generates formatted outputs.

---

## 1. Current Application Analysis

### 1.1 Core Functionality

The application currently performs these key operations:

1. **Claim File Merging**
   - Matches reversals with origin claims
   - Applies logic tagging (O's & R's Check)
   - Processes two input files with validation

2. **Disruption Analysis**
   - Tier Disruption analysis
   - Brand/Generic (B/G) Disruption
   - Open MDF (Tier and B/G variants)

3. **Template Population**
   - Auto-populates `_Rx Repricing_wf.xlsx` with processed results
   - Preserves Excel formulas
   - Applies formatting and highlighting

4. **Output Generation**
   - SHARx LBL generator
   - EPLS Line-by-Line (LBL) generator
   - CSV Claim Detail files
   - Parquet files for large datasets

5. **Audit & Logging**
   - Tracks file access and processing
   - Maintains audit logs
   - User session tracking

### 1.2 Technical Stack (Current)

- **Language**: Python 3.13.5
- **GUI Framework**: CustomTkinter
- **Data Processing**: Pandas, NumPy, Numba
- **Excel Manipulation**: 
  - xlwings (COM automation)
  - openpyxl (file manipulation)
  - xlsxwriter (writing)
- **File Formats**: Excel (.xlsx), CSV, Parquet
- **Multiprocessing**: For performance optimization

### 1.3 Architecture Components

```
┌─────────────────────────────────────────────────────────┐
│                    App.py (Main GUI)                     │
├─────────────────────────────────────────────────────────┤
│  - ConfigManager                                         │
│  - File Import Handlers                                  │
│  - Progress Tracking                                     │
│  - Theme Management                                      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  Processing Modules                      │
├─────────────────────────────────────────────────────────┤
│  - merge.py (File Merging)                              │
│  - tier_disruption.py                                   │
│  - bg_disruption.py                                     │
│  - openmdf_tier.py / openmdf_bg.py                      │
│  - sharx_lbl.py / epls_lbl.py                           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  Support Modules                         │
├─────────────────────────────────────────────────────────┤
│  - DataProcessor (validation, formatting)               │
│  - FileProcessor (I/O operations)                       │
│  - TemplateProcessor (Excel manipulation)               │
│  - ProcessManager (workflow orchestration)              │
│  - AuditHelper (logging)                                │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Web Conversion Options

### Option 1: Flask-based Web Application (Recommended)

**Why This is Best:**
- Already has Flask in dependencies (v3.1.1)
- Minimal learning curve for current codebase
- Can reuse 90%+ of existing backend logic
- Suitable for internal enterprise use
- Easy deployment options

**Architecture:**
```
┌──────────────────┐
│   Web Browser    │
│  (HTML/CSS/JS)   │
└────────┬─────────┘
         │ HTTP/AJAX
┌────────▼─────────┐
│  Flask Server    │
│  - Routes        │
│  - Session Mgmt  │
│  - File Upload   │
└────────┬─────────┘
         │
┌────────▼─────────┐
│ Existing Backend │
│  - merge.py      │
│  - disruption    │
│  - processors    │
└──────────────────┘
```

**Implementation Phases:**

**Phase 1: Core Web Infrastructure** (Week 1-2)
- Create Flask application structure
- Implement file upload/download endpoints
- Add user authentication (if needed)
- Session management for multi-user support
- Progress tracking via WebSockets or Server-Sent Events

**Phase 2: File Processing Integration** (Week 2-3)
- Adapt file import handlers for web uploads
- Implement background task processing (Celery/RQ)
- Add job queue for long-running operations
- Real-time progress updates to UI

**Phase 3: Excel Processing** (Week 3-4)
- Replace xlwings with server-side openpyxl
- Implement template processing without COM
- Add Excel download endpoints
- Ensure formula preservation

**Phase 4: UI Development** (Week 4-5)
- Create responsive HTML templates (Jinja2)
- Implement file drag-and-drop
- Add progress bars and status indicators
- Build disruption type selector
- Create log viewer pages

**Phase 5: Testing & Deployment** (Week 5-6)
- Integration testing
- Performance optimization
- Deployment to server (Docker recommended)
- User acceptance testing

### Option 2: Django-based Web Application

**Pros:**
- Built-in admin interface
- Better for complex user management
- ORM for database operations
- More structured for large teams

**Cons:**
- Heavier framework
- More refactoring required
- Overkill for current scope

### Option 3: Streamlit Application (Quick Prototype)

**Pros:**
- Fastest to implement (can be done in days)
- Python-native, minimal HTML/CSS/JS
- Auto-handles file uploads
- Built-in progress indicators

**Cons:**
- Less customizable UI
- Not suitable for production at scale
- Limited control over user sessions

---

## 3. Recommended Architecture (Flask-based)

### 3.1 Technology Stack

**Backend:**
- **Framework**: Flask 3.1.1
- **Task Queue**: Celery (with Redis broker)
- **Database**: SQLite (for jobs/audit) or PostgreSQL (production)
- **Excel Processing**: openpyxl (remove xlwings dependency)
- **File Storage**: Local filesystem or S3-compatible storage

**Frontend:**
- **Template Engine**: Jinja2
- **CSS Framework**: Bootstrap 5 or Tailwind CSS
- **JavaScript**: 
  - Vanilla JS or jQuery for interactions
  - Socket.IO or SSE for real-time updates
  - Dropzone.js for file uploads

**Infrastructure:**
- **Container**: Docker + Docker Compose
- **Web Server**: Gunicorn + Nginx
- **Task Workers**: Celery workers
- **Caching**: Redis

### 3.2 File Structure

```
uw-automation-webapp/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py          # Main page routes
│   │   ├── files.py         # File upload/download
│   │   ├── processing.py    # Job submission
│   │   └── api.py           # AJAX endpoints
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── processing.html
│   │   ├── disruption.html
│   │   └── logs.html
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── img/
│   ├── tasks/              # Celery tasks
│   │   ├── __init__.py
│   │   ├── merge.py
│   │   ├── disruption.py
│   │   └── template.py
│   └── models/             # Database models (if needed)
│       └── __init__.py
├── config/                 # Existing config
├── modules/                # Existing modules (reuse)
├── utils/                  # Existing utils (reuse)
├── uploads/                # Temporary upload storage
├── downloads/              # Generated files
├── docker-compose.yml
├── Dockerfile
├── requirements-web.txt
└── wsgi.py                # WSGI entry point
```

### 3.3 Key Changes Required

**1. Remove GUI Dependencies:**
```python
# Remove from requirements:
- customtkinter
- pyautogui
- pygetwindow
- pymsgbox
```

**2. Replace Excel COM with Pure Python:**
```python
# Before (app.py):
import xlwings as xw
app = xw.App(visible=False)

# After (web version):
from openpyxl import load_workbook
wb = load_workbook('template.xlsx')
```

**3. File Upload Handler:**
```python
# New: app/routes/files.py
from flask import request, flash, redirect
from werkzeug.utils import secure_filename

@app.route('/upload', methods=['POST'])
def upload_files():
    file1 = request.files['file1']
    file2 = request.files['file2']
    template = request.files['template']
    
    # Save to upload directory
    file1_path = save_upload(file1)
    file2_path = save_upload(file2)
    template_path = save_upload(template)
    
    # Create processing job
    job = process_files.delay(file1_path, file2_path, template_path)
    
    return redirect(url_for('processing_status', job_id=job.id))
```

**4. Background Processing:**
```python
# New: app/tasks/merge.py
from celery import current_task
from modules.merge import merge_files

@celery.task(bind=True)
def process_merge(self, file1, file2):
    # Existing merge logic
    result = merge_files(file1, file2)
    
    # Update progress
    self.update_state(
        state='PROGRESS',
        meta={'current': 50, 'total': 100}
    )
    
    return result
```

**5. Real-time Progress Updates:**
```javascript
// New: static/js/processing.js
function checkProgress(jobId) {
    fetch(`/api/job/${jobId}/status`)
        .then(response => response.json())
        .then(data => {
            updateProgressBar(data.progress);
            if (data.state === 'SUCCESS') {
                showDownloadLink(data.result);
            }
        });
}
```

---

## 4. Migration Strategy

### 4.1 Parallel Development Approach

1. **Keep Desktop Version**: Don't remove GUI initially
2. **Create Web Branch**: Develop web version separately
3. **Feature Parity Testing**: Ensure web version matches all features
4. **Gradual Migration**: Users can choose desktop or web
5. **Deprecate Desktop**: After 3-6 months of stable web operation

### 4.2 Data Compatibility

- **Maintain File Formats**: Keep Excel/CSV/Parquet support
- **Same Templates**: Ensure web version uses same Excel templates
- **Backward Compatible**: Web-generated files work with desktop version

### 4.3 User Training Plan

1. **Create User Guide**: Screenshot-based walkthrough
2. **Video Tutorials**: Record screen demos
3. **Pilot Group**: 5-10 users test web version
4. **Feedback Loop**: Weekly surveys during transition
5. **Support Channel**: Dedicated Slack/Teams channel

---

## 5. Security Considerations

### 5.1 Web-Specific Security Needs

1. **Authentication & Authorization**
   ```python
   # Add Flask-Login for user management
   from flask_login import login_required
   
   @app.route('/process')
   @login_required
   def process_page():
       pass
   ```

2. **File Upload Validation**
   ```python
   ALLOWED_EXTENSIONS = {'xlsx', 'csv'}
   MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
   
   def validate_upload(file):
       if not allowed_file(file.filename):
           raise ValueError("Invalid file type")
       if file.content_length > MAX_FILE_SIZE:
           raise ValueError("File too large")
   ```

3. **Data Encryption**
   - HTTPS only (TLS certificates)
   - Encrypt sensitive data at rest
   - Secure session cookies

4. **Access Control**
   - Role-based permissions (Admin, Analyst, Viewer)
   - Audit log for all file operations
   - IP whitelisting (if needed)

5. **Temporary File Cleanup**
   ```python
   # Automatic cleanup after processing
   @app.after_request
   def cleanup_files(response):
       cleanup_old_uploads(max_age_hours=24)
       return response
   ```

---

## 6. Performance Optimization

### 6.1 Current Bottlenecks

- Excel COM operations (slowest)
- Large file processing (memory intensive)
- Sequential processing of disruption analyses

### 6.2 Web-Specific Optimizations

1. **Async Processing**
   - All heavy operations in background tasks
   - Celery workers for parallel processing
   - Redis for job state management

2. **Chunked Uploads**
   ```javascript
   // For large files (>50MB)
   const uploader = new tus.Upload(file, {
       endpoint: "/upload/",
       chunkSize: 5 * 1024 * 1024  // 5MB chunks
   });
   ```

3. **Progress Streaming**
   ```python
   # Server-Sent Events for real-time updates
   @app.route('/stream/progress/<job_id>')
   def stream_progress(job_id):
       def generate():
           while True:
               progress = get_job_progress(job_id)
               yield f"data: {json.dumps(progress)}\n\n"
               if progress['state'] == 'SUCCESS':
                   break
       return Response(generate(), mimetype='text/event-stream')
   ```

4. **Caching**
   - Cache reference data (MediSpan, Universal NDC)
   - Redis cache for repeated lookups
   - ETag support for downloads

---

## 7. Deployment Options

### 7.1 Cloud Deployment (Recommended for Scale)

**AWS:**
```
ELB (Load Balancer)
  ↓
EC2 Instances (Flask + Gunicorn)
  ↓
ElastiCache (Redis for Celery)
  ↓
RDS (PostgreSQL for audit/jobs)
  ↓
S3 (File storage)
```

**Azure:**
```
Azure App Service (Flask)
  ↓
Azure Cache for Redis
  ↓
Azure Database for PostgreSQL
  ↓
Azure Blob Storage
```

**Docker Compose (Self-Hosted):**
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    depends_on:
      - redis
      - postgres
  
  worker:
    build: .
    command: celery -A app.celery worker
    depends_on:
      - redis
  
  redis:
    image: redis:alpine
  
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: uw_automation
```

### 7.2 On-Premise Deployment

For organizations requiring on-premise:
- Windows Server with IIS + FastCGI
- Linux server with Nginx + Gunicorn
- Docker Desktop on corporate server

---

## 8. Feature Enhancements (Web-Specific Benefits)

### 8.1 Multi-User Collaboration

- **Concurrent Processing**: Multiple users process different files
- **Job Queue**: Fair scheduling of processing jobs
- **Shared Templates**: Centralized template management

### 8.2 Enhanced Reporting

- **Dashboard**: Overview of processing history
- **Analytics**: Success rates, processing times
- **Notifications**: Email alerts on job completion

### 8.3 API Access

```python
# REST API for programmatic access
@app.route('/api/v1/process', methods=['POST'])
@require_api_key
def api_process():
    files = request.files.getlist('files')
    job = process_files.delay(files)
    return jsonify({
        'job_id': job.id,
        'status_url': url_for('api_job_status', job_id=job.id)
    })
```

---

## 9. Cost Estimation

### 9.1 Development Costs (Time)

| Phase | Estimated Time | Complexity |
|-------|---------------|------------|
| Flask Setup & Routes | 1 week | Medium |
| File Upload/Download | 1 week | Low |
| Background Processing | 2 weeks | High |
| Excel Processing Migration | 2 weeks | High |
| UI Development | 2 weeks | Medium |
| Testing & Bug Fixes | 2 weeks | Medium |
| Deployment Setup | 1 week | Medium |
| **Total** | **11 weeks** | - |

### 9.2 Infrastructure Costs (Monthly)

**Cloud (AWS t3.medium example):**
- EC2 instances (2x): $60
- RDS PostgreSQL: $30
- ElastiCache Redis: $15
- S3 Storage (500GB): $12
- Load Balancer: $18
- **Total**: ~$135/month

**Self-Hosted:**
- Server costs (existing infrastructure): $0
- Maintenance time: Varies

---

## 10. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Excel COM removal breaks formula handling | High | Thorough testing, openpyxl formula preservation |
| Performance degradation on large files | Medium | Async processing, chunking, progress indicators |
| User resistance to change | Medium | Training, parallel operation, gradual migration |
| Security vulnerabilities | High | Security audit, HTTPS only, input validation |
| Data loss during migration | High | Comprehensive backups, rollback plan |
| Browser compatibility issues | Low | Use modern standards, test on major browsers |

---

## 11. Immediate Next Steps

### Quick Win: Streamlit Prototype (1-2 Days)

To validate the web approach quickly:

```python
# streamlit_app.py
import streamlit as st
from modules.merge import merge_files

st.title("UW Repricing Tool")

file1 = st.file_uploader("Upload File 1", type=['xlsx', 'csv'])
file2 = st.file_uploader("Upload File 2", type=['xlsx', 'csv'])

if st.button("Process"):
    with st.spinner("Processing..."):
        result = merge_files(file1, file2)
    st.success("Complete!")
    st.download_button("Download Result", result)
```

**Run with**: `streamlit run streamlit_app.py`

### Full Implementation Path

1. **Week 1**: Set up Flask project structure
2. **Week 2**: Implement file upload and basic routing
3. **Week 3**: Add Celery for background tasks
4. **Week 4**: Migrate Excel processing to openpyxl
5. **Week 5**: Build responsive UI templates
6. **Week 6**: Integration testing
7. **Week 7**: Deploy to staging environment
8. **Week 8**: User acceptance testing
9. **Week 9**: Security audit and fixes
10. **Week 10**: Production deployment
11. **Week 11**: Monitoring and optimization

---

## 12. Recommendations

### For Internal Enterprise Use (Recommended):

✅ **Use Flask-based web application** because:
- Best balance of simplicity and functionality
- Reuses existing Python codebase (~90%)
- Scales to dozens of concurrent users
- Enterprise-ready with proper deployment
- Flexible for future enhancements

### Alternative for Quick Validation:

⚡ **Build Streamlit prototype first** to:
- Validate web approach with users (1-2 days)
- Identify UX improvements
- Get stakeholder buy-in
- Then migrate to Flask for production

### Don't Recommend:

❌ **Full JavaScript rewrite** (React/Vue/Angular)
- Requires rewriting all business logic
- 6+ months development time
- Higher cost, more risk

❌ **Desktop Electron wrapper**
- Still desktop-based, defeats purpose
- Large application size
- Doesn't solve multi-user needs

---

## Conclusion

Converting the UW Automation Program to a web application is **highly feasible** and **strategically beneficial**. The recommended Flask-based approach:

- ✅ Preserves all current functionality
- ✅ Enables multi-user collaboration
- ✅ Reduces deployment complexity
- ✅ Improves accessibility (browser-based)
- ✅ Maintains security and audit capabilities
- ✅ Allows gradual migration with minimal risk

**Estimated Timeline**: 10-11 weeks for full production deployment  
**Estimated Cost**: $15,000-$25,000 (developer time) + $135/month (cloud hosting)

**Next Action**: Approve architecture and begin Flask prototype development.

---

## Appendix A: Sample Flask Routes

```python
# app/routes/main.py
from flask import Blueprint, render_template, request, session
from app.tasks import process_repricing

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/upload', methods=['POST'])
def upload():
    files = {
        'file1': request.files['file1'],
        'file2': request.files['file2'],
        'template': request.files.get('template')
    }
    
    # Save files and create job
    job = process_repricing.delay(files)
    session['current_job'] = job.id
    
    return redirect(url_for('main.processing'))

@main.route('/processing')
def processing():
    job_id = session.get('current_job')
    return render_template('processing.html', job_id=job_id)

@main.route('/disruption/<type>')
def disruption(type):
    # type: tier, bg, openmdf_tier, openmdf_bg
    return render_template('disruption.html', type=type)
```

## Appendix B: Sample HTML Template

```html
<!-- templates/index.html -->
{% extends "base.html" %}

{% block content %}
<div class="container">
    <h1>UW Repricing Automation</h1>
    
    <form action="{{ url_for('main.upload') }}" method="POST" enctype="multipart/form-data">
        <div class="mb-3">
            <label for="file1" class="form-label">File 1 (Upload to Tool)</label>
            <input type="file" class="form-control" id="file1" name="file1" required>
        </div>
        
        <div class="mb-3">
            <label for="file2" class="form-label">File 2 (From Tool)</label>
            <input type="file" class="form-control" id="file2" name="file2" required>
        </div>
        
        <div class="mb-3">
            <label for="template" class="form-label">Template File (Optional)</label>
            <input type="file" class="form-control" id="template" name="template">
        </div>
        
        <button type="submit" class="btn btn-primary">Start Processing</button>
    </form>
</div>
{% endblock %}
```

---

**Document Version**: 1.0  
**Last Updated**: November 2, 2025
