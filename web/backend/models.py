from pydantic import BaseModel, Field
from typing import Optional, List


# --- Request Models ---

class CreateJobRequest(BaseModel):
    opacity_min: float = Field(default=0.08, ge=0.0, le=1.0)
    iterations: int = Field(default=30000, ge=1000, le=100000)
    quality: str = Field(default="high")


class LogQuery(BaseModel):
    since: Optional[str] = None


# --- Response Models ---

class StepResponse(BaseModel):
    name: str
    status: str
    progress: float
    duration_sec: Optional[float] = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    current_step: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    opacity_min: float
    iterations: int
    quality: str
    num_photos: int
    steps: List[StepResponse] = []


class LogEntry(BaseModel):
    timestamp: str
    level: str
    line: str


class LogsResponse(BaseModel):
    job_id: str
    entries: List[LogEntry]
    cursor: str


class ArtifactItem(BaseModel):
    filename: str
    size_bytes: int
    url: str


class ResultStats(BaseModel):
    num_gaussians: Optional[int] = None
    psnr: Optional[float] = None
    training_time_sec: Optional[float] = None
    total_points: Optional[int] = None
    num_photos: Optional[int] = None


class ResultResponse(BaseModel):
    job_id: str
    status: str
    artifacts: List[ArtifactItem]
    stats: ResultStats


class GalleryItem(BaseModel):
    id: str
    title: str
    thumbnail_url: str
    ply_url: str
    num_gaussians: int
    num_photos: int


class GalleryResponse(BaseModel):
    items: List[GalleryItem]


class ErrorResponse(BaseModel):
    detail: str


class CreateJobResponse(BaseModel):
    job_id: str
    message: str


# --- WebSocket Event Models ---

class WsEvent(BaseModel):
    type: str  # step_update | log | status | error
    data: dict
