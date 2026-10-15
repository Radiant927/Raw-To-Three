"use client";

import Image from "next/image";
import Link from "next/link";
import {
  Clock,
  Image as ImageIcon,
  ArrowLeft,
} from "lucide-react";

interface StageDef {
  num: number;
  color: string;
  title: string;
  subtitle: string;
  image: string;
  description: React.ReactNode;
  chips: [string, string];
  reverse: boolean;
}

const STAGES: StageDef[] = [
  {
    num: 1,
    color: "#00d4aa",
    title: "COLMAP SfM",
    subtitle: "Structure from Motion",
    image: "/examples/colmap.jpg",
    description:
      "从多张照片中提取特征点，通过匹配与几何验证估计相机位姿，生成稀疏 3D 点云。",
    chips: ["20-100 张 JPG/PNG 照片", "5-15 分钟"],
    reverse: false,
  },
  {
    num: 2,
    color: "#4a9eff",
    title: "3DGS 训练",
    subtitle: "3D Gaussian Splatting",
    image: "/examples/trained.jpg",
    description:
      "在稀疏点云基础上，使用 3D Gaussian Splatting 算法迭代优化高斯参数。通过神经网络学习颜色、不透明度与几何形状，实现高质量新视角合成。",
    chips: ["COLMAP 输出 + GPU", "30-90 分钟（GPU 加速）"],
    reverse: true,
  },
  {
    num: 3,
    color: "#a855f7",
    title: "去噪优化",
    subtitle: "Opacity Denoising",
    image: "/examples/denoised.jpg",
    description: (
      <>
        对训练后的高斯模型进行去噪处理，移除低不透明度高斯点（opacity &lt;
        0.09），减少文件体积，提升渲染质量。去噪后高斯点数量可减少 70-90%。
      </>
    ),
    chips: ["原始 PLY 文件", "约 1 分钟"],
    reverse: false,
  },
  {
    num: 4,
    color: "#f59e0b",
    title: "导出与预览",
    subtitle: "Export & Preview",
    image: "/examples/preview.jpg",
    description:
      "导出优化后的 PLY 文件并在浏览器内进行实时 3D 预览。支持旋转、缩放、平移交互，可对比去噪前后的模型效果。",
    chips: ["去噪后 PLY 文件", "即时"],
    reverse: true,
  },
];

export default function PipelinePage() {
  return (
    <div className="flex flex-col flex-1 bg-[#0a0e17] text-gray-300">
      {/* Header */}
      <section className="py-20 px-6 border-b border-white/5">
        <div className="max-w-4xl mx-auto">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-gray-500 hover:text-cyan-400 transition-colors mb-8"
          >
            <ArrowLeft className="w-4 h-4" />
            返回首页
          </Link>
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4 text-glow">
            Pipeline 原理
          </h1>
          <p className="text-gray-400 text-lg max-w-2xl">
            了解 RT Pipeline 从照片到 3D 高斯模型的完整技术流程
          </p>
        </div>
      </section>

      {/* Timeline */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="relative">
            <div className="absolute left-8 md:left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-cyan-500/50 via-blue-500/30 to-amber-500/50 -translate-x-1/2 hidden md:block" />

            {STAGES.map((stage) => (
              <div key={stage.num} className="relative pb-20 last:pb-0">
                <div className="absolute left-8 md:left-1/2 top-0 -translate-x-1/2 z-10 hidden md:flex">
                  <div
                    className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold text-white border-2"
                    style={{
                      borderColor: stage.color,
                      backgroundColor: `${stage.color}15`,
                    }}
                  >
                    {stage.num}
                  </div>
                </div>

                <div className="flex items-center gap-3 mb-6 md:hidden">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold text-white border-2 flex-shrink-0"
                    style={{
                      borderColor: stage.color,
                      backgroundColor: `${stage.color}15`,
                    }}
                  >
                    {stage.num}
                  </div>
                  <h2 className="text-2xl font-bold" style={{ color: stage.color }}>
                    {stage.title}
                  </h2>
                </div>

                <div
                  className={`flex flex-col md:flex-row items-center gap-8${
                    stage.reverse ? " md:flex-row-reverse" : ""
                  }`}
                >
                  <div className="w-full md:w-1/2 opacity-0 animate-fade-in-up">
                    <div className="aspect-video rounded-xl border border-white/10 relative overflow-hidden bg-[#0d1520]">
                      <Image
                        src={stage.image}
                        alt={stage.title}
                        fill
                        sizes="(max-width: 768px) 100vw, 50vw"
                        className="object-cover"
                      />
                    </div>
                  </div>

                  <div className="w-full md:w-1/2 opacity-0 animate-fade-in-up">
                    <h2
                      className="hidden md:block text-2xl font-bold mb-1"
                      style={{ color: stage.color }}
                    >
                      {stage.title}
                    </h2>
                    <p className="text-sm text-gray-500 font-mono mb-4 hidden md:block">
                      {stage.subtitle}
                    </p>
                    <p className="text-gray-300 leading-relaxed mb-6">
                      {stage.description}
                    </p>
                    <div className="flex flex-wrap gap-4">
                      <div className="flex items-center gap-2 glass px-3 py-2 rounded-lg">
                        <ImageIcon className="w-4 h-4 text-gray-500" />
                        <span className="text-xs text-gray-400">{stage.chips[0]}</span>
                      </div>
                      <div className="flex items-center gap-2 glass px-3 py-2 rounded-lg">
                        <Clock className="w-4 h-4 text-gray-500" />
                        <span className="text-xs text-gray-400">{stage.chips[1]}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6 border-t border-white/5">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl font-bold text-white mb-4">准备好体验了吗？</h2>
          <p className="text-gray-500 mb-8">
            上传你的照片，亲眼见证从 2D 到 3D 的神奇转变
          </p>
          <Link
            href="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 bg-cyan-500 text-gray-900 rounded-lg font-semibold transition-all duration-300 hover:bg-cyan-400 animate-pulse-glow"
          >
            立即体验
          </Link>
        </div>
      </section>
    </div>
  );
}
