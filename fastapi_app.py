"""
UW Automation Program - FastAPI Web Application
Pharmacy Claims Repricing and Disruption Analysis Tool
"""

import sys
from pathlib import Path
import tempfile
import os
import logging
from datetime import datetime
from typing import Optional
import shutil

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import modules
from client_code.merge import merge_files
from client_code.audit_helper import log_file_access, make_audit_entry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="UW Repricing Tool API",
    description="Pharmacy Claims Repricing and Disruption Analysis API",
    version="2.0"
)

# Add CORS middleware
# TODO: For production, configure allow_origins with specific domains
# Example: allow_origins=["https://yourdomain.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production - see DEPLOYMENT_GUIDE.md
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Storage for processing status
processing_status = {}
temp_files = {}


class ProcessStatus(BaseModel):
    status: str
    progress: float
    message: str
    output_files: Optional[dict] = None


@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("static/index.html")


@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "name": "UW Pharmacy Repricing Automation API",
        "version": "2.0",
        "status": "online",
        "endpoints": {
            "health": "/health",
            "upload_files": "/api/upload",
            "process_status": "/api/status/{job_id}",
            "download_file": "/api/download/{job_id}/{file_type}",
            "audit_logs": "/api/audit-logs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    template: Optional[UploadFile] = File(None)
):
    """
    Upload files for processing
    
    Parameters:
    - file1: File uploaded to the tool (Excel or CSV)
    - file2: File from the tool (Excel or CSV)
    - template: Optional template file (Excel)
    """
    try:
        # Generate job ID
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # Create temporary directory for this job
        job_temp_dir = Path(tempfile.gettempdir()) / f"uw_automation_{job_id}"
        job_temp_dir.mkdir(exist_ok=True)
        
        # Save uploaded files
        file1_path = job_temp_dir / file1.filename
        file2_path = job_temp_dir / file2.filename
        
        with open(file1_path, 'wb') as f:
            content = await file1.read()
            f.write(content)
        
        with open(file2_path, 'wb') as f:
            content = await file2.read()
            f.write(content)
        
        # Save template if provided
        template_path = None
        if template:
            template_path = job_temp_dir / template.filename
            with open(template_path, 'wb') as f:
                content = await template.read()
                f.write(content)
        
        # Log file access
        log_file_access("FastAPIApp", str(file1_path), "UPLOADED")
        log_file_access("FastAPIApp", str(file2_path), "UPLOADED")
        if template_path:
            log_file_access("FastAPIApp", str(template_path), "UPLOADED")
        
        # Initialize processing status
        processing_status[job_id] = {
            "status": "uploaded",
            "progress": 0.1,
            "message": "Files uploaded successfully",
            "file1_path": str(file1_path),
            "file2_path": str(file2_path),
            "template_path": str(template_path) if template_path else None,
            "job_temp_dir": str(job_temp_dir)
        }
        
        # Start processing in background
        background_tasks.add_task(process_files, job_id)
        
        return {
            "job_id": job_id,
            "status": "processing_started",
            "message": "Files uploaded and processing started"
        }
        
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def process_files(job_id: str):
    """Background task to process uploaded files"""
    try:
        status = processing_status[job_id]
        file1_path = status["file1_path"]
        file2_path = status["file2_path"]
        job_temp_dir = Path(status["job_temp_dir"])
        
        # Update status
        processing_status[job_id]["status"] = "processing"
        processing_status[job_id]["progress"] = 0.3
        processing_status[job_id]["message"] = "Merging claim files..."
        
        # Change to job temp directory for processing
        original_dir = os.getcwd()
        os.chdir(job_temp_dir)
        
        try:
            # Process files using existing merge logic
            success = merge_files(file1_path, file2_path)
            
            processing_status[job_id]["progress"] = 0.7
            processing_status[job_id]["message"] = "Processing merged data..."
            
            if success:
                # Check for output files
                merged_file = Path("merged_file_with_OR.xlsx")
                csv_files = list(Path(".").glob("*Claim Detail.csv"))
                
                output_files = {}
                
                # Copy output files to a persistent location
                output_dir = Path(original_dir) / "outputs" / job_id
                output_dir.mkdir(parents=True, exist_ok=True)
                
                if merged_file.exists():
                    output_file = output_dir / merged_file.name
                    shutil.copy(merged_file, output_file)
                    output_files["merged"] = str(output_file)
                
                if csv_files:
                    csv_file = output_dir / csv_files[0].name
                    shutil.copy(csv_files[0], csv_file)
                    output_files["csv"] = str(csv_file)
                
                # Update status
                processing_status[job_id]["status"] = "completed"
                processing_status[job_id]["progress"] = 1.0
                processing_status[job_id]["message"] = "Processing complete!"
                processing_status[job_id]["output_files"] = output_files
                
                make_audit_entry("FastAPIApp", f"Job {job_id} completed successfully", "SUCCESS")
            else:
                processing_status[job_id]["status"] = "failed"
                processing_status[job_id]["message"] = "Processing failed"
                make_audit_entry("FastAPIApp", f"Job {job_id} failed", "ERROR")
        
        finally:
            # Change back to original directory
            os.chdir(original_dir)
            
            # Schedule cleanup of temp files after 24 hours
            # In production, use a scheduled job (cron, celery, etc.) for cleanup
            # See DEPLOYMENT_GUIDE.md for cleanup strategies
            
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")
        processing_status[job_id]["status"] = "failed"
        processing_status[job_id]["message"] = f"Error: {str(e)}"
        make_audit_entry("FastAPIApp", f"Job {job_id} error: {str(e)}", "ERROR")


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get processing status for a job"""
    if job_id not in processing_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status = processing_status[job_id]
    return {
        "job_id": job_id,
        "status": status["status"],
        "progress": status["progress"],
        "message": status["message"],
        "output_files": status.get("output_files")
    }


@app.get("/api/download/{job_id}/{file_type}")
async def download_file(job_id: str, file_type: str):
    """
    Download processed files
    
    Parameters:
    - job_id: Job identifier
    - file_type: Type of file to download (merged or csv)
    """
    if job_id not in processing_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status = processing_status[job_id]
    
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Processing not complete")
    
    output_files = status.get("output_files", {})
    
    if file_type not in output_files:
        raise HTTPException(status_code=404, detail=f"File type '{file_type}' not found")
    
    file_path = output_files[file_type]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type='application/octet-stream',
        filename=os.path.basename(file_path)
    )


@app.get("/api/audit-logs")
async def get_audit_logs(limit: int = 50):
    """Get recent audit log entries"""
    try:
        import pandas as pd  # Import locally to avoid startup overhead
        
        audit_file = Path("audit_log.csv")
        
        if not audit_file.exists():
            return {"entries": [], "message": "No audit log available"}
        
        df = pd.read_csv(audit_file)
        
        # Get last N entries
        recent_entries = df.tail(limit).to_dict('records')
        
        return {
            "entries": recent_entries,
            "total": len(df)
        }
        
    except Exception as e:
        logger.error(f"Error reading audit log: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reading audit log: {str(e)}")


@app.delete("/api/cleanup/{job_id}")
async def cleanup_job(job_id: str):
    """Clean up job files and data"""
    if job_id not in processing_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Validate job_id to prevent path traversal attacks
    # Only allow alphanumeric, dash, and underscore characters
    if not job_id.replace('_', '').replace('-', '').isalnum():
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    try:
        status = processing_status[job_id]
        
        # Remove temp directory (use stored path from status, not user input)
        job_temp_dir = Path(status["job_temp_dir"])
        # Additional security: ensure temp dir is actually in temp directory
        if job_temp_dir.exists() and str(job_temp_dir).startswith(tempfile.gettempdir()):
            shutil.rmtree(job_temp_dir)
        
        # Remove output directory - validate it's in expected location
        output_dir = Path("outputs") / job_id
        # Resolve to absolute path and ensure it's within outputs directory
        output_dir_abs = output_dir.resolve()
        outputs_base = Path("outputs").resolve()
        
        # Check that output_dir is actually within outputs directory (prevent path traversal)
        if output_dir_abs.is_relative_to(outputs_base) and output_dir_abs.exists():
            shutil.rmtree(output_dir_abs)
        
        # Remove from status tracking
        del processing_status[job_id]
        
        return {"message": f"Job {job_id} cleaned up successfully"}
        
    except Exception as e:
        logger.error(f"Error cleaning up job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
