"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  Zap,
} from "lucide-react";
import SplatViewer from "@/components/SplatViewer";
import { API_BASE, getResult, type JobResult } from "@/lib/api";

const ARTIFACT_USAGE: Record<string, string> = {
  "denoised_3dgs.ply": "用于 SuperSplat",
  "walls_mesh.glb": "用于 Blender",
  "denoised.ply": "原始 3DGS",
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function formatDuration(sec: number): string {
  if (sec < 60) return `${Math.round(sec)}秒`;
  if (sec < 3600) return `${Math.floor(sec / 60)}分${Math.round(sec % 60)}秒`;
  return `${Math.floor(sec / 3600)}时${Math.floor((sec % 3600) / 60)}分`;
}

export default function ResultPage() {
  const params = useParams<{ jobId: string }>();
  const router = useRouter();
  const jobId = params.jobId;

  const [result, setResult] = useState<JobResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getResult(jobId);
        if (!cancelled) setResult(data);
      } catch (e) {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : "结果加载失败");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Zap className="w-10 h-10 text-cyan-400 animate-pulse" />
          <p className="text-gray-500">加载结果中...</p>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center px-6">
          <AlertCircle className="w-12 h-12 text-red-400" />
          <h2 className="text-xl font-semibold text-white">结果加载失败</h2>
          <p className="text-gray-500">{loadError}</p>
          <button
            onClick={() => router.push("/demo")}
            className="mt-2 px-6 py-2.5 rounded-xl bg-cyan-500 text-black font-medium hover:bg-cyan-400 transition-colors"
          >
            返回首页
          </button>
        </div>
      </div>
    );
  }

  if (!result || result.status !== "done") {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center px-6">
          <Clock className="w-12 h-12 text-yellow-400" />
          <h2 className="text-xl font-semibold text-white">任务尚未完成</h2>
          <p className="text-gray-500">请稍后再试</p>
          <Link
            href={`/demo/${jobId}`}
            className="mt-2 px-6 py-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-medium hover:bg-cyan-500/20 transition-colors"
          >
            查看进度
          </Link>
        </div>
      </div>
    );
  }

  const plyArtifact = result.artifacts.find((a) =>
    a.filename.endsWith(".ply")
  );
  const plyUrl = plyArtifact ? `${API_BASE}${plyArtifact.url}` : "";
  const stats = result.stats;

  return (
    <div className="min-h-screen bg-[#0a0e17] flex flex-col">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-white tracking-tight">RT Pipeline</h1>
        <div className="flex items-center gap-3">
          <Link
            href="/demo"
            className="text-xs text-gray-400 hover:text-cyan-400 transition-colors"
          >
            新建任务
          </Link>
          <span className="text-xs font-mono text-gray-600 bg-gray-800/50 px-2.5 py-1 rounded-lg border border-gray-700/50">
            {jobId}
          </span>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center px-4 py-10 pb-20">
        <div className="w-full max-w-5xl flex flex-col gap-8">
          <div className="flex items-center gap-3 p-5 rounded-xl bg-green-500/10 border border-green-500/30">
            <CheckCircle2 className="w-6 h-6 text-green-400 flex-shrink-0" />
            <div>
              <h2 className="text-lg font-semibold text-white">重建完成!</h2>
              <p className="text-sm text-gray-400">
                你的 3D 高斯模型已生成，可在线预览或下载
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-4">
            {stats.num_gaussians != null && (
              <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#0d1520] border border-gray-700/50">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span className="text-sm text-gray-300">
                  <span className="font-mono text-cyan-400">
                    {stats.num_gaussians.toLocaleString()}
                  </span>{" "}
                  高斯点
                </span>
              </div>
            )}

            {stats.num_photos != null && (
              <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#0d1520] border border-gray-700/50">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span className="text-sm text-gray-300">
                  <span className="font-mono text-cyan-400">{stats.num_photos}</span>{" "}
                  张照片
                </span>
              </div>
            )}

            {stats.training_time_sec != null && (
              <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#0d1520] border border-gray-700/50">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span className="text-sm text-gray-300">
                  训练耗时{" "}
                  <span className="font-mono text-cyan-400">
                    {formatDuration(stats.training_time_sec)}
                  </span>
                </span>
              </div>
            )}
          </div>

          <section>
            <h3 className="text-lg font-semibold text-white mb-4">3D 预览</h3>
            <SplatViewer plyUrl={plyUrl} />
            <p className="text-xs text-gray-600 mt-2">
              鼠标左键旋转 · 右键平移 · 滚轮缩放
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold text-white mb-4">下载结果</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {result.artifacts.map((artifact) => (
                <div
                  key={artifact.filename}
                  className="flex flex-col gap-3 p-5 rounded-xl bg-[#0d1520] border border-gray-700/50 hover:border-cyan-500/30 transition-colors group"
                >
                  <div className="flex-1">
                    <p className="font-mono text-sm text-white break-all mb-1">
                      {artifact.filename}
                    </p>
                    <p className="text-xs text-gray-500 mb-0.5">
                      {ARTIFACT_USAGE[artifact.filename] ?? artifact.filename}
                    </p>
                    <p className="text-xs text-gray-600">
                      {formatFileSize(artifact.size_bytes)}
                    </p>
                  </div>
                  <a
                    href={`${API_BASE}${artifact.url}`}
                    download
                    className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-sm font-medium hover:bg-cyan-500/20 hover:border-cyan-400/50 transition-all group-hover:shadow-[0_0_15px_rgba(6,182,212,0.1)]"
                  >
                    <Download className="w-4 h-4" />
                    下载
                  </a>
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
