import logging
import os
import io
import time
import uuid
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pypdf import PdfReader
import uvicorn

from rag_core import RAGEngine

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Models for Modern API ---

class IngestRequest(BaseModel):
    text: str
    title: Optional[str] = "Untitled"

class IngestResponse(BaseModel):
    status: str
    message: str
    doc_id: str

class QueryRequest(BaseModel):
    query: str

class Citation(BaseModel):
    text: str
    metadata: Dict[str, Any]
    score: Optional[float] = None

class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    timing: float
    cost_estimate: Optional[str] = None

# --- Lifespan & App Initialization ---

rag_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global rag_engine
    logger.info("Initializing RAG Engine...")
    rag_engine = RAGEngine()
    logger.info("RAG Engine ready.")
    yield
    # Shutdown
    logger.info("Shutting down...")

app = FastAPI(
    title="Mini RAG API", 
    description="A simple modern API for RAG ingestion and querying.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routes ---

@app.post("/ingest", response_model=IngestResponse, summary="Ingest Raw Text")
async def ingest_text(request: IngestRequest):
    """
    Ingests raw text into the RAG system.
    """
    try:
        doc_id = str(uuid.uuid4())
        metadata = {
            "doc_id": doc_id,
            "title": request.title,
            "source": "text_input",
            "timestamp": time.time()
        }
        
        chunk_count = rag_engine.ingest_document(request.text, metadata)
        
        return IngestResponse(
            status="success", 
            message=f"Ingested {chunk_count} chunks.", 
            doc_id=doc_id
        )
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/file", response_model=IngestResponse, summary="Ingest File (PDF/Text)")
async def ingest_file(file: UploadFile = File(...)):
    """
    Ingests a file (PDF or Text) into the RAG system.
    """
    try:
        content = await file.read()
        logger.info(f"Ingesting file: {file.filename} ({file.content_type})")
        
        # Check file type
        if file.content_type == "application/pdf" or file.filename.lower().endswith(".pdf"):
            try:
                pdf_file = io.BytesIO(content)
                reader = PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            except Exception as pdf_err:
                raise HTTPException(status_code=400, detail=f"Error reading PDF: {str(pdf_err)}")
        else:
            # Assume text/markdown
            try:
                text = content.decode("utf-8") 
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="File encoding not supported. Please upload a UTF-8 text file or PDF.")
        
        if not text.strip():
             raise HTTPException(status_code=400, detail="Extracted text is empty.")

        doc_id = str(uuid.uuid4())
        metadata = {
            "doc_id": doc_id,
            "title": file.filename,
            "source": "file_upload",
            "timestamp": time.time()
        }
        
        chunk_count = rag_engine.ingest_document(text, metadata)
        
        return IngestResponse(
            status="success", 
            message=f"Ingested {chunk_count} chunks from {file.filename}.", 
            doc_id=doc_id
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"File ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse, summary="Query RAG System")
async def query_rag(request: QueryRequest):
    """
    Queries the RAG system and returns an abstractive answer with citations.
    """
    try:
        start_time = time.time()
        
        # 1. Retrieve & Rerank
        context = rag_engine.search(request.query)
        
        if not context:
            return QueryResponse(
                answer="I couldn't find any relevant information in the uploaded documents.",
                citations=[],
                timing=time.time() - start_time
            )

        # 2. Generate Answer
        result = rag_engine.generate_answer(request.query, context)
        
        elapsed = time.time() - start_time
        
        return QueryResponse(
            answer=result['answer'],
            citations=result['citations'],
            timing=elapsed,
            cost_estimate="Depends on provider" 
        )
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Static Files / SPA Fallback ---
frontend_dist_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(frontend_dist_path):
    # Mount assets (JS/CSS)
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_path, "assets")), name="assets")
    
    # Catch-all for SPA routing (returns index.html)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # API routes are already handled above, so this catches everything else
        index_path = os.path.join(frontend_dist_path, "index.html")
        if os.path.exists(index_path):
             return FileResponse(index_path)
        else:
             return {"status": "error", "message": "Frontend index.html not found"}
else:
    @app.get("/")
    def read_root():
        return {"status": "ok", "message": "Backend running. Frontend build not found."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
