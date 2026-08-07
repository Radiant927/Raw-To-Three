import asyncio
import math
import random
import time
import shutil
from datetime import datetime, timezone
from pathlib import Path

STEP_NAMES = ["upload", "colmap", "train", "denoise", "export"]
STEP_SECONDS = 10  # seconds per step (demo mode; set to 30 for production)


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
        self._num_gaussians = random.randint(80000, 250000)
        self._psnr = round(random.uniform(25.0, 38.0), 2)
        self._training_start = None

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
            iter_values = [1000, 2000, 3000, 5000, 7000, 10000, 15000, 20000, 25000, 30000]
            densify_1 = random.randint(50000, 300000)
            densify_2 = random.randint(100000, 500000)

            logs = [
                ("info", "Initializing 3D Gaussian splatting..."),
                ("info", f"Loading sparse point cloud with {self._num_gaussians} points"),
                ("info", f"Starting training with {self.iterations} iterations, quality={self.quality}"),
            ]
            for it, loss in zip(iter_values, loss_values):
                logs.append(("info", f"Training iter {it}/{self.iterations} loss={loss:.3f}"))
            logs.extend([
                ("info", f"Densification at iter 5000: {densify_1} gaussians"),
                ("info", f"Densification at iter 15000: {densify_2} gaussians"),
                ("info", "Pruning unnecessary gaussians..."),
                ("info", "Training complete. Final loss=0.029"),
            ])
            return logs
        elif step_name == "denoise":
            removed = random.randint(10000, 50000)
            return [
                ("info", "Loading trained point cloud..."),
                ("info", f"Applying opacity filter (min={round(self.opacity_min, 2)})..."),
                ("info", f"Removed {removed} low-opacity gaussians"),
                ("info", "Cleaning isolated points..."),
                ("info", f"Denoising complete. {self._num_gaussians} gaussians retained"),
            ]
        elif step_name == "export":
            return [
                ("info", "Converting to 3DGS format..."),
                ("info", "Writing PLY file..."),
                ("info", "Exporting GLB mesh..."),
                ("info", "Generating thumbnail..."),
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
        result_dir = self.jobs_dir / self.job_id / "result"
        result_dir.mkdir(parents=True, exist_ok=True)

        # Generate a proper INRIA V1 3DGS PLY (binary_little_endian)
        self._generate_3dgs_ply(result_dir)

        # Generate a valid minimal GLB (glTF 2.0 binary)
        self._generate_glb(result_dir)

    def _generate_glb(self, result_dir):
        """Generate a minimal but valid GLB file that Blender can open."""
        import struct

        # A simple triangle mesh: 3 vertices, 1 face
        vertices = [
            -1.0, -1.0, 0.0,
             1.0, -1.0, 0.0,
             0.0,  1.0, 0.0,
        ]
        indices = [0, 1, 2]

        vertex_bytes = struct.pack("<" + "f" * 9, *vertices)
        index_bytes = struct.pack("<" + "H" * 3, *indices)

        # Pad to 4-byte alignment
        while len(vertex_bytes) % 4 != 0:
            vertex_bytes += b"\x00"
        bin_data = vertex_bytes + index_bytes

        import json
        json_content = json.dumps({
            "asset": {"version": "2.0", "generator": "RT Pipeline Mock"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [{
                "primitives": [{
                    "attributes": {"POSITION": 0},
                    "indices": 1
                }]
            }],
            "accessors": [
                {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3",
                 "max": [1.0, 1.0, 0.0], "min": [-1.0, -1.0, 0.0]},
                {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"}
            ],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": len(vertex_bytes)},
                {"buffer": 0, "byteOffset": len(vertex_bytes), "byteLength": len(index_bytes)}
            ],
            "buffers": [{"byteLength": len(bin_data)}]
        })

        json_bytes = json_content.encode("utf-8")
        while len(json_bytes) % 4 != 0:
            json_bytes += b" "

        # GLB header + chunks
        total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
        glb = struct.pack("<I", 0x46546C67)  # magic "glTF"
        glb += struct.pack("<I", 2)           # version
        glb += struct.pack("<I", total_len)    # total length

        # JSON chunk
        glb += struct.pack("<I", len(json_bytes))
        glb += struct.pack("<I", 0x4E4F534A)  # "JSON"
        glb += json_bytes

        # BIN chunk
        glb += struct.pack("<I", len(bin_data))
        glb += struct.pack("<I", 0x004E4942)  # "BIN\0"
        glb += bin_data

        filepath = result_dir / "walls_mesh.glb"
        filepath.write_bytes(glb)

    def _generate_3dgs_ply(self, result_dir):
        """Generate a minimal but valid 3DGS PLY that gsplat.js can render."""
        import struct

        num_gaussians = 200
        # Arrange gaussians in a roughly spherical pattern
        points = []
        for i in range(num_gaussians):
            theta = (i * 2.399963) % (2 * 3.14159)
            phi = (i * 1.618034) % 3.14159
            r = 2.0 + (i % 3) * 0.5
            x = r * math.sin(phi) * math.cos(theta)
            y = r * math.sin(phi) * math.sin(theta)
            z = r * math.cos(phi) - 1.0

            nx, ny, nz = 0.0, 0.0, 0.0
            # Colors: mix of cyan, blue, purple
            f_dc = [
                0.2 + 0.3 * (i % 3 == 0),
                0.4 + 0.3 * (i % 3 == 1),
                0.6 + 0.3 * (i % 3 == 2),
            ]
            f_rest = [0.0] * 45
            opacity = 0.5
            scale = [-2.5, -2.5, -2.5]  # exp(-2.5) ≈ 0.08, visible size
            rot = [1.0, 0.0, 0.0, 0.0]

            points.append((x, y, z, nx, ny, nz, *f_dc, *f_rest, opacity, *scale, *rot))

        # Build header
        header = "ply\nformat binary_little_endian 1.0\n"
        header += f"element vertex {num_gaussians}\n"
        header += "property float x\nproperty float y\nproperty float z\n"
        header += "property float nx\nproperty float ny\nproperty float nz\n"
        header += "property float f_dc_0\nproperty float f_dc_1\nproperty float f_dc_2\n"
        for k in range(45):
            header += f"property float f_rest_{k}\n"
        header += "property float opacity\n"
        header += "property float scale_0\nproperty float scale_1\nproperty float scale_2\n"
        header += "property float rot_0\nproperty float rot_1\nproperty float rot_2\nproperty float rot_3\n"
        header += "end_header\n"

        # Write PLY files
        for filename in ["denoised_3dgs.ply", "denoised.ply"]:
            filepath = result_dir / filename
            with open(filepath, "wb") as f:
                f.write(header.encode("ascii"))
                for pt in points:
                    f.write(struct.pack("<" + "f" * 62, *pt))

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
