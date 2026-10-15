"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  CircleX,
  Loader2,
  WifiOff,
} from "lucide-react";
import { getJob, wsUrl, type LogEntry, type Step } from "@/lib/api";

const STEP_LABELS: Record<string, string> = {
  upload: "照片上传",
  colmap: "COLMAP SfM",
  train: "3DGS 训练",
  denoise: "去噪",
  export: "导出",
};

const STEP_ORDER = ["upload", "colmap", "train", "denoise", "export"];

function formatDuration(sec: number): string {
  if (sec < 60) return `${Math.round(sec)}秒`;
  if (sec < 3600) return `${Math.floor(sec / 60)}分${Math.round(sec % 60)}秒`;
  return `${Math.floor(sec / 3600)}时${Math.floor((sec % 3600) / 60)}分`;
}

function StepsPanel({ steps }: { steps: Step[] }) {
  const map = new Map(steps.map((s) => [s.name, s]));

  return (
    <div className="flex flex-col gap-0">
      {STEP_ORDER.map((name, idx) => {
        const step = map.get(name);
        const status = step?.status ?? "pending";
        const progress = step?.progress ?? 0;
        const duration = step?.duration_sec;
        const label = STEP_LABELS[name] ?? name;
        const isLast = idx === STEP_ORDER.length - 1;

        return (
          <div key={name} className="relative flex gap-4">
            {!isLast && (
              <div className="absolute left-[17px] top-9 w-0.5 h-full bg-gray-700" />
            )}
            <div className="relative z-10 flex-shrink-0 mt-1.5">
              {status === "done" && (
                <CheckCircle2 className="w-9 h-9 text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.4)]" />
              )}
              {status === "running" && (
                <Loader2 className="w-9 h-9 text-cyan-400 animate-spin drop-shadow-[0_0_8px_rgba(6,182,212,0.4)]" />
              )}
              {status === "pending" && <Circle className="w-9 h-9 text-gray-600" />}
              {status === "failed" && (
                <CircleX className="w-9 h-9 text-red-400 drop-shadow-[0_0_8px_rgba(248,113,113,0.4)]" />
              )}
            </div>

            <div className={`flex-1 min-w-0 pb-8 ${isLast ? "pb-0" : ""}`}>
              <div className="flex items-center justify-between mb-1.5">
                <span
                  className={`font-medium text-sm transition-colors duration-300 ${
                    status === "running"
                      ? "text-cyan-400"
                      : status === "done"
                        ? "text-green-400"
                        : status === "failed"
                          ? "text-red-400"
                          : "text-gray-500"
                  }`}
                >
                  {label}
                </span>
                {status === "done" && duration != null && (
                  <span className="text-xs text-gray-500">
                    {formatDuration(duration)}
                  </span>
                )}
                {status === "running" && progress > 0 && (
                  <span className="text-xs text-cyan-400">
                    {Math.round(progress)}%
                  </span>
                )}
              </div>
              {status === "running" && (
                <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500 ease-out"
                    style={{
                      width: `${progress}%`,
                      background:
                        "linear-gradient(90deg, #06b6d4, #22d3ee, #67e8f9)",
                    }}
                  />
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

const LOG_DOT: Record<string, string> = {
  info: "bg-green-500 shadow-[0_0_4px_rgba(74,222,128,0.6)]",
  warn: "bg-yellow-400 shadow-[0_0_4px_rgba(250,204,21,0.6)]",
  error: "bg-red-500 shadow-[0_0_4px_rgba(248,113,113,0.6)]",
};

function LogPanel({ logs }: { logs: LogEntry[] }) {
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (boxRef.current) {
      boxRef.current.scrollTop = boxRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="rounded-xl border border-gray-700/50 overflow-hidden bg-[#0a0d14]">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-700/50 bg-[#0d1117]">
        <span className="text-sm font-medium text-gray-300 font-mono">实时日志</span>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
          </span>
          <span className="text-xs text-gray-500 font-mono">LIVE</span>
        </div>
      </div>

      <div
        ref={boxRef}
        className="h-64 overflow-y-auto font-mono text-sm p-4"
        style={{ scrollbarWidth: "thin", scrollbarColor: "#1f2937 #0a0d14" }}
      >
        {logs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-600">
            等待日志输出...
          </div>
        ) : (
          <div className="flex flex-col gap-0.5">
            {logs.map((entry, idx) => {
              const time = entry.timestamp
                ? new Date(entry.timestamp).toLocaleTimeString("zh-CN", {
                    hour12: false,
                  })
                : "";
              return (
                <div key={idx} className="flex items-start gap-2 leading-relaxed">
                  {time && (
                    <span className="text-gray-600 flex-shrink-0 select-none">
                      {time}
                    </span>
                  )}
                  <span className="flex-shrink-0 mt-2">
                    <span
                      className={`inline-block w-1.5 h-1.5 rounded-full ${
                        LOG_DOT[entry.level] ?? LOG_DOT.info
                      }`}
                    />
                  </span>
                  <span className="text-green-400/90 break-all">{entry.line}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function formatElapsed(total: number): string {
  const hours = Math.floor(total / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours > 0) return `${hours} 小时 ${mins} 分钟`;
  if (mins > 0) return `${mins} 分钟 ${secs} 秒`;
  return `${secs} 秒`;
}

export default function JobProgressPage() {
  const params = useParams<{ jobId: string }>();
  const router = useRouter();
  const jobId = params.jobId;

  const [steps, setSteps] = useState<Step[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [connected, setConnected] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [loading, setLoading] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const statusRef = useRef<string | null>(null);
  statusRef.current = status;

  const pollJob = useCallback(async () => {
    try {
      const job = await getJob(jobId);
      setStatus(job.status);
      if (job.steps) setSteps(job.steps);
    } catch (e) {
      if (e instanceof Error && e.message.includes("404")) {
        setNotFound(true);
      }
    }
  }, [jobId]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl(`/ws/jobs/${jobId}`));
      wsRef.current = ws;
    } catch {
      reconnectTimer.current = setTimeout(connect, 5000);
      return;
    }

    ws.onopen = () => {
      setConnected(true);
      setLoading(false);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const data = msg.data ?? msg;

        if (msg.type === "step_update" || data.name) {
          const payload = data.step ?? data;
          setSteps((prev) => {
            const idx = prev.findIndex((s) => s.name === payload.name);
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = { ...next[idx], ...payload };
              return next;
            }
            return [...prev, payload];
          });
        }

        if (msg.type === "log" || data.line) {
          const payload = data.log ?? data;
          setLogs((prev) => [...prev, payload]);
        }

        if (msg.type === "status") {
          setStatus(data.status);
          if (data.status === "done") {
            setTimeout(() => router.push(`/result/${jobId}`), 2000);
          }
        }

        if (msg.type === "error") {
          setStatus("failed");
        }
      } catch {
        // ignore malformed frame
      }
    };

    ws.onclose = () => {
      setConnected(false);
      const current = statusRef.current;
      if (current !== "done" && current !== "failed") {
        reconnectTimer.current = setTimeout(connect, 5000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [jobId, router]);

  useEffect(() => {
    connect();
    pollTimer.current = setInterval(pollJob, 3000);
    return () => {
      wsRef.current?.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, [connect, pollJob]);

  useEffect(() => {
    const ticker = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(ticker);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (loading) {
        pollJob().then(() => setLoading(false));
      }
    }, 3000);
    return () => clearTimeout(timer);
  }, [loading, pollJob]);

  if (loading && steps.length === 0) {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-cyan-400 animate-spin" />
          <p className="text-gray-500">正在连接任务...</p>
        </div>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <AlertCircle className="w-12 h-12 text-red-400" />
          <h2 className="text-xl font-semibold text-white">任务不存在</h2>
          <p className="text-gray-500">请检查任务 ID 是否正确</p>
        </div>
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <AlertCircle className="w-12 h-12 text-red-400" />
          <h2 className="text-xl font-semibold text-white">任务处理失败</h2>
          <p className="text-gray-500">请查看日志了解详情</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0e17] flex flex-col">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-white tracking-tight">RT Pipeline</h1>
        <div className="flex items-center gap-4">
          {!connected && (
            <div className="flex items-center gap-1.5 text-yellow-500 text-xs">
              <WifiOff className="w-3.5 h-3.5" />
              <span>重连中...</span>
            </div>
          )}
          <span className="text-xs font-mono text-gray-600 bg-gray-800/50 px-2.5 py-1 rounded-lg border border-gray-700/50">
            {jobId}
          </span>
        </div>
      </header>

      <main className="flex-1 flex items-start justify-center px-4 py-12">
        <div className="w-full max-w-2xl flex flex-col gap-8">
          <div>
            <h2 className="text-2xl font-bold text-white">任务进度</h2>
            <p className="mt-1 text-sm text-gray-400">
              已运行 {formatElapsed(elapsed)}
            </p>
          </div>

          {status === "done" && (
            <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30 flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <p className="text-sm text-green-400">
                重建完成！即将跳转到结果页面...
              </p>
            </div>
          )}

          <div className="rounded-xl border border-gray-700/50 bg-[#0d1520] p-6">
            <StepsPanel steps={steps} />
          </div>

          <LogPanel logs={logs} />
        </div>
      </main>
    </div>
  );
}
