"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, ChevronUp, Zap, Clock, Loader2 } from "lucide-react";
import UploadZone from "@/components/UploadZone";
import { createJob } from "@/lib/api";

export default function DemoPage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [paramsOpen, setParamsOpen] = useState(false);
  const [opacityMin, setOpacityMin] = useState(0.09);
  const [quality, setQuality] = useState<"high" | "medium">("high");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = files.length >= 20 && files.length <= 100;

  const handleFilesSelected = useCallback((newFiles: File[]) => {
    setFiles(newFiles);
    setError(null);
  }, []);

  const handleSubmit = async () => {
    if (!canSubmit || loading) return;
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append("photos", file);
      });
      formData.append("opacity_min", String(opacityMin));
      formData.append("iterations", "30000");
      formData.append("quality", quality);

      const result = await createJob(formData);
      router.push(`/demo/${result.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "提交失败，请重试");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e17] flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-white tracking-tight">RT Pipeline</h1>
        <span className="text-xs text-gray-500 font-mono">3D Gaussian Splatting</span>
      </header>

      <main className="flex-1 flex items-start justify-center px-4 py-12">
        <div className="w-full max-w-2xl flex flex-col gap-8">
          {/* Title */}
          <div>
            <h2 className="text-2xl font-bold text-white">上传照片</h2>
            <p className="mt-1 text-sm text-gray-400">
              上传多角度拍摄的照片，AI 将自动重建 3D 场景
            </p>
          </div>

          {/* Upload Zone */}
          <UploadZone onFilesSelected={handleFilesSelected} />

          {/* Params */}
          <div className="rounded-xl border border-gray-700/50 bg-[#0d1520] overflow-hidden">
            <button
              onClick={() => setParamsOpen(!paramsOpen)}
              className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-white/[0.02] transition-colors"
            >
              <span className="font-medium text-gray-200">参数配置</span>
              {paramsOpen ? (
                <ChevronUp className="w-5 h-5 text-gray-500" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-500" />
              )}
            </button>
            {paramsOpen && (
              <div className="px-5 pb-5 space-y-5 border-t border-gray-700/30 pt-4">
                {/* opacity_min */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm text-gray-400">透明度最小值 (opacity_min)</label>
                    <span className="text-sm font-mono text-cyan-400">{opacityMin}</span>
                  </div>
                  <input
                    type="range"
                    min="0.01"
                    max="0.5"
                    step="0.01"
                    value={opacityMin}
                    onChange={(e) => setOpacityMin(parseFloat(e.target.value))}
                    className="w-full h-2 rounded-full appearance-none bg-gray-700 cursor-pointer
                      [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5
                      [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full
                      [&::-webkit-slider-thumb]:bg-cyan-400 [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(6,182,212,0.5)]
                      [&::-webkit-slider-thumb]:cursor-pointer"
                  />
                  <div className="flex justify-between mt-1">
                    <span className="text-xs text-gray-600">0.01</span>
                    <span className="text-xs text-gray-600">0.50</span>
                  </div>
                </div>

                {/* iterations */}
                <div>
                  <label className="text-sm text-gray-400">训练迭代次数</label>
                  <div className="mt-1.5 px-3 py-2 rounded-lg bg-gray-800/50 border border-gray-700/50">
                    <span className="text-sm font-mono text-gray-400">30000</span>
                    <span className="text-xs text-gray-600 ml-2">（固定）</span>
                  </div>
                </div>

                {/* quality */}
                <div>
                  <label className="text-sm text-gray-400">输出质量</label>
                  <div className="flex gap-3 mt-1.5">
                    {(["high", "medium"] as const).map((q) => (
                      <button
                        key={q}
                        onClick={() => setQuality(q)}
                        className={`flex-1 px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
                          quality === q
                            ? "border-cyan-400/50 bg-cyan-400/10 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.1)]"
                            : "border-gray-700 bg-transparent text-gray-500 hover:text-gray-300 hover:border-gray-600"
                        }`}
                      >
                        {q === "high" ? "高" : "中等"}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Submit */}
          <div className="flex flex-col items-center gap-4">
            <button
              onClick={handleSubmit}
              disabled={!canSubmit || loading}
              className={`
                relative w-full max-w-sm py-3.5 px-8 rounded-xl font-semibold text-base
                transition-all duration-200 flex items-center justify-center gap-2
                ${
                  canSubmit && !loading
                    ? "bg-cyan-500 hover:bg-cyan-400 text-black shadow-[0_0_30px_rgba(6,182,212,0.3)] hover:shadow-[0_0_50px_rgba(6,182,212,0.5)]"
                    : "bg-gray-800 text-gray-500 cursor-not-allowed"
                }
              `}
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  提交中...
                </>
              ) : (
                <>
                  <Zap className="w-5 h-5" />
                  开始处理
                </>
              )}
            </button>

            {canSubmit && (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Clock className="w-4 h-4" />
                <span>预计耗时: 约 60 分钟</span>
              </div>
            )}

            {!canSubmit && files.length > 0 && (
              <p className="text-sm text-gray-600">请选择 20-100 张照片</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
