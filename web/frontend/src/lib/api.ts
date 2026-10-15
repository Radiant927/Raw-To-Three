export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export function wsUrl(path: string): string {
  return `${API_BASE.replace(/^http/, "ws")}${path}`;
}

export interface Step {
  name: string;
  status: string;
  progress: number;
  duration_sec?: number | null;
}

export interface Job {
  job_id: string;
  status: string;
  current_step?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
  opacity_min: number;
  iterations: number;
  quality: string;
  num_photos: number;
  steps: Step[];
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
  num_gaussians?: number | null;
  psnr?: number | null;
  training_time_sec?: number | null;
  total_points?: number | null;
  num_photos?: number | null;
}

export interface JobResult {
  job_id: string;
  status: string;
  artifacts: Artifact[];
  stats: ResultStats;
}

export interface CreateJobParams {
  opacityMin: number;
  iterations: number;
  quality: string;
  photos: File[];
}

export async function createJob(params: CreateJobParams): Promise<string> {
  const form = new FormData();
  form.append("opacity_min", String(params.opacityMin));
  form.append("iterations", String(params.iterations));
  form.append("quality", params.quality);
  for (const photo of params.photos) {
    form.append("photos", photo);
  }

  const res = await fetch(apiUrl("/api/jobs"), {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    let detail = `创建任务失败（${res.status}）`;
    try {
      const data = await res.json();
      if (data.detail) detail = data.detail;
    } catch {
      // ignore non-JSON error body
    }
    throw new Error(detail);
  }

  const data = await res.json();
  return data.job_id as string;
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(apiUrl(`/api/jobs/${jobId}`), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Job not found (${res.status})`);
  }
  return res.json();
}

export async function getResult(jobId: string): Promise<JobResult> {
  const res = await fetch(apiUrl(`/api/jobs/${jobId}/result`), {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Result not found (${res.status})`);
  }
  return res.json();
}
