# UW Automation Program - FastAPI Web Application

## 🌐 Overview
This is the FastAPI-based web application for the UW Pharmacy Repricing Automation tool. It provides a REST API and web interface for processing pharmacy claims data.

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
pip install -r requirements-fastapi.txt
```

3. Run the application:
```bash
python fastapi_app.py
```

Or using uvicorn directly:
```bash
uvicorn fastapi_app:app --reload --host 0.0.0.0 --port 8000
```

4. Open your browser to `http://localhost:8000`

## 📋 Features

### Current Features
- ✅ **REST API** - RESTful API for claims processing
- ✅ **File Upload** - Upload claim files via web interface or API
- ✅ **Claim File Repricing** - Merge and process claim files with reversal matching
- ✅ **Background Processing** - Asynchronous file processing
- ✅ **Real-time Status** - Check processing status via API
- ✅ **Download Results** - Download merged Excel and CSV files
- ✅ **Audit Logging** - Track all file processing activities
- ✅ **Web Interface** - Simple, modern web UI for file upload and download

### API Endpoints

#### GET /
- Returns the main web interface

#### GET /api
- Returns API information and available endpoints

#### GET /health
- Health check endpoint
- Returns: `{"status": "healthy", "timestamp": "..."}`

#### POST /api/upload
- Upload files for processing
- Parameters:
  - `file1`: File uploaded to tool (multipart/form-data)
  - `file2`: File from tool (multipart/form-data)
  - `template`: Optional template file (multipart/form-data)
- Returns: `{"job_id": "...", "status": "processing_started", "message": "..."}`

#### GET /api/status/{job_id}
- Get processing status for a job
- Returns: `{"job_id": "...", "status": "...", "progress": 0.0-1.0, "message": "...", "output_files": {...}}`

#### GET /api/download/{job_id}/{file_type}
- Download processed files
- file_type: `merged` or `csv`
- Returns: File download

#### GET /api/audit-logs
- Get recent audit log entries
- Query parameters:
  - `limit`: Number of entries to return (default: 50)
- Returns: `{"entries": [...], "total": N}`

#### DELETE /api/cleanup/{job_id}
- Clean up job files and data
- Returns: `{"message": "Job ... cleaned up successfully"}`

## 🎯 Usage

### Via Web Interface

1. Open `http://localhost:8000` in your browser
2. Upload File 1 and File 2
3. Optionally upload a template file
4. Click "Start Processing"
5. Wait for processing to complete
6. Download the results

### Via API (curl examples)

Upload files:
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file1=@path/to/file1.xlsx" \
  -F "file2=@path/to/file2.xlsx" \
  -F "template=@path/to/template.xlsx"
```

Check status:
```bash
curl "http://localhost:8000/api/status/{job_id}"
```

Download results:
```bash
curl -O "http://localhost:8000/api/download/{job_id}/merged"
curl -O "http://localhost:8000/api/download/{job_id}/csv"
```

### Via API (Python example)

```python
import requests

# Upload files
with open('file1.xlsx', 'rb') as f1, open('file2.xlsx', 'rb') as f2:
    files = {
        'file1': f1,
        'file2': f2
    }
    response = requests.post('http://localhost:8000/api/upload', files=files)
    job_id = response.json()['job_id']

# Check status
while True:
    response = requests.get(f'http://localhost:8000/api/status/{job_id}')
    data = response.json()
    print(f"Progress: {data['progress']*100:.1f}% - {data['message']}")
    
    if data['status'] == 'completed':
        break
    elif data['status'] == 'failed':
        print(f"Processing failed: {data['message']}")
        break
    
    time.sleep(2)

# Download results
response = requests.get(f'http://localhost:8000/api/download/{job_id}/merged')
with open('output.xlsx', 'wb') as f:
    f.write(response.content)
```

## 🔧 Configuration

### Environment Variables
- `HOST`: Host to bind to (default: 0.0.0.0)
- `PORT`: Port to bind to (default: 8000)

### CORS
CORS is enabled for all origins by default. For production, update the `allow_origins` in `fastapi_app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Update this
    ...
)
```

## 📦 Deployment

### Using Docker

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements-fastapi.txt .
RUN pip install --no-cache-dir -r requirements-fastapi.txt

COPY . .

CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t uw-automation-fastapi .
docker run -p 8000:8000 uw-automation-fastapi
```

### Using a Cloud Platform

The FastAPI application can be deployed to various cloud platforms:
- **AWS**: Use Elastic Beanstalk, ECS, or Lambda with API Gateway
- **Google Cloud**: Use Cloud Run or App Engine
- **Azure**: Use App Service or Container Instances
- **Heroku**: Use the Python buildpack with a `Procfile`
- **Railway/Render**: Direct deployment from Git repository

## 🧪 Testing

Run the application and test the endpoints:
```bash
# Start the server
python fastapi_app.py

# In another terminal, test the health endpoint
curl http://localhost:8000/health

# Test the API info endpoint
curl http://localhost:8000/api
```

## 📝 Migration from Streamlit

The FastAPI application replaces the Streamlit web interface with:
- Better API design and flexibility
- Background processing capabilities
- RESTful endpoints for integration
- Improved scalability and performance
- Modern web interface using standard HTML/CSS/JavaScript

The core business logic in `modules/` remains unchanged.

## 🔒 Security

For production deployment:
1. Configure CORS properly (restrict origins)
2. Add authentication/authorization
3. Use HTTPS/TLS
4. Implement rate limiting
5. Add input validation
6. Set up proper logging and monitoring
7. Use environment variables for sensitive configuration

## 📖 Additional Documentation

- [Main README](README.md)
- [Implementation Guide](IMPLEMENTATION_GUIDE.md)

## 🤝 Contributing

This is a private repository. Contact the repository owner for access.

## 📄 License

See [LICENSE](LICENSE) file for details.
