import asyncio
import secrets
import os
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple

import aiosqlite

from database import (
    get_db, create_job, get_job, get_jobs, update_job_status,
    get_running_job, create_steps, get_steps, update_step,
    add_log, get_logs_since
)
from mock_runner import MockRunner

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500 MB
MIN_PHOTOS = 20
MAX_PHOTOS = 100

BACKEND_DIR = Path(__file__).parent
JOBS_DIR = BACKEND_DIR / "jobs"
MOCK_DATA_DIR = BACKEND_DIR / "mock_data"
DB_PATH = BACKEND_DIR / "pipeline.db"


class JobManager:
    def __init__(self):
        self._queues: dict = {}  # job_id -> asyncio.Queue
        self._runners: dict = {}  # job_id -> MockRunner
        self._mock_mode = False
        self._pipeline_runner = None  # placeholder for real PipelineRunner

    def set_mock_mode(self, mock: bool):
        self._mock_mode = mock

    def get_event_queue(self, job_id: str) -> asyncio.Queue:
        if job_id not in self._queues:
            self._queues[job_id] = asyncio.Queue()
        return self._queues[job_id]

    def remove_event_queue(self, job_id: str):
        self._queues.pop(job_id, None)

    async def create_job(
        self, photos: list, opacity_min: float = 0.08,
        iterations: int = 30000, quality: str = "high"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Create a new job. Returns (job_id, error_message)."""

        # Check if another job is running
        db = await get_db()
        try:
            running = await get_running_job(db)
            if running:
                return None, "Another job is currently running. Please wait for it to complete."

            # Validate photos count
            if len(photos) < MIN_PHOTOS:
                return None, f"At least {MIN_PHOTOS} photos required, got {len(photos)}"
            if len(photos) > MAX_PHOTOS:
                return None, f"At most {MAX_PHOTOS} photos allowed, got {len(photos)}"

            # Read all photos into memory and validate
            photo_data = []
            total_size = 0
            for photo in photos:
                filename = photo.filename or ""
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    return None, f"Invalid file type '{ext}' for {filename}. Only JPG/PNG allowed."

                content = await photo.read()
                size = len(content)
                if size > MAX_FILE_SIZE:
                    return None, f"File {filename} exceeds 10MB limit"
                total_size += size
                if not filename:
                    filename = f"image_{len(photo_data)}.jpg"
                photo_data.append((filename, content))

            if total_size > MAX_TOTAL_SIZE:
                return None, f"Total upload size {total_size / 1024 / 1024:.1f}MB exceeds 500MB limit"

            # Generate job_id
            job_id = secrets.token_hex(4)
            job_dir = JOBS_DIR / job_id / "photos"
            job_dir.mkdir(parents=True, exist_ok=True)

            # Save photos to disk
            saved_count = 0
            for filename, content in photo_data:
                photo_path = job_dir / filename
                photo_path.write_bytes(content)
                saved_count += 1

            now = datetime.now(timezone.utc).isoformat()

            # Create DB records
            await create_job(db, job_id, now, opacity_min, iterations, quality, saved_count)
            await create_steps(db, job_id)

            # Add initial log
            await add_log(db, job_id, now, "info", f"Job {job_id} created with {saved_count} photos")

            return job_id, None

        finally:
            await db.close()

    async def start_pipeline(self, job_id: str):
        """Start the pipeline for a given job (async background)."""
        db = await get_db()
        try:
            job = await get_job(db, job_id)
            if not job:
                return
        finally:
            await db.close()

        queue = self.get_event_queue(job_id)

        if self._mock_mode:
            runner = MockRunner(
                job_id=job_id,
                num_photos=job["num_photos"],
                opacity_min=job["opacity_min"],
                iterations=job["iterations"],
                quality=job["quality"],
                jobs_dir=JOBS_DIR,
                mock_data_dir=MOCK_DATA_DIR,
                event_queue=queue,
                db_path=str(DB_PATH)
            )
            self._runners[job_id] = runner
            asyncio.create_task(runner.run())
        else:
            # Placeholder for real PipelineRunner
            pass

    async def get_job_status(self, job_id: str):
        """Get job status with steps."""
        db = await get_db()
        try:
            job = await get_job(db, job_id)
            if not job:
                return None

            steps = await get_steps(db, job_id)

            result = dict(job)
            result["steps"] = steps
            return result

        finally:
            await db.close()

    async def get_job_logs(self, job_id: str, since: str = None):
        """Get job logs with optional since cursor."""
        db = await get_db()
        try:
            job = await get_job(db, job_id)
            if not job:
                return None

            entries = await get_logs_since(db, job_id, since)

            # Determine cursor: the timestamp of the last entry, or "0" if empty
            cursor = entries[-1]["timestamp"] if entries else "0"

            return {
                "job_id": job_id,
                "entries": entries,
                "cursor": cursor
            }

        finally:
            await db.close()

    async def get_job_result(self, job_id: str):
        """Get job result with artifacts."""
        db = await get_db()
        try:
            job = await get_job(db, job_id)
            if not job:
                return None

            if job["status"] != "done":
                return {
                    "job_id": job_id,
                    "status": job["status"],
                    "artifacts": [],
                    "stats": {}
                }

            result_dir = JOBS_DIR / job_id / "result"
            artifacts = []
            if result_dir.exists():
                for f in result_dir.iterdir():
                    if f.is_file():
                        size = f.stat().st_size
                        artifacts.append({
                            "filename": f.name,
                            "size_bytes": size,
                            "url": f"/files/{job_id}/result/{f.name}"
                        })

            # Get stats from DB logs or compute
            steps = await get_steps(db, job_id)
            training_step = next((s for s in steps if s["name"] == "train"), None)
            training_time = training_step["duration_sec"] if training_step else None

            stats = {
                "num_gaussians": None,
                "psnr": None,
                "training_time_sec": training_time,
                "total_points": None,
                "num_photos": job["num_photos"]
            }

            return {
                "job_id": job_id,
                "status": job["status"],
                "artifacts": artifacts,
                "stats": stats
            }

        finally:
            await db.close()

    async def get_gallery(self):
        """Get gallery items from mock_data/gallery.json."""
        import json
        gallery_path = MOCK_DATA_DIR / "gallery.json"
        if gallery_path.exists():
            with open(gallery_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"items": []}


job_manager = JobManager()
