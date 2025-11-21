 # src/api_openrouter.py
"""
Enhanced FastAPI server for RAG system with analytics and feedback
"""
import os
import warnings

# Configure environment before other imports
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

warnings.filterwarnings("ignore")

import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Import our enhanced modules
from rag_engine import RAGEngine
from rate_limiter import RateLimiter, InputValidator
from database import get_db
from auth import get_current_user, require_admin, require_user, auth_manager
from document_manager import DocumentManager
from audit_logger import AuditLogger

USE_V2 = True  # Now using enhanced engine by default
logger.info("Using Enhanced RAG Engine with all optimizations")

# Initialize document manager and audit logger
doc_manager = DocumentManager()
audit_logger = AuditLogger()

# Setup logging
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = DATA_DIR / "api.log"

logger.remove()
logger.add(LOG_FILE, rotation="100 MB", level="INFO")
logger.add(lambda msg: print(msg), level="INFO")

# Initialize FastAPI
app = FastAPI(
    title="RAG Company Chatbot API",
    version="3.0.0",
    description="Enhanced RAG API with analytics and feedback tracking",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Global instances
rag_engine: Optional[RAGEngine] = None
db = get_db()
rate_limiter = RateLimiter(requests_per_minute=60, requests_per_hour=1000) if USE_V2 else None
input_validator = InputValidator() if USE_V2 else None

@app.on_event("startup")
async def startup_event():
    """Initialize RAG engine on startup"""
    global rag_engine
    try:
        logger.info("Initializing RAG Engine...")
        
        # Explicitly load API key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            logger.info(f"✅ API Key loaded: {api_key[:20]}...")
        else:
            logger.warning("⚠️ No API key found - LLM generation will fail")
        
        rag_engine = RAGEngine(api_key=api_key)
        logger.info("✅ RAG Engine initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize RAG Engine: {e}")
        raise

# Pydantic models
class CitationModel(BaseModel):
    """Citation with document reference"""
    doc: str
    chunk: int
    snippet: str
    score: Optional[float] = None

class QueryRequest(BaseModel):
    """Request model for query endpoint"""
    question: str = Field(..., min_length=1, description="The question to answer")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    temperature: float = Field(default=0.0, ge=0, le=2.0, description="Generation temperature (0.0 for policy)")
    model: Optional[str] = Field(default=None, description="LLM model to use")
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation memory")
    user_id: Optional[str] = Field(default=None, description="User ID for RBAC/personalization")
    use_cache: bool = Field(default=True, description="Use cached responses if available")
    conversation_history: Optional[List[Dict]] = Field(default=None, description="Previous conversation turns")

class QueryResponse(BaseModel):
    """Enhanced response model with citations and confidence"""
    query_id: int
    success: bool
    answer: str
    citations: List[CitationModel]
    confidence: float
    should_escalate: bool
    execution_time: float
    model_used: str
    from_cache: bool = False

class FeedbackRequest(BaseModel):
    """Request model for feedback endpoint"""
    query_id: int
    rating: int = Field(..., ge=-1, le=1, description="1 for helpful, -1 for not helpful")
    comment: Optional[str] = None

class AnalyticsResponse(BaseModel):
    """Response model for analytics endpoint"""
    total_queries: int
    successful_queries: int
    success_rate: float
    avg_execution_time: float
    popular_questions: List[Dict]
    popular_documents: List[Dict]
    failed_queries: List[Dict]
    feedback: Dict
    period_days: int

# API Endpoints
@app.post("/query", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequest, 
    req: Request,
    current_user: Dict = Depends(get_current_user)
):
    """
    Process a RAG query (Requires Authentication)
    
    - Retrieves relevant document chunks
    - Generates answer using LLM
    - Logs query for analytics and audit
    - Returns answer with source citations
    """
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG Engine not initialized")
    
    client_ip = req.client.host
    logger.info(f"Query from {current_user['name']} ({client_ip}): {request.question[:100]}...")
    
    # Rate limiting (V2 only)
    if USE_V2 and rate_limiter:
        allowed, reason = rate_limiter.is_allowed(client_ip)
        if not allowed:
            raise HTTPException(status_code=429, detail=reason)
    
    # Input validation (V2 only)
    if USE_V2 and input_validator:
        valid, error_msg = input_validator.validate_question(request.question)
        if not valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        valid_params, error_msg = input_validator.validate_parameters(request.top_k, request.temperature)
        if not valid_params:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Sanitize input
        request.question = input_validator.sanitize_question(request.question)
    
    try:
        # Execute RAG query with enhanced features
        result = await rag_engine.query(
            question=request.question,
            top_k=request.top_k,
            model=request.model,
            temperature=request.temperature,
            session_id=request.session_id,
            use_cache=request.use_cache
        )
        
        # Log to database
        query_id = db.log_query(
            question=request.question,
            answer=result["answer"],
            sources=result["sources"],
            top_k=request.top_k,
            temperature=request.temperature,
            model=result.get("model_used", "unknown"),
            execution_time=result["execution_time"],
            user_ip=client_ip,
            success=result["success"]
        )
        
        # Audit logging for compliance
        audit_logger.log_query(
            query_id=query_id,
            user_id=current_user["user_id"],
            user_role=current_user["role"],
            question=request.question,
            answer=result["answer"],
            retrieved_chunks=result.get("retrieved_chunks", []),
            model_used=result.get("model_used", "unknown"),
            success=result["success"],
            response_time=result["execution_time"],
            tokens_used=result.get("tokens_used"),
            error=result.get("error"),
            ip_address=client_ip
        )
        
        # Log failed query separately if needed
        if not result["success"]:
            db.log_failed_query(request.question, result.get("error", "Unknown error"))
        
        # Citations suppressed for friendlier responses
        citations: List[CitationModel] = []
        
        # Calculate confidence and escalation flag
        confidence = result.get("confidence_score", 0.85)
        should_escalate = confidence < 0.5 or not result["success"]
        
        return QueryResponse(
            query_id=query_id,
            success=result["success"],
            answer=result["answer"],
            citations=citations,
            confidence=confidence,
            should_escalate=should_escalate,
            execution_time=result["execution_time"],
            model_used=result.get("model_used", "unknown"),
            from_cache=result.get("from_cache", False)
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        # Log failed query
        db.log_failed_query(request.question, str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit user feedback for a query
    
    - Tracks helpful/not helpful ratings
    - Stores optional comments
    - Used for continuous improvement
    """
    try:
        db.log_feedback(
            query_id=feedback.query_id,
            rating=feedback.rating,
            comment=feedback.comment
        )
        return {"success": True, "message": "Feedback recorded"}
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(days: int = 7):
    """
    Get analytics for the last N days
    
    - Total queries and success rate
    - Popular questions
    - Most used documents
    - Failed queries
    - User feedback stats
    """
    try:
        analytics = db.get_analytics(days=days)
        return AnalyticsResponse(**analytics)
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def get_models():
    """Get list of available LLM models"""
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG Engine not initialized")
    
    return {"models": rag_engine.get_available_models()}

@app.get("/stats")
async def get_stats():
    """Get RAG engine statistics"""
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG Engine not initialized")
    
    return rag_engine.get_stats()

# Root endpoint with HTML response
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with HTML interface"""
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>RAG API Service</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .status { color: green; }
                .links { margin-top: 20px; }
                a { color: #0066cc; text-decoration: none; margin-right: 20px; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>RAG API Service</h1>
                <p class="status">✅ API is running successfully</p>
                <div class="links">
                    <a href="/docs">📚 API Documentation (Swagger UI)</a>
                    <a href="/redoc">📖 API Reference (ReDoc)</a>
                    <a href="/health">🔍 System Health</a>
                </div>
            </div>
        </body>
    </html>
    """

@app.get("/health")
async def healthcheck():
    """Enhanced healthcheck endpoint with detailed system status"""
    try:
        if not rag_engine:
            return {"status": "initializing", "message": "RAG Engine is starting up"}
        
        stats = rag_engine.get_stats()
        return {
            "status": "healthy",
            "version": "3.0.0",
            "embedding_model": stats["embedding_model"],
            "total_chunks": stats["total_chunks"],
            "documents": len(stats["documents"]),
            "api_ready": bool(os.getenv("OPENROUTER_API_KEY"))
        }
    except Exception as e:
        logger.error(f"Healthcheck failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/metrics")
async def get_metrics():
    """Get performance metrics (V2 only)"""
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG Engine not initialized")
    
    try:
        if hasattr(rag_engine, 'get_metrics'):
            return rag_engine.get_metrics()
        else:
            return {"message": "Metrics not available in basic engine"}
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitoring/summary")
async def get_monitoring_summary(hours: int = 24):
    """Get detailed monitoring summary (V2 only)"""
    if not rag_engine or not USE_V2:
        raise HTTPException(status_code=503, detail="Monitoring not available")
    
    try:
        return rag_engine.monitor.get_performance_summary(hours=hours)
    except Exception as e:
        logger.error(f"Error getting monitoring summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitoring/health")
async def get_health_status():
    """Get system health status"""
    try:
        return rag_engine.monitor.get_health_status()
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== ADMIN ENDPOINTS ==========

@app.post("/admin/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    current_user: Dict = Depends(require_admin)
):
    """
    Upload document (Admin only)
    Auto-triggers reindex if content changed
    """
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.txt', '.docx', '.md']
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not allowed. Allowed: {allowed_extensions}"
            )
        
        # Read file content
        content = await file.read()
        
        # Upload with versioning
        result = doc_manager.upload_document(
            file_content=content,
            filename=file.filename,
            uploaded_by=current_user["user_id"]
        )
        
        # Trigger reindex if needed
        if result["needs_reindex"]:
            logger.info(f"Triggering reindex after document upload: {file.filename}")
            # TODO: Implement async reindex
            # await trigger_reindex()
            result["reindex_status"] = "pending"
        
        return {
            "success": True,
            **result,
            "uploaded_by": current_user["name"]
        }
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin/delete-document/{filename}")
async def delete_document(
    filename: str,
    current_user: Dict = Depends(require_admin)
):
    """Delete document (Admin only)"""
    try:
        result = doc_manager.delete_document(filename)
        
        if result["status"] == "error":
            raise HTTPException(status_code=404, detail=result["message"])
        
        if result["needs_reindex"]:
            logger.info(f"Triggering reindex after document deletion: {filename}")
            result["reindex_status"] = "pending"
        
        return {
            "success": True,
            **result,
            "deleted_by": current_user["name"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/list-documents")
async def list_documents(current_user: Dict = Depends(require_admin)):
    """List all documents (Admin only)"""
    try:
        docs = doc_manager.list_documents()
        return {
            "success": True,
            "documents": docs,
            "total": len(docs)
        }
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/document-info/{filename}")
async def get_document_info(
    filename: str,
    current_user: Dict = Depends(require_admin)
):
    """Get document information (Admin only)"""
    try:
        info = doc_manager.get_document_info(filename)
        if not info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "success": True,
            "document": info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/generate-api-key")
async def generate_api_key(
    user_id: str,
    role: str,
    name: str,
    current_user: Dict = Depends(require_admin)
):
    """Generate new API key (Admin only)"""
    try:
        from auth import UserRole
        
        # Validate role
        try:
            user_role = UserRole(role)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}"
            )
        
        # Generate key
        api_key = auth_manager.generate_api_key(user_id, user_role, name)
        
        return {
            "success": True,
            "api_key": api_key,
            "user_id": user_id,
            "role": role,
            "name": name,
            "message": "API key generated. Save it securely - it won't be shown again."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/audit-summary")
async def get_audit_summary(
    date: Optional[str] = None,
    current_user: Dict = Depends(require_admin)
):
    """Get audit summary for a specific date (Admin only)"""
    try:
        summary = audit_logger.get_audit_summary(date)
        return {
            "success": True,
            **summary
        }
    except Exception as e:
        logger.error(f"Error getting audit summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/audit-search")
async def search_audit_logs(
    user_id: Optional[str] = None,
    limit: int = 100,
    current_user: Dict = Depends(require_admin)
):
    """Search audit logs (Admin only)"""
    try:
        results = audit_logger.search_audit_logs(user_id=user_id, limit=limit)
        return {
            "success": True,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        logger.error(f"Error searching audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    # Log startup information
    logger.info("="*60)
    logger.info("🚀 RAG Company Chatbot API Server")
    logger.info("="*60)
    logger.info(f"📂 Data directory: {DATA_DIR}")
    logger.info(f"🔑 API Key set: {'Yes' if os.getenv('OPENROUTER_API_KEY') else 'No'}")
    logger.info("="*60)
    
    # Run the server
    uvicorn.run(
        "api_openrouter:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False,
        workers=1
    )

