import sys
import os
import json
import asyncio
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, Form, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.types import ASGIApp, Scope, Receive, Send

from database import init_db, get_db, get_job, get_logs_since
from job_manager import job_manager
from models import (
    CreateJobResponse, JobResponse, LogsResponse, ResultResponse,
    GalleryResponse, ErrorResponse, WsEvent, StepResponse
)

# --- Mock mode flag (use env var to survive uvicorn reload) ---
MOCK_MODE = os.environ.get("RT_PIPELINE_MOCK", "0") == "1"

# --- App Setup ---
BACKEND_DIR = Path(__file__).parent.resolve()
JOBS_DIR = BACKEND_DIR / "jobs"
MOCK_DATA_DIR = BACKEND_DIR / "mock_data"

JOBS_DIR.mkdir(parents=True, exist_ok=True)
MOCK_DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="RT Pipeline API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def no_store_api_responses(request, call_next):
    """API 响应一律 no-store。

    否则浏览器会启发式缓存 /api/jobs/{id}/result 这类响应，
    页面可能拿到过期的产物 URL（指向已被替换的旧模型），
    造成「预览的是旧模型、下载的是新文件」这种分叉。
    """
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response

# Wrap static mounts with CORS headers (CORSMiddleware doesn't cover static files)
class CORSStaticFiles:
    """Wraps StaticFiles to add CORS headers, since CORSMiddleware skips mounted apps."""
    def __init__(self, directory: str):
        self.app = StaticFiles(directory=directory)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            async def cors_send(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    headers[b"access-control-allow-origin"] = b"*"
                    # 必须带 no-cache：否则浏览器会用启发式规则把旧响应当"新鲜"缓存、
                    # 不回源校验，模型文件被替换后页面仍渲染旧内容（展示与下载分叉）
                    headers[b"cache-control"] = b"no-cache"
                    message["headers"] = list(headers.items())
                await send(message)
            await self.app(scope, receive, cors_send)
        else:
            await self.app(scope, receive, send)

# Mount static file serving
app.mount("/mock_data", CORSStaticFiles(directory=str(MOCK_DATA_DIR)), name="mock_data")
app.mount("/files", CORSStaticFiles(directory=str(JOBS_DIR)), name="job_files")


@app.on_event("startup")
async def startup():
    await init_db()
    job_manager.set_mock_mode(MOCK_MODE)


# --- REST Routes ---

@app.post("/api/jobs", response_model=CreateJobResponse)
async def create_job(
    opacity_min: float = Form(default=0.09),
    iterations: int = Form(default=30000),
    quality: str = Form(default="high"),
    photos: List[UploadFile] = File(...)
):
    """Create a new pipeline job with uploaded photos."""

    job_id, error = await job_manager.create_job(
        photos=photos,
        opacity_min=opacity_min,
        iterations=iterations,
        quality=quality
    )

    if error:
        if "currently running" in error:
            raise HTTPException(status_code=409, detail=error)
        raise HTTPException(status_code=400, detail=error)

    # Start pipeline asynchronously
    asyncio.create_task(job_manager.start_pipeline(job_id))

    return CreateJobResponse(
        job_id=job_id,
        message=f"Job {job_id} created successfully with pipeline started"
    )


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get job status with all steps."""
    result = await job_manager.get_job_status(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@app.get("/api/jobs/{job_id}/logs", response_model=LogsResponse)
async def get_job_logs(job_id: str, since: Optional[str] = Query(default=None)):
    """Get job logs, optionally since a cursor timestamp."""
    result = await job_manager.get_job_logs(job_id, since)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@app.get("/api/jobs/{job_id}/result", response_model=ResultResponse)
async def get_job_result(job_id: str):
    """Get job result with artifacts and stats."""
    result = await job_manager.get_job_result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@app.get("/api/gallery", response_model=GalleryResponse)
async def get_gallery():
    """Get pre-built demo gallery items."""
    result = await job_manager.get_gallery()
    return result


# --- WebSocket Route ---

@app.websocket("/ws/jobs/{job_id}")
async def websocket_job(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job updates."""
    await websocket.accept()

    # Verify job exists
    db = await get_db()
    try:
        job = await get_job(db, job_id)
        if not job:
            await websocket.send_json({"type": "error", "data": {"message": "Job not found"}})
            await websocket.close()
            return
    finally:
        await db.close()

    queue = job_manager.get_event_queue(job_id)

    # Send current status on connect
    current = await job_manager.get_job_status(job_id)
    if current:
        await websocket.send_json({
            "type": "status",
            "data": {"status": current["status"], "job": current}
        })

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                # Check for client ping
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                except asyncio.TimeoutError:
                    pass

            # Check if job is done/failed to close gracefully
            db_check = await get_db()
            try:
                job_status = await get_job(db_check, job_id)
                if job_status and job_status["status"] in ("done", "failed"):
                    # Drain remaining events
                    while not queue.empty():
                        event = queue.get_nowait()
                        await websocket.send_json(event)
                    break
            finally:
                await db_check.close()

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# --- CLI Entry Point ---

def main():
    import argparse
    parser = argparse.ArgumentParser(description="RT Pipeline API Server")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode with MockRunner")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8010, help="Port to bind")
    args = parser.parse_args()

    # Set env var so uvicorn worker processes can read it
    os.environ["RT_PIPELINE_MOCK"] = "1" if args.mock else "0"

    import uvicorn
    uvicorn.run("main:app", host=args.host, port=args.port, reload=True)


if __name__ == "__main__":
    main()
