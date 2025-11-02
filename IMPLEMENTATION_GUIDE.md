# Web Conversion Implementation Guide
## Step-by-Step Instructions for Converting to Web Application

---

## Quick Start: Choose Your Path

### Path A: Quick Prototype (Streamlit) - 1-2 Days
**Best for**: Validating the concept, getting quick feedback

### Path B: Production Web App (Flask) - 10-11 Weeks  
**Best for**: Full-featured, scalable, production-ready solution

---

## PATH A: Streamlit Quick Prototype

### Step 1: Install Streamlit

```bash
pip install streamlit
```

### Step 2: Create `streamlit_app.py`

```python
import streamlit as st
import sys
from pathlib import Path
import tempfile
import os

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from modules.merge import merge_files
from modules.tier_disruption import run_tier_disruption
from modules.bg_disruption import run_bg_disruption

st.set_page_config(
    page_title="UW Repricing Tool",
    page_icon="💊",
    layout="wide"
)

st.title("🏥 UW Pharmacy Repricing Automation")
st.markdown("---")

# Sidebar for navigation
page = st.sidebar.selectbox(
    "Select Process",
    ["Claim Repricing", "Tier Disruption", "B/G Disruption", "SHARx LBL", "EPLS LBL"]
)

if page == "Claim Repricing":
    st.header("📊 Claim File Repricing")
    
    col1, col2 = st.columns(2)
    
    with col1:
        file1 = st.file_uploader(
            "Upload File 1 (To Tool)", 
            type=['xlsx', 'csv'],
            help="Select the file uploaded to the tool"
        )
    
    with col2:
        file2 = st.file_uploader(
            "Upload File 2 (From Tool)", 
            type=['xlsx', 'csv'],
            help="Select the file from the tool"
        )
    
    template = st.file_uploader(
        "Upload Template (Optional)",
        type=['xlsx'],
        help="Select _Rx Repricing_wf.xlsx template"
    )
    
    if st.button("🚀 Start Processing", type="primary"):
        if file1 and file2:
            with st.spinner("Processing files..."):
                # Save uploaded files temporarily
                with tempfile.TemporaryDirectory() as tmpdir:
                    file1_path = Path(tmpdir) / file1.name
                    file2_path = Path(tmpdir) / file2.name
                    
                    with open(file1_path, 'wb') as f:
                        f.write(file1.getbuffer())
                    with open(file2_path, 'wb') as f:
                        f.write(file2.getbuffer())
                    
                    # Process files
                    try:
                        # Call existing merge logic
                        success = merge_files(str(file1_path), str(file2_path))
                        
                        if success:
                            st.success("✅ Processing complete!")
                            
                            # Offer downloads
                            merged_file = Path("merged_file_with_OR.xlsx")
                            if merged_file.exists():
                                with open(merged_file, 'rb') as f:
                                    st.download_button(
                                        "📥 Download Merged File",
                                        f,
                                        file_name=merged_file.name,
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                        else:
                            st.error("❌ Processing failed. Check logs.")
                    
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        else:
            st.warning("⚠️ Please upload both files")

elif page == "Tier Disruption":
    st.header("📈 Tier Disruption Analysis")
    
    reprice_file = st.file_uploader(
        "Upload Repricing Template",
        type=['xlsx'],
        key="tier_reprice"
    )
    
    if st.button("Run Tier Disruption", type="primary"):
        if reprice_file:
            with st.spinner("Analyzing tier disruptions..."):
                # Process tier disruption
                st.info("Tier disruption processing...")
        else:
            st.warning("Please upload repricing template")

elif page == "B/G Disruption":
    st.header("🔄 Brand/Generic Disruption Analysis")
    st.info("B/G Disruption functionality")

elif page == "SHARx LBL":
    st.header("📋 SHARx Line-by-Line Generator")
    st.info("SHARx LBL functionality")

elif page == "EPLS LBL":
    st.header("📋 EPLS Line-by-Line Generator")
    st.info("EPLS LBL functionality")

# Footer
st.sidebar.markdown("---")
st.sidebar.info("🔒 All data is processed securely")
```

