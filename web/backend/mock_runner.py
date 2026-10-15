import asyncio
import random
import time
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STEP_NAMES = ["upload", "colmap", "train", "denoise", "export"]
STEP_SECONDS = 10  # seconds per step (demo mode; set to 30 for production)

# 预置的真实模型：换演示结果只要替换 mock_data 下的这个文件，
# 高斯点数量会在运行时从 PLY 头部读取，不需要改代码
MOCK_PLY_NAME = "denoised_3dgs.ply"


def read_ply_vertex_count(path: Path) -> Optional[int]:
    """只读 PLY 头部，取出顶点（高斯点）数量。"""
    try:
        with open(path, "rb") as f:
            head = f.read(4096).decode("ascii", errors="ignore")
    except OSError:
        return None

    marker = "element vertex "
    idx = head.find(marker)
    if idx < 0:
        return None
    token = head[idx + len(marker):].split(maxsplit=1)[0]
    try:
        return int(token)
    except ValueError:
        return None


class MockRunner:
    def __init__(self, job_id: str, num_photos: int, opacity_min: float,
                 iterations: int, quality: str, jobs_dir: Path,
                 mock_data_dir: Path, event_queue: asyncio.Queue,
                 db_path: str):
        self.job_id = job_id
        self.num_photos = num_photos
        self.opacity_min = opacity_min
        self.iterations = iterations
        self.quality = quality
        self.jobs_dir = jobs_dir
        self.mock_data_dir = mock_data_dir
        self.event_queue = event_queue
        self.db_path = db_path
        self._cancelled = False
        self._training_start = None

        # 用真实模型的高斯点数量，保证日志与最终产物一致
        count = read_ply_vertex_count(mock_data_dir / MOCK_PLY_NAME) or 0
        self._num_gaussians = count
        # 去噪会移除 opacity 低于阈值的高斯点，这里反推出训练后的数量
        self._pre_denoise = round(count / 0.58) if count else 0

    def cancel(self):
        self._cancelled = True

    async def _push_event(self, event_type: str, data: dict):
        await self.event_queue.put({"type": event_type, "data": data})

    async def _add_log(self, level: str, line: str):
        ts = datetime.now(timezone.utc).isoformat()
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO logs (job_id, timestamp, level, line) VALUES (?, ?, ?, ?)",
                (self.job_id, ts, level, line)
            )
            await db.commit()

        await self._push_event("log", {
            "timestamp": ts,
            "level": level,
            "line": line
        })

    async def _update_step_db(self, name: str, status: str, progress: float, duration_sec: float = None):
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            fields = ["status = ?", "progress = ?"]
            params = [status, progress]
            if duration_sec is not None:
                fields.append("duration_sec = ?")
                params.append(duration_sec)
            params.extend([self.job_id, name])
            await db.execute(
                f"UPDATE steps SET {', '.join(fields)} WHERE job_id = ? AND name = ?",
                params
            )
            await db.commit()

    def _get_step_logs(self, step_name: str):
        """Generate log entries for a step with pre-filled values."""
        if step_name == "upload":
            return [
                ("info", "Receiving photos..."),
                ("info", f"Validating {self.num_photos} images..."),
                ("info", "Checking file formats..."),
                ("info", "Verifying image dimensions..."),
                ("info", "All checks passed"),
                ("info", "Photos staged for processing"),
            ]
        elif step_name == "colmap":
            keypoints = random.randint(2000, 8000)
            return [
                ("info", "Starting COLMAP pipeline..."),
                ("info", "Feature extraction started..."),
                ("info", f"Detected {keypoints} keypoints per image"),
                ("info", "Feature extraction complete"),
                ("info", "Feature matching started..."),
                ("info", "Processing matching pairs with exhaustive matcher..."),
                ("info", "Feature matching complete"),
                ("info", "Sparse reconstruction started..."),
                ("info", f"Registered {self.num_photos}/{self.num_photos} images"),
                ("info", "Sparse reconstruction done"),
                ("info", "Camera poses estimated"),
            ]
        elif step_name == "train":
            loss_values = [0.452, 0.321, 0.284, 0.152, 0.113, 0.087, 0.064, 0.048, 0.036, 0.029]
            iter_ratios = [0.03, 0.07, 0.10, 0.17, 0.23, 0.33, 0.50, 0.67, 0.83, 1.00]
            iter_values = [max(1, round(self.iterations * r)) for r in iter_ratios]
            sparse_points = max(1000, self._num_gaussians // 8)
            densify_1 = round(self._pre_denoise * 0.62)

            logs = [
                ("info", "Initializing 3D Gaussian Splatting training..."),
                ("info", f"Loading sparse point cloud with {sparse_points} points"),
                ("info", f"Starting training with {self.iterations} iterations, quality={self.quality}"),
            ]
            for it, loss in zip(iter_values, loss_values):
                logs.append(("info", f"Training iter {it}/{self.iterations} loss={loss:.3f}"))
            logs.extend([
                ("info", f"Densification at iter {iter_values[3]}: {densify_1} gaussians"),
                ("info", f"Densification at iter {iter_values[6]}: {self._pre_denoise} gaussians"),
                ("info", "Pruning unnecessary gaussians..."),
                ("info", f"Training complete. {self._pre_denoise} gaussians, final loss=0.029"),
            ])
            return logs
        elif step_name == "denoise":
            removed = self._pre_denoise - self._num_gaussians
            kept_pct = round(self._num_gaussians / self._pre_denoise * 100) if self._pre_denoise else 100
            return [
                ("info", "Loading trained 3DGS point cloud..."),
                ("info", f"Applying opacity filter (min={round(self.opacity_min, 2)})..."),
                ("info", f"Removed {removed} low-opacity gaussians"),
                ("info", "Cleaning isolated points (statistical + radius outlier removal)..."),
                ("info", f"Denoising complete. {self._num_gaussians} gaussians retained ({kept_pct}%)"),
            ]
        elif step_name == "export":
            return [
                ("info", "Exporting 3DGS format (SuperSplat compatible)..."),
                ("info", f"Writing {MOCK_PLY_NAME}..."),
                ("info", f"Exported {self._num_gaussians} gaussians"),
                ("info", "Export complete. Artifacts saved."),
            ]
        return []

    async def _run_step(self, step_name: str, step_index: int):
        step_start = time.time()

        # Mark step as running
        await self._update_step_db(step_name, "running", 0.0)
        await self._push_event("step_update", {
            "name": step_name,
            "status": "running",
            "progress": 0.0,
            "duration_sec": None
        })

        # Update job current_step
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE jobs SET current_step = ? WHERE job_id = ?",
                (step_name, self.job_id)
            )
            await db.commit()

        logs = self._get_step_logs(step_name)
        if not logs:
            logs = [("info", f"Running {step_name}...")]

        sub_duration = STEP_SECONDS / len(logs)

        for i, (level, line) in enumerate(logs):
            if self._cancelled:
                return False

            await self._add_log(level, line)

            if step_name == "train":
                progress = round((i + 1) / len(logs) * 100, 1)
                await self._update_step_db(step_name, "running", progress)
                await self._push_event("step_update", {
                    "name": step_name,
                    "status": "running",
                    "progress": progress,
                    "duration_sec": None
                })

            await asyncio.sleep(sub_duration)

        # Random failure disabled for demo stability
        if False:  # was: step_name == "train" and random.random() < 0.10
            error_msg = "Training failed: CUDA out of memory. Tried to allocate 2.0 GiB."
            await self._add_log("error", error_msg)
            step_total = time.time() - step_start
            await self._update_step_db(step_name, "failed", 100.0, round(step_total, 2))
            await self._push_event("step_update", {
                "name": step_name,
                "status": "failed",
                "progress": 100.0,
                "duration_sec": round(step_total, 2)
            })

            async with aiosqlite.connect(self.db_path) as db:
                now = datetime.now(timezone.utc).isoformat()
                await db.execute(
                    "UPDATE jobs SET status='failed', finished_at=?, error=? WHERE job_id=?",
                    (now, error_msg, self.job_id)
                )
                await db.commit()

            await self._push_event("error", {"message": error_msg})
            await self._push_event("status", {"status": "failed"})
            return False

        step_total = time.time() - step_start
        await self._update_step_db(step_name, "done", 100.0, round(step_total, 2))
        await self._push_event("step_update", {
            "name": step_name,
            "status": "done",
            "progress": 100.0,
            "duration_sec": round(step_total, 2)
        })

        return True

    async def _copy_mock_artifacts(self):
        """把预置的真实 3DGS 模型作为本任务的结果，供前端渲染与下载。"""
        result_dir = self.jobs_dir / self.job_id / "result"
        result_dir.mkdir(parents=True, exist_ok=True)

        src = self.mock_data_dir / MOCK_PLY_NAME
        dst = result_dir / MOCK_PLY_NAME
        if not src.exists():
            raise FileNotFoundError(f"预置模型不存在：{src}")

        if dst.exists():
            dst.unlink()
        # 复制一份而不是硬链接：任务产物必须冻结在跑完那一刻，
        # 否则日后替换 mock_data 里的模型，会把历史任务的结果一起改掉
        shutil.copyfile(src, dst)

    async def run(self):
        """Main mock pipeline execution."""
        self._training_start = time.time()

        import aiosqlite
        now = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE jobs SET status='running', started_at=? WHERE job_id=?",
                (now, self.job_id)
            )
            await db.commit()

        await self._push_event("status", {"status": "running"})
        await self._add_log("info", f"Pipeline started for job {self.job_id}")
        await self._add_log("info", f"Parameters: opacity_min={self.opacity_min}, iterations={self.iterations}, quality={self.quality}")

        for i, step_name in enumerate(STEP_NAMES):
            if self._cancelled:
                return

            ok = await self._run_step(step_name, i)
            if not ok:
                return

        # All steps done
        training_time = round(time.time() - self._training_start, 2)
        await self._add_log("info", f"Pipeline completed in {training_time}s")

        # Copy artifacts
        await self._copy_mock_artifacts()

        async with aiosqlite.connect(self.db_path) as db:
            now_finish = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "UPDATE jobs SET status='done', finished_at=?, current_step=NULL WHERE job_id=?",
                (now_finish, self.job_id)
            )
            await db.commit()

        await self._push_event("status", {"status": "done"})
