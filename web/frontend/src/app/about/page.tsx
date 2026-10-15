import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "关于 - RT Pipeline",
  description: "了解 RT Pipeline 的技术栈与团队信息",
};

const TECH_STACK = [
  { name: "COLMAP", color: "#00d4aa" },
  { name: "3D Gaussian Splatting", color: "#4a9eff" },
  { name: "Open3D", color: "#a855f7" },
  { name: "Next.js", color: "#f59e0b" },
  { name: "FastAPI", color: "#10b981" },
  { name: "gsplat.js", color: "#00d4aa" },
  { name: "WebSocket", color: "#4a9eff" },
  { name: "SQLite", color: "#6366f1" },
  { name: "Tailwind CSS", color: "#38bdf8" },
  { name: "TypeScript", color: "#60a5fa" },
];

const CREDITS = [
  {
    url: "https://github.com/colmap/colmap",
    name: "COLMAP",
    desc: "通用 Structure from Motion 与 Multi-View Stereo 管线",
  },
  {
    url: "https://github.com/nerfstudio-project/nerfstudio",
    name: "3D Gaussian Splatting",
    desc: "3D 高斯泼溅（splatfacto）用于几何重建与新视角合成",
  },
  {
    url: "https://github.com/mkkellogg/gsplat.js",
    name: "gsplat.js",
    desc: "浏览器端高斯泼溅实时渲染引擎",
  },
  {
    url: "https://nextjs.org/",
    name: "Next.js",
    desc: "React 全栈框架",
  },
  {
    url: "https://github.com/twak/awesome-3dgs",
    name: "3D Gaussian Splatting 社区",
    desc: "前沿技术的持续推动者",
  },
];

export default function AboutPage() {
  return (
    <div className="flex flex-col flex-1 bg-[#0a0e17] text-gray-300 min-h-screen">
      {/* Header */}
      <section className="py-16 px-6 border-b border-white/5">
        <div className="max-w-4xl mx-auto">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-gray-500 hover:text-cyan-400 transition-colors mb-6"
          >
            <ArrowLeft className="w-4 h-4" />
            返回首页
          </Link>
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-3 text-glow">
            关于
          </h1>
          <p className="text-gray-400 text-lg">RT Pipeline — 一键式三维重建平台</p>
        </div>
      </section>

      {/* 技术栈 */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-white mb-3">技术栈</h2>
          <p className="text-gray-500 mb-10">本平台基于以下开源技术与框架构建</p>
          <div className="flex flex-wrap gap-3">
            {TECH_STACK.map((tech) => (
              <span
                key={tech.name}
                className="px-4 py-2 text-sm font-medium rounded-full border bg-white/5 backdrop-blur-md transition-all duration-300 hover:scale-105"
                style={{ borderColor: `${tech.color}40`, color: tech.color }}
              >
                {tech.name}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* 致谢 */}
      <section className="py-20 px-6 border-t border-white/5">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-white mb-3">致谢</h2>
          <div className="glass-card p-8 space-y-5">
            <p className="text-gray-400 leading-relaxed">
              RT Pipeline
              是一个面向科研与教育场景的三维重建平台，将
              COLMAP Structure from Motion 与 3D Gaussian Splatting
              等技术整合为简单易用的 Web 工作流，让用户无需
              配置复杂环境即可完成从照片到交互式 3D 模型的全流程重建。
            </p>
            <p className="text-gray-400 leading-relaxed">
              本项目的前端基于 Next.js 16 与 React 19 构建，采用 Tailwind CSS
              实现界面样式； 3D 渲染使用 gsplat.js（基于 WebGL
              的高斯泼溅渲染库）；后端使用 FastAPI 提供 RESTful API 与
              WebSocket 实时通信，任务调度基于 SQLite 进行轻量化管理。
            </p>
            <p className="text-gray-400 leading-relaxed">
              感谢以下开源项目与社区的贡献：
            </p>
            <ul className="space-y-2 text-gray-400">
              {CREDITS.map((credit) => (
                <li key={credit.name} className="flex items-start gap-2">
                  <span className="text-cyan-400 mt-1">▹</span>
                  <span>
                    <a
                      href={credit.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400 hover:underline"
                    >
                      {credit.name}
                    </a>{" "}
                    — {credit.desc}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <div className="py-12 px-6 border-t border-white/5">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-gray-600 text-sm">
            RT Pipeline © 2026 — Built with passion for 3D reconstruction
          </p>
        </div>
      </div>
    </div>
  );
}