### Step 3: Run the App

```bash
streamlit run streamlit_app.py
```

### Step 4: Test and Gather Feedback

- Share with 2-3 users
- Collect feedback on UX
- Validate that web approach works
- Identify missing features

---

## PATH B: Flask Production Web App

### Phase 1: Project Setup (Week 1)

#### Step 1: Create Flask Project Structure

```bash
# Create new directory
mkdir uw-automation-webapp
cd uw-automation-webapp

# Copy existing modules
cp -r ../UW-Automation-Program/modules .
cp -r ../UW-Automation-Program/utils .
cp -r ../UW-Automation-Program/config .

# Create Flask structure
mkdir -p app/{routes,templates,static/{css,js},tasks}
touch app/__init__.py
touch app/routes/{__init__.py,main.py,api.py}
touch app/tasks/{__init__.py,merge.py,disruption.py}
```

#### Step 2: Create `requirements-web.txt`

```text
# Web framework
Flask==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.1

# Task queue
celery==5.4.0
redis==5.2.3

# Database
Flask-SQLAlchemy==3.1.1
psycopg2-binary==2.9.9  # If using PostgreSQL

# Existing dependencies (keep these)
pandas==2.3.1
numpy==2.2.6
openpyxl==3.1.5
xlsxwriter==3.2.5
psutil==7.0.0
pyarrow==20.0.0
fastparquet==2024.11.0

# Web server
gunicorn==23.0.0
python-dotenv==1.0.1
```

#### Step 3: Create Flask App Factory

```python
# app/__init__.py
from flask import Flask
from flask_login import LoginManager
from celery import Celery
import os

celery = Celery(__name__, broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
login_manager = LoginManager()

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
    
    # Initialize extensions
    login_manager.init_app(app)
    celery.conf.update(app.config)
    
    # Register blueprints
    from app.routes import main, api
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp, url_prefix='/api')
    
    # Create upload folders
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('downloads', exist_ok=True)
    
    return app
```

#### Step 4: Create Main Routes

```python
# app/routes/main.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
from app.tasks.merge import process_repricing_task

bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'xlsx', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/upload', methods=['POST'])
def upload_files():
    # Validate files
    if 'file1' not in request.files or 'file2' not in request.files:
        flash('Both files are required', 'error')
        return redirect(url_for('main.index'))
    
    file1 = request.files['file1']
    file2 = request.files['file2']
    template = request.files.get('template')
    
    if file1.filename == '' or file2.filename == '':
        flash('Please select both files', 'error')
        return redirect(url_for('main.index'))
    
    if not (allowed_file(file1.filename) and allowed_file(file2.filename)):
        flash('Invalid file type. Only .xlsx and .csv allowed', 'error')
        return redirect(url_for('main.index'))
    
    # Save files
    from flask import current_app
    upload_folder = current_app.config['UPLOAD_FOLDER']
    
    file1_filename = secure_filename(file1.filename)
    file2_filename = secure_filename(file2.filename)
    
    file1_path = os.path.join(upload_folder, file1_filename)
    file2_path = os.path.join(upload_folder, file2_filename)
    
    file1.save(file1_path)
    file2.save(file2_path)
    
    template_path = None
    if template and template.filename:
        template_filename = secure_filename(template.filename)
        template_path = os.path.join(upload_folder, template_filename)
        template.save(template_path)
    
    # Create background task
    task = process_repricing_task.delay(file1_path, file2_path, template_path)
    
    session['current_task_id'] = task.id
    flash('Processing started!', 'success')
    
    return redirect(url_for('main.processing', task_id=task.id))

@bp.route('/processing/<task_id>')
def processing(task_id):
    return render_template('processing.html', task_id=task_id)

@bp.route('/disruption')
def disruption():
    return render_template('disruption.html')

@bp.route('/logs')
def logs():
    return render_template('logs.html')
```

#### Step 5: Create API Routes for Progress

