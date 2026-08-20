import uuid
import threading
import logging
from typing import Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from translator_engine import process_pdf_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

app = FastAPI(title="PDF Layout-Preserving Translator", version="1.0.0")

# In-memory store for translation jobs
# In production, this can be Redis or DB
JOBS: Dict[str, Dict[str, Any]] = {}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB Limit

# Setup static files and templates
import os
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def run_translation_job(job_id: str, pdf_bytes: bytes, target_lang: str, original_filename: str):
    """
    Background worker thread function for translating PDF.
    """
    try:
        def update_progress(current_page: int, total_pages: int, message: str):
            pct = int((current_page / max(total_pages, 1)) * 100)
            JOBS[job_id].update({
                "progress": pct,
                "current_page": current_page,
                "total_pages": total_pages,
                "message": message
            })

        JOBS[job_id]["message"] = "Reading PDF document structure..."
        
        translated_pdf = process_pdf_document(
            pdf_bytes=pdf_bytes,
            target_lang=target_lang,
            progress_callback=update_progress
        )

        out_name = f"translated_{target_lang}_{original_filename}"
        if not out_name.lower().endswith(".pdf"):
            out_name += ".pdf"

        JOBS[job_id].update({
            "status": "completed",
            "progress": 100,
            "message": "Translation completed successfully!",
            "result_bytes": translated_pdf,
            "download_filename": out_name
        })

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        JOBS[job_id].update({
            "status": "failed",
            "progress": 0,
            "message": f"Error during translation: {str(e)}",
            "error": str(e)
        })


@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """
    Renders the modern single-page frontend.
    """
    return templates.TemplateResponse(request=request, name="index.html")



@app.post("/api/translate")
async def start_translation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_lang: str = Form(...)
):
    """
    Upload endpoint for PDF translation.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported.")

    file_bytes = await file.read()
    
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="The uploaded PDF file is empty.")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds limit of {MAX_FILE_SIZE // (1024*1024)}MB.")

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "status": "processing",
        "progress": 0,
        "current_page": 0,
        "total_pages": 0,
        "message": "Initializing document processor...",
        "result_bytes": None,
        "filename": file.filename,
        "target_lang": target_lang,
        "error": None
    }

    # Launch translation background thread
    background_tasks.add_task(
        run_translation_job,
        job_id,
        file_bytes,
        target_lang,
        file.filename
    )

    return {"job_id": job_id, "status": "processing", "message": "Translation job created successfully."}


@app.get("/api/progress/{job_id}")
async def get_progress(job_id: str):
    """
    Real-time progress polling endpoint.
    """
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Translation job not found.")

    job = JOBS[job_id]
    return {
        "status": job["status"],
        "progress": job["progress"],
        "current_page": job["current_page"],
        "total_pages": job["total_pages"],
        "message": job["message"],
        "error": job.get("error")
    }


from urllib.parse import quote

@app.get("/api/download/{job_id}")
async def download_translated_pdf(job_id: str):
    """
    Download endpoint for completed translated PDF.
    """
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Translation job not found.")

    job = JOBS[job_id]
    if job["status"] != "completed" or not job.get("result_bytes"):
        raise HTTPException(status_code=400, detail="Translated document is not ready or failed.")

    filename = job.get("download_filename", "translated_document.pdf")
    
    # Sanitize ASCII fallback and UTF-8 quote for RFC 5987 standard HTTP headers
    safe_ascii_filename = "".join(c for c in filename if ord(c) < 128 and c not in '"\r\n\\')
    if not safe_ascii_filename or not safe_ascii_filename.lower().endswith(".pdf"):
        safe_ascii_filename = "translated_document.pdf"

    encoded_filename = quote(filename)

    return Response(
        content=job["result_bytes"],
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}'
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
