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
from mock_runner import MockRunner, read_ply_vertex_count
from local_runner import LocalRunner

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB

BACKEND_DIR = Path(__file__).parent
JOBS_DIR = BACKEND_DIR / "jobs"
MOCK_DATA_DIR = BACKEND_DIR / "mock_data"
DB_PATH = BACKEND_DIR / "pipeline.db"
PIPELINE_DIR = Path(os.environ.get("RT_PIPELINE_DIR", str(Path.home() / "huolong_run")))


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

            # 照片数量不做限制：至少 1 张（空提交没有意义），张数上限不设
            if len(photos) == 0:
                return None, "未收到任何照片，请至少选择 1 张"

            # 只做校验（格式 / 单张大小 / 总大小），不把照片写入磁盘。
            # 当前是 mock 模式，照片不参与任何计算，落盘只是白占磁盘。
            # 注意：将来接入真实 pipeline（SSH 调服务器跑 COLMAP）时必须改回保存，
            # 否则服务器上没有图片可用。
            total_size = 0
            for index, photo in enumerate(photos):
                filename = photo.filename or f"image_{index}.jpg"
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    return None, f"Invalid file type '{ext}' for {filename}. Only JPG/PNG allowed."

                size = len(await photo.read())
                if size > MAX_FILE_SIZE:
                    return None, f"File {filename} exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit"
                total_size += size

            if total_size > MAX_TOTAL_SIZE:
                return None, f"Total upload size {total_size / 1024 / 1024:.1f}MB exceeds {MAX_TOTAL_SIZE // (1024*1024)}MB limit"

            # Generate job_id
            job_id = secrets.token_hex(4)
            now = datetime.now(timezone.utc).isoformat()

            # Create DB records
            await create_job(db, job_id, now, opacity_min, iterations, quality, len(photos))
            await create_steps(db, job_id)

            # Add initial log
            await add_log(db, job_id, now, "info", f"Job {job_id} created with {len(photos)} photos")

            # 真实模式：照片必须落盘，服务器上的 run.sh 才能读到。
            # mock 模式照片不参与计算，不落盘（校验循环里读过，这里要 seek 回开头）
            # 统一重命名为 img_001.jpg 等格式：
            #   1) 避免文件名含空格/中文/特殊字符导致 hloc / COLMAP 子模块解析失败
            #   2) 扩展名保持原始（jpg/png 都支持），数量跟提交完全一致
            if not self._mock_mode:
                photos_dir = JOBS_DIR / job_id / "photos"
                photos_dir.mkdir(parents=True, exist_ok=True)
                for index, photo in enumerate(photos):
                    await photo.seek(0)
                    orig = photo.filename or f"image_{index}.jpg"
                    ext = os.path.splitext(orig)[1].lower()
                    if ext not in ALLOWED_EXTENSIONS:
                        ext = ".jpg"
                    safe_name = f"img_{index + 1:03d}{ext}"
                    content = await photo.read()
                    (photos_dir / safe_name).write_bytes(content)

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
            gpu_id = await self._pick_gpu()
            runner = LocalRunner(
                job_id=job_id,
                num_photos=job["num_photos"],
                opacity_min=job["opacity_min"],
                iterations=job["iterations"],
                quality=job["quality"],
                jobs_dir=JOBS_DIR,
                pipeline_dir=PIPELINE_DIR,
                event_queue=queue,
                db_path=str(DB_PATH),
                gpu_id=gpu_id
            )
            self._runners[job_id] = runner
            asyncio.create_task(runner.run())

    async def _pick_gpu(self) -> int:
        """选当前显存占用最少的 GPU，避开服务器上其他人正在用的卡。"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "nvidia-smi", "--query-gpu=index,memory.used",
                "--format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            out, _ = await proc.communicate()
            best, best_mem = 0, 10 ** 12
            for line in out.decode().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) == 2:
                    idx, used = int(parts[0]), int(parts[1])
                    if used < best_mem:
                        best, best_mem = idx, used
            return best
        except Exception:
            return 0

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
            num_gaussians = None
            if result_dir.exists():
                for f in sorted(result_dir.iterdir()):
                    if f.is_file():
                        stat = f.stat()
                        # URL 带版本号：文件被替换后 URL 随之变化，
                        # 避免浏览器命中旧的缓存条目（展示与下载分叉）
                        version = f"{int(stat.st_mtime)}-{stat.st_size}"
                        artifacts.append({
                            "filename": f.name,
                            "size_bytes": stat.st_size,
                            "url": f"/files/{job_id}/result/{f.name}?v={version}"
                        })
                        # 直接读 PLY 头部，拿到真实的高斯点数量
                        if num_gaussians is None and f.suffix.lower() == ".ply":
                            num_gaussians = read_ply_vertex_count(f)

            # Get stats from DB logs or compute
            steps = await get_steps(db, job_id)
            training_step = next((s for s in steps if s["name"] == "train"), None)
            training_time = training_step["duration_sec"] if training_step else None

            stats = {
                "num_gaussians": num_gaussians,
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
