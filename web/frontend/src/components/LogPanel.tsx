"use client";

import { useEffect, useRef } from "react";
import type { LogEntry } from "@/lib/api";

interface LogPanelProps {
  logs: LogEntry[];
}

const LEVEL_DOT: Record<LogEntry["level"], string> = {
  info: "bg-green-500 shadow-[0_0_4px_rgba(74,222,128,0.6)]",
  warn: "bg-yellow-400 shadow-[0_0_4px_rgba(250,204,21,0.6)]",
  error: "bg-red-500 shadow-[0_0_4px_rgba(248,113,113,0.6)]",
};

export default function LogPanel({ logs }: LogPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="rounded-xl border border-gray-700/50 overflow-hidden bg-[#0a0d14]">
      {/* Header */}
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

      {/* Log output */}
      <div
        ref={scrollRef}
        className="h-64 overflow-y-auto font-mono text-sm p-4"
        style={{
          scrollbarWidth: "thin",
          scrollbarColor: "#1f2937 #0a0d14",
        }}
      >
        {logs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-600">
            等待日志输出...
          </div>
        ) : (
          <div className="flex flex-col gap-0.5">
            {logs.map((log, i) => {
              const time = log.timestamp
                ? new Date(log.timestamp).toLocaleTimeString("zh-CN", { hour12: false })
                : "";
              return (
                <div key={i} className="flex items-start gap-2 leading-relaxed">
                  {time && (
                    <span className="text-gray-600 flex-shrink-0 select-none">{time}</span>
                  )}
                  <span className="flex-shrink-0 mt-2">
                    <span className={`inline-block w-1.5 h-1.5 rounded-full ${LEVEL_DOT[log.level] ?? LEVEL_DOT.info}`} />
                  </span>
                  <span className="text-green-400/90 break-all">{log.line}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
