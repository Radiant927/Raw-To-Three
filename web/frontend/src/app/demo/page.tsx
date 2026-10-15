"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  FileImage,
  Loader2,
  Upload,
  X,
  Zap,
} from "lucide-react";
import { createJob } from "@/lib/api";

const MIME_TYPES = ["image/jpeg", "image/png"];

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function validateFiles(files: File[]): string[] {
  const errors: string[] = [];

  if (files.length < 20) {
    errors.push(`至少需要 20 张照片，当前选择了 ${files.length} 张`);
  }
  if (files.length > 100) {
    errors.push(`最多支持 100 张照片，当前选择了 ${files.length} 张`);
  }

  const invalidType = files.filter((f) => !MIME_TYPES.includes(f.type));
  if (invalidType.length > 0) {
    const names = invalidType
      .slice(0, 3)
      .map((f) => f.name)
      .join("、");
    errors.push(
      `不支持的文件格式: ${names}${
        invalidType.length > 3 ? ` 等 ${invalidType.length} 个文件` : ""
      }`
    );
  }

  const tooBig = files.filter((f) => f.size > 50 * 1024 * 1024);
  if (tooBig.length > 0) {
    const names = tooBig
      .slice(0, 3)
      .map((f) => f.name)
      .join("、");
    errors.push(
      `文件超过 50MB 限制: ${names}${
        tooBig.length > 3 ? ` 等 ${tooBig.length} 个文件` : ""
      }`
    );
  }

  const total = files.reduce((sum, f) => sum + f.size, 0);
  if (total > 2 * 1024 * 1024 * 1024) {
    errors.push(`总大小 ${formatSize(total)} 超过 2GB 限制`);
  }

  return errors;
}

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void;
}

