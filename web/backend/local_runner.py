import asyncio
import os
import re
import time
import shutil
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

STEP_NAMES = ["upload", "colmap", "train", "denoise", "export"]
FINAL_PLY_NAME = "denoised_3dgs.ply"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[?]?[a-zA-Z]")
STEP_MARKER_RE = re.compile(r"\[(\d(?:\.5)?)/5\]")
# nerfstudio rich 进度表数据行形如 "7570 (25.23%)   24.7 ms   9 m  ..."
PCT_ROW_RE = re.compile(r"^\s*(\d+)\s+\((\d+(?:\.\d+)?)%\)")
ERROR_RE = re.compile(r"Traceback|Error|ERROR|FAILED|CUDA out of memory")


class LocalRunner:
    """在本机（huolong）直接跑 huolong_run/run.sh，替代 MockRunner。"""

    def __init__(self, job_id: str, num_photos: int, opacity_min: float,
                 iterations: int, quality: str, jobs_dir: Path,
                 pipeline_dir: Path, event_queue: asyncio.Queue,
                 db_path: str, gpu_id: int, matcher: str = "sequential"):
        self.job_id = job_id
        self.num_photos = num_photos
        self.opacity_min = opacity_min
        self.iterations = iterations
        self.quality = quality
        self.jobs_dir = jobs_dir
        self.pipeline_dir = pipeline_dir
        self.event_queue = event_queue
        self.db_path = db_path
        self.gpu_id = gpu_id
        self.matcher = matcher

        self.photos_dir = jobs_dir / job_id / "photos"
        self.work_dir = jobs_dir / job_id / "work"
        self.result_dir = jobs_dir / job_id / "result"
        self._recent = deque(maxlen=30)
        self._proc = None
        self._train_poller = None
        self._train_log_offset = 0
        self._last_train_pct = -1
        self._last_logged_ten = 0
        self._train_finished = False
        self._step_start: dict = {}

    # ---------- DB / WS helpers ----------

    async def _push_event(self, event_type: str, data: dict):
        await self.event_queue.put({"type": event_type, "data": data})

    async def _add_log(self, level: str, line: str):
        line = ANSI_RE.sub("", line).strip()
        if not line:
            return
        if len(line) > 1000:
            line = line[:1000] + " …[truncated]"
        ts = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO logs (job_id, timestamp, level, line) VALUES (?, ?, ?, ?)",
                (self.job_id, ts, level, line)
            )
            await db.commit()
        await self._push_event("log", {"timestamp": ts, "level": level, "line": line})

    async def _set_step(self, name: str, status: str, progress: float):
        duration = None
        if status in ("done", "failed") and name in self._step_start:
            duration = round(time.time() - self._step_start[name], 2)
        async with aiosqlite.connect(self.db_path) as db:
            if duration is not None:
                await db.execute(
                    "UPDATE steps SET status=?, progress=?, duration_sec=? "
                    "WHERE job_id=? AND name=?",
                    (status, progress, duration, self.job_id, name)
                )
            else:
                await db.execute(
                    "UPDATE steps SET status=?, progress=? WHERE job_id=? AND name=?",
                    (status, progress, self.job_id, name)
                )
            await db.commit()
        await self._push_event("step_update", {
            "name": name, "status": status, "progress": progress,
            "duration_sec": duration
        })

    async def _set_job(self, status: str, **fields):
        async with aiosqlite.connect(self.db_path) as db:
            if fields:
                cols = ", ".join(f"{k}=?" for k in fields)
                await db.execute(
                    f"UPDATE jobs SET status=?, {cols} WHERE job_id=?",
                    [status, *fields.values(), self.job_id]
                )
            else:
                await db.execute(
                    "UPDATE jobs SET status=? WHERE job_id=?", (status, self.job_id)
                )
            await db.commit()

    async def _set_current_step(self, name: Optional[str]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE jobs SET current_step=? WHERE job_id=?", (name, self.job_id)
            )
            await db.commit()

    # ---------- step transitions ----------

    async def _step_begin(self, name: str):
        self._step_start[name] = time.time()
        await self._set_current_step(name)
        await self._set_step(name, "running", 0.0)

    async def _step_finish(self, name: str):
        await self._set_step(name, "done", 100.0)

    async def _fail(self, message: str):
        for name in STEP_NAMES:
            async with aiosqlite.connect(self.db_path) as db:
                cur = await db.execute(
                    "SELECT status FROM steps WHERE job_id=? AND name=?",
                    (self.job_id, name)
                )
                row = await cur.fetchone()
            if row and row[0] == "running":
                await self._set_step(name, "failed", 0.0)
        now = datetime.now(timezone.utc).isoformat()
        await self._set_job("failed", finished_at=now, error=message)
        await self._push_event("error", {"message": message})
        await self._push_event("status", {"status": "failed"})

    # ---------- training progress ----------

    async def _poll_train_log(self):
        log_path = self.work_dir / "train.log"
        while True:
            await asyncio.sleep(4)
            if self._train_finished:
                break
            if not log_path.exists():
                continue
            try:
                with open(log_path, "rb") as f:
                    f.seek(self._train_log_offset)
                    chunk = f.read()
                    self._train_log_offset = f.tell()
            except OSError:
                continue
            text = ANSI_RE.sub("", chunk.decode("utf-8", errors="ignore"))
            last_cur, last_pct_val = None, None
            for ln in text.splitlines():
                m = PCT_ROW_RE.match(ln)
                if m:
                    last_cur, last_pct_val = int(m.group(1)), float(m.group(2))
            if last_pct_val is not None and not self._train_finished:
                pct = round(min(last_pct_val, 100.0), 1)
                if pct > self._last_train_pct:
                    self._last_train_pct = pct
                    await self._set_step("train", "running", pct)
                    ten = int(pct) // 10
                    if 1 <= ten <= 9 and ten > self._last_logged_ten:
                        self._last_logged_ten = ten
                        await self._add_log(
                            "info",
                            f"训练进度 {ten * 10}%（iter {last_cur}/{self.iterations}）"
                        )

    async def _handle_output_line(self, raw: bytes):
        line = raw.decode("utf-8", errors="ignore")
        clean = ANSI_RE.sub("", line).strip()
        if not clean:
            return
        # tqdm 进度条会在一行里塞几十上百个 \r 刷新，可能极长；截断只留末尾状态
        truncated = len(clean) > 4000
        if truncated:
            clean = clean[-4000:]
        self._recent.append(clean)

        marker = None if truncated else STEP_MARKER_RE.search(clean)
        if marker:
            tag = marker.group(1)
            if tag in ("1", "1.5"):
                pass  # colmap 进行中
            elif tag == "2":
                await self._step_finish("colmap")
                await self._step_begin("train")
            elif tag == "3":
                self._train_finished = True
                await self._step_finish("train")
                await self._step_begin("denoise")
            elif tag == "4":
                pass  # denoise 进行中
            elif tag == "5":
                await self._step_finish("denoise")
                await self._step_begin("export")

        level = "error" if ERROR_RE.search(clean) else "info"
        # 标记行本身不重复入库（避免和状态事件重复），其余输出照录
        if not marker:
            await self._add_log(level, clean)

    # ---------- main ----------

    async def run(self):
        now = datetime.now(timezone.utc).isoformat()
        await self._set_job("running", started_at=now)
        await self._push_event("status", {"status": "running"})
        await self._add_log("info", f"任务 {self.job_id} 开始，分配到 GPU{self.gpu_id}")
        await self._add_log(
            "info",
            f"参数: {self.num_photos} 张照片, iterations={self.iterations}, "
            f"quality={self.quality}, matcher={self.matcher}"
        )

        # 照片在 HTTP 上传时已落盘，upload 直接完成
        await self._step_finish("upload")
        await self._step_begin("colmap")

        self.work_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(self.gpu_id)

        self._proc = await asyncio.create_subprocess_exec(
            "bash", str(self.pipeline_dir / "run.sh"),
            "--photos", str(self.photos_dir),
            "--output", str(self.work_dir),
            "--matcher", self.matcher,
            "--iterations", str(self.iterations),
            "--quality", self.quality,
            "--no_undistort",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
            cwd=str(self.pipeline_dir),
        )
        self._train_poller = asyncio.create_task(self._poll_train_log())

        # 手动按字节读、按 \n 切分。
        # SuperGlue/COLMAP 的 tqdm 进度条用 \r 原地刷新、长时间不换行，
        # asyncio 默认的 readline() 在单行超过 64KB 时会抛 LimitOverrunError，
        # 直接把整个 run() 干掉（现象：训练/产物都跑完了，但任务永远卡在 running、
        # 也没有 result/ 目录）。逐块 read() 不受单行长度限制，可彻底避免。
        buf = b""
        while True:
            chunk = await self._proc.stdout.read(65536)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                await self._handle_output_line(line)
        if buf:
            await self._handle_output_line(buf)

        rc = await self._proc.wait()
        self._train_poller.cancel()

        final_ply = self.work_dir / FINAL_PLY_NAME
        if rc != 0 or not final_ply.exists():
            tail = " | ".join(list(self._recent)[-5:])
            await self._add_log("error", f"pipeline 退出码 {rc}")
            await self._fail(f"Pipeline 失败（退出码 {rc}）。最后输出：{tail}")
            return

        self.result_dir.mkdir(parents=True, exist_ok=True)
        dst = self.result_dir / FINAL_PLY_NAME
        if dst.exists():
            dst.unlink()
        shutil.copyfile(final_ply, dst)
        await self._add_log("info", f"已导出最终模型 {FINAL_PLY_NAME}")

        await self._step_finish("export")
        finished = datetime.now(timezone.utc).isoformat()
        await self._set_job("done", finished_at=finished, current_step=None)
        await self._push_event("status", {"status": "done"})
