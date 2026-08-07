const BASE_URL = "http://localhost:8000";

// ── Type definitions (matches backend models.py) ──

export interface Step {
  name: string;
  status: "pending" | "running" | "done" | "failed";
  progress: number;
  duration_sec: number | null;
}

export interface Job {
  job_id: string;
  status: "queued" | "running" | "done" | "failed";
  current_step: string | null;
  steps: Step[];
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  opacity_min: number;
  iterations: number;
  quality: string;
  num_photos: number;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  line: string;
}

export interface Artifact {
  filename: string;
  size_bytes: number;
  url: string;
}

export interface ResultStats {
  num_gaussians: number | null;
  psnr: number | null;
  training_time_sec: number | null;
  total_points: number | null;
  num_photos: number | null;
}

export interface JobResult {
  job_id: string;
  status: string;
  artifacts: Artifact[];
  stats: ResultStats;
}

export interface GalleryItem {
  id: string;
  title: string;
  thumbnail_url: string;
  ply_url: string;
  num_gaussians: number;
  num_photos: number;
}

export interface WsMessage {
  type: string;
  data: Record<string, unknown>;
}

// ── API client functions ──

export async function createJob(
  formData: FormData
): Promise<{
  job_id: string;
  message: string;
}> {
  const res = await fetch(`${BASE_URL}/api/jobs`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    let msg = "创建任务失败";
    if (typeof err.detail === "string") {
      msg = err.detail;
    } else if (Array.isArray(err.detail)) {
      msg = err.detail.map((e: { msg?: string }) => e.msg || JSON.stringify(e)).join("; ");
    } else if (err.detail) {
      msg = JSON.stringify(err.detail);
    }
    throw new Error(msg);
  }
  return res.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE_URL}/api/jobs/${encodeURIComponent(jobId)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "获取任务失败");
  }
  return res.json();
}

export async function getJobLogs(
  jobId: string,
  since?: string
): Promise<{ entries: LogEntry[]; cursor: string }> {
  const params = new URLSearchParams();
  if (since) params.set("since", since);
  const url = `${BASE_URL}/api/jobs/${encodeURIComponent(jobId)}/logs?${params.toString()}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "获取日志失败");
  }
  return res.json();
}

export async function getJobResult(jobId: string): Promise<JobResult> {
  const res = await fetch(
    `${BASE_URL}/api/jobs/${encodeURIComponent(jobId)}/result`
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "获取结果失败");
  }
  return res.json();
}

export async function getGallery(): Promise<{ items: GalleryItem[] }> {
  const res = await fetch(`${BASE_URL}/api/gallery`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "获取画廊失败");
  }
  return res.json();
}

export function getDownloadUrl(jobId: string, filename: string): string {
  return `${BASE_URL}/files/${encodeURIComponent(jobId)}/${encodeURIComponent(filename)}`;
}

export function getPlyUrl(jobId: string): string {
  return `${BASE_URL}/files/${encodeURIComponent(jobId)}/denoised_3dgs.ply`;
}
