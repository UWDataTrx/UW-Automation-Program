# Deployment Guide - FastAPI Application

This guide covers deploying the UW Automation Program FastAPI application to various platforms.

## Table of Contents
- [Docker Deployment](#docker-deployment)
- [Cloud Platforms](#cloud-platforms)
- [Production Considerations](#production-considerations)

---

## Docker Deployment

### Create Dockerfile

Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-fastapi.txt .
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-fastapi.txt

# Copy application code
COPY . .

# Create directories for outputs
RUN mkdir -p outputs static

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Create docker-compose.yml (optional)

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./outputs:/app/outputs
      - ./static:/app/static
    environment:
      - HOST=0.0.0.0
      - PORT=8000
    restart: unless-stopped
```

### Build and Run

```bash
# Build the Docker image
docker build -t uw-automation-fastapi .

# Run the container
docker run -d -p 8000:8000 --name uw-automation uw-automation-fastapi

# Or use docker-compose
docker-compose up -d
```

---

## Cloud Platforms

### AWS Elastic Beanstalk

1. Install EB CLI:
   ```bash
   pip install awsebcli
   ```

2. Initialize EB application:
   ```bash
   eb init -p python-3.11 uw-automation
   ```

3. Create `Procfile`:
   ```
   web: uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
   ```

4. Create `.ebextensions/python.config`:
   ```yaml
   option_settings:
     aws:elasticbeanstalk:container:python:
       WSGIPath: fastapi_app:app
   ```

5. Deploy:
   ```bash
   eb create uw-automation-env
   eb deploy
   ```

### Google Cloud Run

1. Create `Dockerfile` (see above)

2. Build and push to Google Container Registry:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/uw-automation
   ```

3. Deploy to Cloud Run:
   ```bash
   gcloud run deploy uw-automation \
     --image gcr.io/PROJECT_ID/uw-automation \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

### Azure App Service

1. Create `startup.sh`:
   ```bash
   #!/bin/bash
   uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
   ```

2. Deploy using Azure CLI:
   ```bash
   az webapp up --runtime PYTHON:3.11 --sku B1 --name uw-automation
   ```

### Heroku

1. Create `Procfile`:
   ```
   web: uvicorn fastapi_app:app --host 0.0.0.0 --port $PORT
   ```

2. Create `runtime.txt`:
   ```
   python-3.11.5
   ```

3. Deploy:
   ```bash
   heroku create uw-automation
   git push heroku main
   ```

### Railway / Render

These platforms support automatic deployment from Git repositories:

1. Connect your GitHub repository
2. Select the branch to deploy
3. Set build command: `pip install -r requirements-fastapi.txt`
4. Set start command: `uvicorn fastapi_app:app --host 0.0.0.0 --port $PORT`

---

## Production Considerations

### 1. Environment Variables

Create a `.env` file (add to `.gitignore`):
```env
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=https://yourdomain.com
MAX_UPLOAD_SIZE=200000000
TEMP_DIR=/tmp/uw_automation
```

Update `fastapi_app.py` to use environment variables:
```python
import os
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
```

### 2. CORS Configuration

Update CORS settings for production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # Use environment variable
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

### 3. HTTPS/TLS

For production, always use HTTPS:

- Use a reverse proxy (nginx, Caddy)
- Configure SSL certificates (Let's Encrypt)
- Redirect HTTP to HTTPS

Example nginx configuration:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Authentication

Add authentication for production use:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Implement your token verification logic
    if not verify_jwt_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return token

@app.post("/api/upload")
async def upload_files(
    token: str = Depends(verify_token),
    # ... rest of parameters
):
    # Protected endpoint
    pass
```

### 5. Rate Limiting

Add rate limiting to prevent abuse:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/upload")
@limiter.limit("5/minute")
async def upload_files(request: Request, ...):
    # Limited to 5 requests per minute per IP
    pass
```

### 6. Logging

Configure production logging:

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
handler = RotatingFileHandler(
    'app.log',
    maxBytes=10000000,  # 10MB
    backupCount=5
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

### 7. Monitoring

Use monitoring tools:
- **Prometheus + Grafana** for metrics
- **Sentry** for error tracking
- **New Relic** or **DataDog** for APM

Example with Prometheus:
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

### 8. File Storage

For production, use cloud storage for uploaded files:

```python
import boto3  # AWS S3
from google.cloud import storage  # Google Cloud Storage

# Example with S3
s3_client = boto3.client('s3')

def upload_to_s3(file_path, bucket, key):
    s3_client.upload_file(file_path, bucket, key)
    return f"https://{bucket}.s3.amazonaws.com/{key}"
```

### 9. Database

For tracking jobs and status, consider using a database:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
```

### 10. Background Tasks

For long-running tasks, use Celery with Redis:

```python
from celery import Celery

celery_app = Celery(
    'tasks',
    broker=os.getenv('REDIS_URL'),
    backend=os.getenv('REDIS_URL')
)

@celery_app.task
def process_files_task(job_id, file1_path, file2_path):
    # Background processing
    pass
```

---

## Performance Optimization

### 1. Use Gunicorn with Uvicorn workers

```bash
gunicorn fastapi_app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300
```

### 2. Enable Response Caching

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

@app.get("/api/status/{job_id}")
@cache(expire=60)  # Cache for 60 seconds
async def get_status(job_id: str):
    # ...
```

### 3. Enable Compression

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

## Health Checks and Monitoring

### Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: uw-automation
spec:
  replicas: 3
  selector:
    matchLabels:
      app: uw-automation
  template:
    metadata:
      labels:
        app: uw-automation
    spec:
      containers:
      - name: uw-automation
        image: uw-automation:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

## Maintenance

### Cleanup Jobs

Schedule periodic cleanup of old job files:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=2)  # Run at 2 AM daily
async def cleanup_old_jobs():
    cutoff_time = datetime.now() - timedelta(days=7)
    # Clean up jobs older than 7 days
    for job_id in list(processing_status.keys()):
        # Check job age and clean up
        pass

scheduler.start()
```

---

## Support

For issues or questions:
- Open an issue on GitHub
- Contact the development team
- See [README_FASTAPI.md](README_FASTAPI.md) for API documentation