function UploadZone({ onFilesSelected }: UploadZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const [validFiles, setValidFiles] = useState<File[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (files: File[]) => {
      const errs = validateFiles(files);
      setErrors(errs);
      if (errs.length === 0) {
        setValidFiles(files);
        onFilesSelected(files);
      } else {
        setValidFiles([]);
        onFilesSelected([]);
      }
    },
    [onFilesSelected]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(false);
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) handleFiles(files);
    },
    [handleFiles]
  );

  const totalSize = validFiles.reduce((sum, f) => sum + f.size, 0);

  const clear = () => {
    setValidFiles([]);
    setErrors([]);
    onFilesSelected([]);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="w-full">
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setDragOver(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setDragOver(false);
        }}
        onDrop={onDrop}
        className={`
          relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed
          p-10 transition-all duration-200 cursor-pointer min-h-[220px]
          ${
            dragOver
              ? "border-cyan-400 bg-cyan-400/10 shadow-[0_0_30px_rgba(6,182,212,0.15)]"
              : validFiles.length > 0
                ? "border-cyan-500/50 bg-[#0d1520]"
                : "border-gray-600 hover:border-cyan-500/50 bg-[#0d1520] hover:bg-[#101a26]"
          }
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".jpg,.jpeg,.png"
          multiple
          className="hidden"
          onChange={(e) => {
            const files = Array.from(e.target.files ?? []);
            if (files.length > 0) handleFiles(files);
          }}
        />

        {validFiles.length > 0 ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-full bg-cyan-500/20 flex items-center justify-center">
              <FileImage className="w-7 h-7 text-cyan-400" />
            </div>
            <p className="text-lg font-medium text-white">
              已选择 {validFiles.length} 张照片
            </p>
            <p className="text-sm text-gray-400">总大小: {formatSize(totalSize)}</p>
            <button
              onClick={(e) => {
                e.stopPropagation();
                clear();
              }}
              className="mt-2 px-4 py-1.5 text-sm text-gray-400 hover:text-white border border-gray-600 hover:border-gray-400 rounded-lg transition-colors flex items-center gap-1"
            >
              <X className="w-4 h-4" />
              清除选择
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-full bg-cyan-500/10 flex items-center justify-center">
              <Upload className="w-8 h-8 text-cyan-400" />
            </div>
            <p className="text-lg font-medium text-gray-300">拖拽照片到此处或点击选择</p>
            <p className="text-sm text-gray-500">支持 JPG/PNG 格式，20-100 张</p>
          </div>
        )}
      </div>

      {errors.length > 0 && (
        <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/30">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex flex-col gap-1">
              {errors.map((err, idx) => (
                <p key={idx} className="text-sm text-red-400">
                  {err}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DemoPage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [paramsOpen, setParamsOpen] = useState(false);
  const [opacityMin, setOpacityMin] = useState(0.09);
  const [quality, setQuality] = useState("high");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const countValid = files.length >= 20 && files.length <= 100;

  const handleSubmit = async () => {
    if (!countValid || submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const jobId = await createJob({
        opacityMin,
        iterations: 30000,
        quality,
        photos: files,
      });
      router.push(`/demo/${jobId}`);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "提交失败，请重试");
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e17] flex flex-col">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-white tracking-tight">RT Pipeline</h1>
        <span className="text-xs text-gray-500 font-mono">3D Gaussian Splatting</span>
      </header>

      <main className="flex-1 flex items-start justify-center px-4 py-12">
        <div className="w-full max-w-2xl flex flex-col gap-8">
          <div>
            <h2 className="text-2xl font-bold text-white">上传照片</h2>
            <p className="mt-1 text-sm text-gray-400">
              上传多角度拍摄的照片，AI 将自动重建 3D 场景
            </p>
          </div>

          <UploadZone onFilesSelected={setFiles} />

          <div className="rounded-xl border border-gray-700/50 bg-[#0d1520] overflow-hidden">
            <button
              onClick={() => setParamsOpen((v) => !v)}
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
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm text-gray-400">
                      透明度最小值 (opacity_min)
                    </label>
                    <span className="text-sm font-mono text-cyan-400">
                      {opacityMin.toFixed(2)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={0.01}
                    max={0.5}
                    step={0.01}
                    value={opacityMin}
                    onChange={(e) => setOpacityMin(parseFloat(e.target.value))}
                    className="w-full h-2 rounded-full appearance-none bg-gray-700 cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-cyan-400 [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(6,182,212,0.5)] [&::-webkit-slider-thumb]:cursor-pointer"
                  />
                  <div className="flex justify-between mt-1">
                    <span className="text-xs text-gray-600">0.01</span>
                    <span className="text-xs text-gray-600">0.50</span>
                  </div>
                </div>

                <div>
                  <label className="text-sm text-gray-400">训练迭代次数</label>
                  <div className="mt-1.5 px-3 py-2 rounded-lg bg-gray-800/50 border border-gray-700/50">
                    <span className="text-sm font-mono text-gray-400">30000</span>
                    <span className="text-xs text-gray-600 ml-2">（固定）</span>
                  </div>
                </div>

                <div>
                  <label className="text-sm text-gray-400">输出质量</label>
                  <div className="flex gap-3 mt-1.5">
                    {["high", "medium"].map((q) => (
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

          {submitError && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30">
              <p className="text-sm text-red-400">{submitError}</p>
            </div>
          )}

          <div className="flex flex-col items-center gap-4">
            <button
              onClick={handleSubmit}
              disabled={!countValid || submitting}
              className={`
                relative w-full max-w-sm py-3.5 px-8 rounded-xl font-semibold text-base
                transition-all duration-200 flex items-center justify-center gap-2
                ${
                  countValid && !submitting
                    ? "bg-cyan-500 hover:bg-cyan-400 text-black shadow-[0_0_30px_rgba(6,182,212,0.3)] hover:shadow-[0_0_50px_rgba(6,182,212,0.5)]"
                    : "bg-gray-800 text-gray-500 cursor-not-allowed"
                }
              `}
            >
              {submitting ? (
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

            {countValid && (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Clock className="w-4 h-4" />
                <span>预计耗时: 约 60 分钟</span>
              </div>
            )}
            {!countValid && files.length > 0 && (
              <p className="text-sm text-gray-600">请选择 20-100 张照片</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
