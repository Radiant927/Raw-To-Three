"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, FileImage, AlertCircle, X } from "lucide-react";

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void;
}

const ACCEPTED_TYPES = ["image/jpeg", "image/png"] as const;
const MIN_FILES = 20;
const MAX_FILES = 100;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_TOTAL_SIZE = 500 * 1024 * 1024; // 500MB

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadZone({ onFilesSelected }: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFiles = useCallback((files: File[]): string[] => {
    const errs: string[] = [];

    // Check count
    if (files.length < MIN_FILES) {
      errs.push(`至少需要 ${MIN_FILES} 张照片，当前选择了 ${files.length} 张`);
    }
    if (files.length > MAX_FILES) {
      errs.push(`最多支持 ${MAX_FILES} 张照片，当前选择了 ${files.length} 张`);
    }

    // Check types
    const invalidTypes = files.filter((f) => !ACCEPTED_TYPES.includes(f.type as typeof ACCEPTED_TYPES[number]));
    if (invalidTypes.length > 0) {
      const names = invalidTypes.slice(0, 3).map((f) => f.name).join("、");
      errs.push(`不支持的文件格式: ${names}${invalidTypes.length > 3 ? ` 等 ${invalidTypes.length} 个文件` : ""}`);
    }

    // Check per-file size
    const oversized = files.filter((f) => f.size > MAX_FILE_SIZE);
    if (oversized.length > 0) {
      const names = oversized.slice(0, 3).map((f) => f.name).join("、");
      errs.push(`文件超过 10MB 限制: ${names}${oversized.length > 3 ? ` 等 ${oversized.length} 个文件` : ""}`);
    }

    // Check total size
    const totalSize = files.reduce((sum, f) => sum + f.size, 0);
    if (totalSize > MAX_TOTAL_SIZE) {
      errs.push(`总大小 ${formatSize(totalSize)} 超过 500MB 限制`);
    }

    return errs;
  }, []);

  const handleFiles = useCallback(
    (files: File[]) => {
      const errs = validateFiles(files);
      setErrors(errs);
      if (errs.length === 0) {
        setSelectedFiles(files);
        onFilesSelected(files);
      } else {
        setSelectedFiles([]);
        onFilesSelected([]);
      }
    },
    [validateFiles, onFilesSelected]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) handleFiles(files);
    },
    [handleFiles]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (files.length > 0) handleFiles(files);
    },
    [handleFiles]
  );

  const handleClick = () => {
    inputRef.current?.click();
  };

  const clearFiles = () => {
    setSelectedFiles([]);
    setErrors([]);
    onFilesSelected([]);
    if (inputRef.current) inputRef.current.value = "";
  };

  const totalSize = selectedFiles.reduce((sum, f) => sum + f.size, 0);

  return (
    <div className="w-full">
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed
          p-10 transition-all duration-200 cursor-pointer min-h-[220px]
          ${isDragOver
            ? "border-cyan-400 bg-cyan-400/10 shadow-[0_0_30px_rgba(6,182,212,0.15)]"
            : selectedFiles.length > 0
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
          onChange={handleInputChange}
          className="hidden"
        />

        {selectedFiles.length > 0 ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-full bg-cyan-500/20 flex items-center justify-center">
              <FileImage className="w-7 h-7 text-cyan-400" />
            </div>
            <p className="text-lg font-medium text-white">
              已选择 {selectedFiles.length} 张照片
            </p>
            <p className="text-sm text-gray-400">总大小: {formatSize(totalSize)}</p>
            <button
              onClick={(e) => {
                e.stopPropagation();
                clearFiles();
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
              {errors.map((err, i) => (
                <p key={i} className="text-sm text-red-400">{err}</p>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
