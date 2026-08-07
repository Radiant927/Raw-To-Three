import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent / "pipeline.db"

async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'queued',
                current_step TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                error TEXT,
                opacity_min REAL NOT NULL DEFAULT 0.08,
                iterations INTEGER NOT NULL DEFAULT 30000,
                quality TEXT NOT NULL DEFAULT 'high',
                num_photos INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                progress REAL NOT NULL DEFAULT 0.0,
                duration_sec REAL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'info',
                line TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_steps_job_id ON steps(job_id);
            CREATE INDEX IF NOT EXISTS idx_logs_job_id ON logs(job_id);
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(job_id, timestamp);
        """)
        await db.commit()
    finally:
        await db.close()


# --- Job CRUD ---

async def create_job(db: aiosqlite.Connection, job_id: str, created_at: str,
                     opacity_min: float, iterations: int, quality: str, num_photos: int):
    await db.execute(
        "INSERT INTO jobs (job_id, status, created_at, opacity_min, iterations, quality, num_photos) "
        "VALUES (?, 'queued', ?, ?, ?, ?, ?)",
        (job_id, created_at, opacity_min, iterations, quality, num_photos)
    )
    await db.commit()


async def get_job(db: aiosqlite.Connection, job_id: str):
    cursor = await db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_jobs(db: aiosqlite.Connection):
    cursor = await db.execute("SELECT * FROM jobs ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def update_job_status(db: aiosqlite.Connection, job_id: str, status: str,
                            current_step: str = None, started_at: str = None,
                            finished_at: str = None, error: str = None):
    fields = ["status = ?"]
    params = [status]

    if current_step is not None:
        fields.append("current_step = ?")
        params.append(current_step)
    if started_at is not None:
        fields.append("started_at = ?")
        params.append(started_at)
    if finished_at is not None:
        fields.append("finished_at = ?")
        params.append(finished_at)
    if error is not None:
        fields.append("error = ?")
        params.append(error)

    params.append(job_id)
    await db.execute(
        f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ?",
        params
    )
    await db.commit()


async def get_running_job(db: aiosqlite.Connection):
    cursor = await db.execute(
        "SELECT * FROM jobs WHERE status IN ('queued', 'running') LIMIT 1"
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


# --- Step CRUD ---

async def create_steps(db: aiosqlite.Connection, job_id: str):
    step_names = ["upload", "colmap", "train", "denoise", "export"]
    for name in step_names:
        await db.execute(
            "INSERT INTO steps (job_id, name, status) VALUES (?, ?, 'pending')",
            (job_id, name)
        )
    await db.commit()


async def get_steps(db: aiosqlite.Connection, job_id: str):
    cursor = await db.execute(
        "SELECT name, status, progress, duration_sec FROM steps WHERE job_id = ? ORDER BY id",
        (job_id,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def update_step(db: aiosqlite.Connection, job_id: str, name: str,
                      status: str = None, progress: float = None, duration_sec: float = None):
    fields = []
    params = []

    if status is not None:
        fields.append("status = ?")
        params.append(status)
    if progress is not None:
        fields.append("progress = ?")
        params.append(progress)
    if duration_sec is not None:
        fields.append("duration_sec = ?")
        params.append(duration_sec)

    if not fields:
        return

    params.extend([job_id, name])
    await db.execute(
        f"UPDATE steps SET {', '.join(fields)} WHERE job_id = ? AND name = ?",
        params
    )
    await db.commit()


# --- Log CRUD ---

async def add_log(db: aiosqlite.Connection, job_id: str, timestamp: str, level: str, line: str):
    await db.execute(
        "INSERT INTO logs (job_id, timestamp, level, line) VALUES (?, ?, ?, ?)",
        (job_id, timestamp, level, line)
    )
    await db.commit()


async def get_logs_since(db: aiosqlite.Connection, job_id: str, since: str = None):
    if since:
        cursor = await db.execute(
            "SELECT timestamp, level, line FROM logs WHERE job_id = ? AND timestamp > ? ORDER BY id",
            (job_id, since)
        )
    else:
        cursor = await db.execute(
            "SELECT timestamp, level, line FROM logs WHERE job_id = ? ORDER BY id",
            (job_id,)
        )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]