```python
# app/routes/api.py
from flask import Blueprint, jsonify
from celery.result import AsyncResult
from app import celery

bp = Blueprint('api', __name__)

@bp.route('/task/<task_id>/status')
def task_status(task_id):
    task = AsyncResult(task_id, app=celery)
    
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'progress': 0,
            'status': 'Pending...'
        }
    elif task.state == 'PROGRESS':
        response = {
            'state': task.state,
            'progress': task.info.get('current', 0),
            'total': task.info.get('total', 100),
            'status': task.info.get('status', '')
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'progress': 100,
            'result': task.info
        }
    else:  # FAILURE
        response = {
            'state': task.state,
            'progress': 0,
            'status': str(task.info)
        }
    
    return jsonify(response)
```

#### Step 6: Create Celery Tasks

```python
# app/tasks/merge.py
from celery import current_task
from app import celery
import sys
from pathlib import Path

# Add modules to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.merge import merge_files

@celery.task(bind=True)
def process_repricing_task(self, file1_path, file2_path, template_path=None):
    try:
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'current': 10, 'total': 100, 'status': 'Starting merge...'}
        )
        
        # Run merge
        success = merge_files(file1_path, file2_path)
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 50, 'total': 100, 'status': 'Processing complete...'}
        )
        
        if success:
            # Additional processing
            self.update_state(
                state='PROGRESS',
                meta={'current': 100, 'total': 100, 'status': 'Finalizing...'}
            )
            
            return {
                'status': 'success',
                'output_file': 'merged_file_with_OR.xlsx'
            }
        else:
            return {'status': 'failed'}
    
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise
```

### Phase 2: Template Development (Week 4-5)

#### Base Template

```html
<!-- app/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}UW Repricing Tool{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">🏥 UW Repricing</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/disruption">Disruption</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/logs">Logs</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <main class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>

    <footer class="mt-5 py-3 bg-light">
        <div class="container text-center">
            <small class="text-muted">UW Automation Program © 2025</small>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

#### Index Page

```html
<!-- app/templates/index.html -->
{% extends "base.html" %}

{% block content %}
<div class="row">
    <div class="col-md-8 mx-auto">
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0">📊 Claim File Repricing</h4>
            </div>
            <div class="card-body">
                <form action="{{ url_for('main.upload_files') }}" method="POST" enctype="multipart/form-data" id="uploadForm">
                    <div class="mb-3">
                        <label for="file1" class="form-label">File 1 (Upload to Tool) *</label>
                        <input type="file" class="form-control" id="file1" name="file1" accept=".xlsx,.csv" required>
                        <small class="text-muted">Accepted formats: .xlsx, .csv</small>
                    </div>

                    <div class="mb-3">
                        <label for="file2" class="form-label">File 2 (From Tool) *</label>
                        <input type="file" class="form-control" id="file2" name="file2" accept=".xlsx,.csv" required>
                        <small class="text-muted">Accepted formats: .xlsx, .csv</small>
                    </div>

                    <div class="mb-3">
                        <label for="template" class="form-label">Template File (Optional)</label>
                        <input type="file" class="form-control" id="template" name="template" accept=".xlsx">
                        <small class="text-muted">Select _Rx Repricing_wf.xlsx template</small>
                    </div>

                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary btn-lg">
                            🚀 Start Processing
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <div class="mt-4">
            <div class="card">
                <div class="card-body">
                    <h5>ℹ️ Processing Information</h5>
                    <ul>
                        <li>Maximum file size: 500MB</li>
                        <li>Processing typically takes 2-5 minutes</li>
                        <li>You'll be redirected to a progress page</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

#### Processing Page

