"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Download, ExternalLink, Loader2, AlertCircle, CheckCircle2, Zap } from "lucide-react";
import GSplatViewer from "@/components/GSplatViewer";
import { getJobResult } from "@/lib/api";
import type { JobResult, Artifact } from "@/lib/api";

const API_BASE = "http://localhost:8000";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function findPlyArtifact(artifacts: Artifact[]): Artifact | undefined {
  return artifacts.find((a) => a.filename.endsWith(".ply"));
}

const ARTIFACT_LABELS: Record<string, string> = {
  "denoised_3dgs.ply": "用于 SuperSplat",
  "walls_mesh.glb": "用于 Blender",
  "denoised.ply": "原始 2DGS",
};

export default function ResultPage() {
  const params = useParams() as { jobId: string };
  const router = useRouter();
  const jobId = params.jobId;

  const [result, setResult] = useState<JobResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchResult() {
      try {
        const data = await getJobResult(jobId);
        if (cancelled) return;
        setResult(data);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "结果加载失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchResult();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  // Loading
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-cyan-400 animate-spin" />
          <p className="text-gray-500">加载结果中...</p>
        </div>
      </div>
    );
  }

  // Error
  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center px-6">
          <AlertCircle className="w-12 h-12 text-red-400" />
          <h2 className="text-xl font-semibold text-white">结果加载失败</h2>
          <p className="text-gray-500">{error}</p>
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

  // No result yet
  if (!result) {
    return (
      <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center px-6">
          <AlertCircle className="w-12 h-12 text-yellow-400" />
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

  const plyArtifact = result ? findPlyArtifact(result.artifacts) : undefined;

  return (
    <div className="min-h-screen bg-[#0a0e17] flex flex-col">
      {/* Header */}
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
          {/* Success banner */}
          <div className="flex items-center gap-3 p-5 rounded-xl bg-green-500/10 border border-green-500/30">
            <CheckCircle2 className="w-6 h-6 text-green-400 flex-shrink-0" />
            <div>
              <h2 className="text-lg font-semibold text-white">重建完成!</h2>
              <p className="text-sm text-gray-400">
                重建完成
              </p>
            </div>
          </div>

          {/* Stats bar */}
          <div className="flex flex-wrap gap-4">
            {result.stats.num_gaussians != null && (
              <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#0d1520] border border-gray-700/50">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span className="text-sm text-gray-300">
                  <span className="font-mono text-cyan-400">{result.stats.num_gaussians?.toLocaleString()}</span> 高斯点
                </span>
              </div>
            )}
            {result.stats.num_photos != null && (
              <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#0d1520] border border-gray-700/50">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span className="text-sm text-gray-300">
                  <span className="font-mono text-cyan-400">{result.stats.num_photos}</span> 张照片
                </span>
              </div>
            )}
          </div>

          {/* 3D Viewer */}
          <section>
            <h3 className="text-lg font-semibold text-white mb-4">3D 预览</h3>
            <GSplatViewer plyUrl={plyArtifact ? `${API_BASE}${plyArtifact.url}` : ""} />
          </section>

          {/* Downloads */}
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
                      {ARTIFACT_LABELS[artifact.filename] || artifact.filename}
                    </p>
                    <p className="text-xs text-gray-600">
                      {formatSize(artifact.size_bytes)}
                    </p>
                  </div>
                  <a
                    href={`${API_BASE}${artifact.url}`}
                    download
                    className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg
                      bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-sm font-medium
                      hover:bg-cyan-500/20 hover:border-cyan-400/50 transition-all
                      group-hover:shadow-[0_0_15px_rgba(6,182,212,0.1)]"
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
