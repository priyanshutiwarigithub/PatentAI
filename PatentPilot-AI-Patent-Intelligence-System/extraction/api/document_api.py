# api/document_api.py

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import shutil
import tempfile
import os
from agents.document_extraction_agent import run_extraction

app = FastAPI(title="SciNexus Document AI API", version="1.0.0")

@app.post("/extract", summary="Extract structured data from a PDF")
async def extract_document(file: UploadFile = File(...)):
    """
    Upload a PDF (digital or scanned) and receive structured JSON output.
    This endpoint is called by the Literature Retrieval Agent to process
    downloaded papers.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = run_extraction(tmp_path)
        return JSONResponse(content=result.model_dump(mode="json"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "SciNexus Document AI Agent"}