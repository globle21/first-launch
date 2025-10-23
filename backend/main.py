"""
FastAPI Backend for Product Discovery System
Provides REST API and Server-Sent Events for real-time updates
"""

import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import threading
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

from session_manager import session_manager
from workflow_async import run_workflow_async


# FastAPI app
app = FastAPI(
    title="Product Discovery API",
    description="Backend for product discovery with price comparison",
    version="1.0.0"
)

# CORS middleware (allow frontend from any origin in development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class StartWorkflowRequest(BaseModel):
    input_type: str  # "keyword" or "url"
    user_input: str


class StartWorkflowResponse(BaseModel):
    session_id: str
    message: str


class ConfirmProductRequest(BaseModel):
    product_index: int


class ConfirmVariantRequest(BaseModel):
    variant_index: int


class ConfirmExtractionRequest(BaseModel):
    confirmed: bool


class StatusResponse(BaseModel):
    session_id: str
    status: str  # running, waiting_confirmation, completed, failed
    current_stage: str
    needs_product_confirmation: bool
    needs_variant_confirmation: bool
    needs_url_extraction_confirmation: bool
    product_candidates: list = []
    variant_candidates: list = []
    extracted_details: Optional[dict] = None
    final_results: Optional[list] = None
    error_message: Optional[str] = None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "service": "Product Discovery API",
        "version": "1.0.0",
        "active_sessions": session_manager.get_session_count()
    }


@app.post("/api/workflow/start", response_model=StartWorkflowResponse)
async def start_workflow(request: StartWorkflowRequest):
    """
    Start a new workflow session
    
    - **input_type**: "keyword" or "url"
    - **user_input**: Product keywords or product URL
    """
    
    # Validate input
    if request.input_type not in ["keyword", "url"]:
        raise HTTPException(status_code=400, detail="input_type must be 'keyword' or 'url'")
    
    if not request.user_input.strip():
        raise HTTPException(status_code=400, detail="user_input cannot be empty")
    
    # Create session
    session_id = session_manager.create_session(
        input_type=request.input_type,
        user_input=request.user_input
    )
    
    # Start workflow in background thread
    thread = threading.Thread(
        target=run_workflow_async,
        args=(session_id, request.input_type, request.user_input),
        daemon=True
    )
    thread.start()
    
    return StartWorkflowResponse(
        session_id=session_id,
        message="Workflow started successfully"
    )


@app.get("/api/workflow/status/{session_id}", response_model=StatusResponse)
async def get_workflow_status(session_id: str):
    """
    Get current status of a workflow session
    """
    
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return StatusResponse(
        session_id=session.session_id,
        status=session.status,
        current_stage=session.current_stage,
        needs_product_confirmation=session.needs_product_confirmation,
        needs_variant_confirmation=session.needs_variant_confirmation,
        needs_url_extraction_confirmation=session.needs_url_extraction_confirmation,
        product_candidates=session.product_candidates,
        variant_candidates=session.variant_candidates,
        extracted_details=session.extracted_details,
        final_results=session.final_results,
        error_message=session.error_message
    )


@app.post("/api/workflow/confirm-product/{session_id}")
async def confirm_product(session_id: str, request: ConfirmProductRequest):
    """
    Confirm product selection
    """
    
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.needs_product_confirmation:
        raise HTTPException(status_code=400, detail="Product confirmation not needed")
    
    success = session_manager.confirm_product(session_id, request.product_index)
    
    if not success:
        raise HTTPException(status_code=400, detail="Invalid product index")
    
    return {"message": "Product confirmed", "product_index": request.product_index}


@app.post("/api/workflow/confirm-variant/{session_id}")
async def confirm_variant(session_id: str, request: ConfirmVariantRequest):
    """
    Confirm variant selection
    """
    
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.needs_variant_confirmation:
        raise HTTPException(status_code=400, detail="Variant confirmation not needed")
    
    success = session_manager.confirm_variant(session_id, request.variant_index)
    
    if not success:
        raise HTTPException(status_code=400, detail="Invalid variant index")
    
    return {"message": "Variant confirmed", "variant_index": request.variant_index}


@app.post("/api/workflow/confirm-extraction/{session_id}")
async def confirm_extraction(session_id: str, request: ConfirmExtractionRequest):
    """
    Confirm or reject URL extraction
    """
    
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.needs_url_extraction_confirmation:
        raise HTTPException(status_code=400, detail="URL extraction confirmation not needed")
    
    success = session_manager.confirm_url_extraction(session_id, request.confirmed)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to confirm extraction")
    
    return {
        "message": "Extraction confirmed" if request.confirmed else "Extraction rejected",
        "confirmed": request.confirmed
    }


@app.get("/api/workflow/results/{session_id}")
async def get_results(session_id: str):
    """
    Get final results for a completed workflow
    """
    
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Workflow not completed. Current status: {session.status}"
        )
    
    return {
        "session_id": session.session_id,
        "results": session.final_results,
        "total_results": len(session.final_results) if session.final_results else 0
    }


@app.get("/api/workflow/progress/{session_id}")
async def stream_progress(session_id: str):
    """
    Server-Sent Events endpoint for real-time progress updates
    """
    
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    async def event_generator():
        """Generate SSE events"""
        last_log_count = 0
        
        while True:
            session = session_manager.get_session(session_id)
            
            if not session:
                # Session expired
                yield f"data: {json.dumps({'type': 'error', 'message': 'Session expired'})}\n\n"
                break
            
            # Send new logs
            current_logs = session.progress_logs
            if len(current_logs) > last_log_count:
                new_logs = current_logs[last_log_count:]
                for log in new_logs:
                    yield f"data: {json.dumps({'type': 'log', 'data': log})}\n\n"
                last_log_count = len(current_logs)
            
            # Send status update
            status_data = {
                "type": "status",
                "data": {
                    "status": session.status,
                    "current_stage": session.current_stage,
                    "needs_product_confirmation": session.needs_product_confirmation,
                    "needs_variant_confirmation": session.needs_variant_confirmation,
                    "needs_url_extraction_confirmation": session.needs_url_extraction_confirmation
                }
            }
            yield f"data: {json.dumps(status_data)}\n\n"
            
            # If completed or failed, send final event and close
            if session.status in ["completed", "failed"]:
                final_data = {
                    "type": "complete" if session.status == "completed" else "error",
                    "data": {
                        "status": session.status,
                        "results": session.final_results if session.status == "completed" else None,
                        "error": session.error_message if session.status == "failed" else None
                    }
                }
                yield f"data: {json.dumps(final_data)}\n\n"
                break
            
            await asyncio.sleep(1)  # Poll every second
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    print("="*80)
    print("🚀 Product Discovery API Starting")
    print("="*80)
    print(f"✅ Environment variables loaded")
    print(f"✅ Session manager initialized")
    print("="*80)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup tasks"""
    print("\n👋 Shutting down Product Discovery API")


# Development server
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    print("\n" + "="*80)
    print("🔧 DEVELOPMENT MODE")
    print("="*80)
    print(f"Server: http://localhost:{port}")
    print(f"API Docs: http://localhost:{port}/docs")
    print("="*80 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False  # Disable reload to avoid import issues
    )
