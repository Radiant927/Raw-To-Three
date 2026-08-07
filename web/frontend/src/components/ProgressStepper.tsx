"use client";

import { CheckCircle2, Loader2, Circle, XCircle } from "lucide-react";
import type { Step } from "@/lib/api";

interface ProgressStepperProps {
  steps: Step[];
}

const STEP_LABELS: Record<string, string> = {
  upload: "照片上传",
  colmap: "COLMAP SfM",
  train: "2DGS 训练",
  denoise: "去噪",
  export: "导出",
};

const stepOrder = ["upload", "colmap", "train", "denoise", "export"];

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}秒`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${Math.round(seconds % 60)}秒`;
  return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`;
}

export default function ProgressStepper({ steps }: ProgressStepperProps) {
  const stepsMap = new Map(steps.map((s) => [s.name, s]));

  return (
    <div className="flex flex-col gap-0">
      {stepOrder.map((name, index) => {
        const step = stepsMap.get(name);
        const status = step?.status ?? "pending";
        const progress = step?.progress ?? 0;
        const duration = step?.duration_sec;
        const label = STEP_LABELS[name] ?? name;
        const isLast = index === stepOrder.length - 1;

        return (
          <div key={name} className="relative flex gap-4">
            {/* Connector line */}
            {!isLast && (
              <div className="absolute left-[17px] top-9 w-0.5 h-full bg-gray-700" />
            )}

            {/* Status icon */}
            <div className="relative z-10 flex-shrink-0 mt-1.5">
              {status === "done" && (
                <CheckCircle2 className="w-9 h-9 text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.4)]" />
              )}
              {status === "running" && (
                <Loader2 className="w-9 h-9 text-cyan-400 animate-spin drop-shadow-[0_0_8px_rgba(6,182,212,0.4)]" />
              )}
              {status === "pending" && (
                <Circle className="w-9 h-9 text-gray-600" />
              )}
              {status === "failed" && (
                <XCircle className="w-9 h-9 text-red-400 drop-shadow-[0_0_8px_rgba(248,113,113,0.4)]" />
              )}
            </div>

            {/* Content */}
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
                  <span className="text-xs text-gray-500">{formatDuration(duration)}</span>
                )}
                {status === "running" && progress > 0 && (
                  <span className="text-xs text-cyan-400">{Math.round(progress)}%</span>
                )}
              </div>

              {/* Progress bar */}
              {status === "running" && (
                <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500 ease-out"
                    style={{
                      width: `${progress}%`,
                      background: "linear-gradient(90deg, #06b6d4, #22d3ee, #67e8f9)",
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
