"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, AlertCircle, WifiOff } from "lucide-react";
import ProgressStepper from "@/components/ProgressStepper";
import LogPanel from "@/components/LogPanel";
import type { Step, LogEntry, Job } from "@/lib/api";
import { getJob } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function JobProgressPage() {
  const params = useParams() as { jobId: string };
  const router = useRouter();
  const jobId = params.jobId;

  const [steps, setSteps] = useState<Step[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [wsConnected, setWsConnected] = useState(false);
  const [jobNotFound, setJobNotFound] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Elapsed timer
  useEffect(() => {
    const timer = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatElapsed = (seconds: number): string => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h} 小时 ${m} 分钟`;
    if (m > 0) return `${m} 分钟 ${s} 秒`;
    return `${s} 秒`;
  };

  // Poll fallback
  const pollJob = useCallback(async () => {
    try {
      const job: Job = await getJob(jobId);
      setStatus(job.status);
      if (job.steps) setSteps(job.steps);
    } catch {
      // ignore poll errors
    }
  }, [jobId]);

  // WebSocket connection
  const connectWs = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(`${API_BASE.replace("http", "ws")}/ws/jobs/${jobId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        setInitialLoading(false);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          const payload = msg.data || msg;

          if (msg.type === "step_update" || payload.name) {
            const stepData = payload.step || payload;
            setSteps((prev) => {
              const idx = prev.findIndex((s) => s.name === stepData.name);
              if (idx >= 0) {
                const next = [...prev];
                next[idx] = { ...next[idx], ...stepData };
                return next;
              }
              return [...prev, stepData];
            });
          }

          if (msg.type === "log" || payload.line) {
            const logEntry: LogEntry = payload.log || payload;
            setLogs((prev) => [...prev, logEntry]);
          }

          if (msg.type === "status" && payload.status === "done") {
            setStatus("done");
            setTimeout(() => {
              router.push(`/result/${jobId}`);
            }, 2000);
          }

          if (msg.type === "status") {
            setStatus(payload.status);
          }

          if (msg.type === "error") {
            setStatus("failed");
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (status !== "done" && status !== "failed") {
          reconnectTimeoutRef.current = setTimeout(connectWs, 5000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setInitialLoading(false);
      reconnectTimeoutRef.current = setTimeout(connectWs, 5000);
    }
  }, [jobId, router, status]);

  useEffect(() => {
    connectWs();
    pollIntervalRef.current = setInterval(pollJob, 3000);

    return () => {
      wsRef.current?.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [connectWs, pollJob]);

  // Handle initial load timeout
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (initialLoading) {
        pollJob().then(() => setInitialLoading(false));
      }
    }, 3000);
    return () => clearTimeout(timeout);
  }, [initialLoading, pollJob]);

  // Loading state
  if (initialLoading && steps.length === 0) {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-cyan-400 animate-spin" />
          <p className="text-gray-500">正在连接任务...</p>
        </div>
      </div>
    );
  }

  // Job not found (we detect this from polling)
  if (jobNotFound) {
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

  // Error state
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
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-white tracking-tight">RT Pipeline</h1>
        <div className="flex items-center gap-4">
          {!wsConnected && (
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
          {/* Title */}
          <div>
            <h2 className="text-2xl font-bold text-white">任务进度</h2>
            <p className="mt-1 text-sm text-gray-400">
              已运行 {formatElapsed(elapsed)}
            </p>
          </div>

          {/* Done redirecting */}
          {status === "done" && (
            <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30 flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <p className="text-sm text-green-400">重建完成！即将跳转到结果页面...</p>
            </div>
          )}

          {/* ProgressStepper */}
          <div className="rounded-xl border border-gray-700/50 bg-[#0d1520] p-6">
            <ProgressStepper steps={steps} />
          </div>

          {/* LogPanel */}
          <LogPanel logs={logs} />
        </div>
      </main>
    </div>
  );
}