```html
<!-- app/templates/processing.html -->
{% extends "base.html" %}

{% block content %}
<div class="row">
    <div class="col-md-8 mx-auto">
        <div class="card shadow-sm">
            <div class="card-header bg-info text-white">
                <h4 class="mb-0">⚙️ Processing...</h4>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <div class="progress" style="height: 30px;">
                        <div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                            0%
                        </div>
                    </div>
                </div>

                <p id="statusText" class="text-center">Starting...</p>

                <div id="resultSection" class="d-none">
                    <div class="alert alert-success">
                        <h5>✅ Processing Complete!</h5>
                        <p>Your files have been processed successfully.</p>
                    </div>
                    <div class="d-grid gap-2">
                        <a href="#" id="downloadLink" class="btn btn-success btn-lg">
                            📥 Download Results
                        </a>
                        <a href="/" class="btn btn-outline-primary">
                            ← Process New Files
                        </a>
                    </div>
                </div>

                <div id="errorSection" class="d-none">
                    <div class="alert alert-danger">
                        <h5>❌ Processing Failed</h5>
                        <p id="errorMessage"></p>
                    </div>
                    <a href="/" class="btn btn-outline-primary">
                        ← Try Again
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
const taskId = "{{ task_id }}";

function updateProgress() {
    fetch(`/api/task/${taskId}/status`)
        .then(response => response.json())
        .then(data => {
            const progress = data.progress || 0;
            const progressBar = document.getElementById('progressBar');
            const statusText = document.getElementById('statusText');
            
            progressBar.style.width = progress + '%';
            progressBar.textContent = progress + '%';
            progressBar.setAttribute('aria-valuenow', progress);
            
            statusText.textContent = data.status || 'Processing...';
            
            if (data.state === 'SUCCESS') {
                progressBar.classList.remove('progress-bar-animated');
                progressBar.classList.add('bg-success');
                document.getElementById('resultSection').classList.remove('d-none');
                
                if (data.result && data.result.output_file) {
                    document.getElementById('downloadLink').href = '/download/' + data.result.output_file;
                }
            } else if (data.state === 'FAILURE') {
                progressBar.classList.remove('progress-bar-animated');
                progressBar.classList.add('bg-danger');
                document.getElementById('errorSection').classList.remove('d-none');
                document.getElementById('errorMessage').textContent = data.status;
            } else {
                setTimeout(updateProgress, 1000);  // Poll every second
            }
        })
        .catch(error => {
            console.error('Error:', error);
            setTimeout(updateProgress, 2000);  // Retry after 2 seconds
        });
}

// Start polling
updateProgress();
</script>
{% endblock %}
```

### Phase 3: Deployment (Week 10)

#### Docker Setup

```dockerfile
# Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p uploads downloads

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "wsgi:app"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://user:pass@db:5432/uwautomation
    depends_on:
      - redis
      - db
    volumes:
      - ./uploads:/app/uploads
      - ./downloads:/app/downloads

  worker:
    build: .
    command: celery -A app.celery worker --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./downloads:/app/downloads

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=uwautomation
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

#### Running with Docker

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop
docker-compose down
```

---

## Testing Checklist

- [ ] File upload validation (size, type)
- [ ] Merge processing accuracy
- [ ] Progress tracking accuracy
- [ ] Error handling
- [ ] Download functionality
- [ ] Multi-user concurrent processing
- [ ] Session management
- [ ] Security (file access, XSS, CSRF)
- [ ] Performance with large files (>100MB)
- [ ] Browser compatibility (Chrome, Firefox, Safari, Edge)

---

## Maintenance Guide

### Monitoring

```python
# Add health check endpoint
@bp.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'celery': check_celery_health(),
        'redis': check_redis_health()
    })
```

### Logging

```python
# Configure logging
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler('app.log', maxBytes=10000000, backupCount=3)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
```

---

## Support & Troubleshooting

### Common Issues

**Issue**: Celery tasks not executing
**Solution**: Check Redis connection, restart worker

**Issue**: File upload fails
**Solution**: Check upload folder permissions, verify file size limits

**Issue**: Slow performance
**Solution**: Increase Celery workers, optimize pandas operations

---

## Next Steps After Implementation

1. Set up CI/CD pipeline
2. Add automated tests
3. Configure backup strategy
4. Set up monitoring (Sentry, New Relic)
5. Create user documentation
6. Plan training sessions
7. Establish support process

---

**End of Implementation Guide**
