'use client';

import Link from 'next/link';
import {
  Upload,
  Cpu,
  Box,
  ArrowRight,
  ChevronDown,
  Camera,
  Grid3X3,
  Cuboid,
} from 'lucide-react';

export default function HomePage() {
  const features = [
    {
      icon: Upload,
      title: '上传照片',
      description: '上传 20-100 张多角度拍摄的 JPG/PNG 照片，系统自动识别 EXIF 信息并进行预处理。',
      color: '#00d4aa',
    },
    {
      icon: Cpu,
      title: '智能重建',
      description: '基于 COLMAP SfM 与 2D Gaussian Splatting 的先进重建算法，全流程 GPU 加速。',
      color: '#4a9eff',
    },
    {
      icon: Box,
      title: '3D 预览',
      description: '浏览器内交互式 3D 高斯预览，支持旋转、缩放、平移，实时探索重建模型。',
      color: '#a855f7',
    },
  ];

  const results = [
    {
      icon: Camera,
      title: '原始照片',
      description: '上传多角度拍摄的照片作为重建素材',
      gradient: 'from-blue-900/40 to-blue-800/20',
    },
    {
      icon: Grid3X3,
      title: 'COLMAP 点云',
      description: 'SfM 稀疏重建与相机位姿估计结果',
      gradient: 'from-cyan-900/40 to-cyan-800/20',
    },
    {
      icon: Cuboid,
      title: '3DGS 模型',
      description: '2D Gaussian Splatting 实时渲染模型',
      gradient: 'from-emerald-900/40 to-emerald-800/20',
    },
  ];

  return (
    <div className="flex flex-col flex-1 bg-[#0a0e17] text-gray-300">
      {/* ===== Hero Section ===== */}
      <section className="animated-grid relative min-h-screen flex flex-col items-center justify-center px-6">
        {/* Decorative orbs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-blue-500/10 rounded-full blur-[100px] pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center text-center max-w-4xl">
          <div className="animate-fade-in-up opacity-0" style={{ animationDelay: '0.1s' }}>
            <span className="inline-block px-3 py-1 mb-6 text-xs font-mono tracking-widest uppercase text-cyan-400 border border-cyan-500/30 rounded-full glass">
              WebGL-based 3D Gaussian Splatting
            </span>
          </div>

          <h1
            className="animate-fade-in-up opacity-0 text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight text-white mb-6 text-glow select-none"
            style={{ animationDelay: '0.3s' }}
          >
            RT Pipeline
          </h1>

          <p
            className="animate-fade-in-up opacity-0 text-lg md:text-xl text-gray-400 max-w-2xl mb-10 leading-relaxed"
            style={{ animationDelay: '0.5s' }}
          >
            从照片到 3D 高斯模型 — 一键式三维重建平台
          </p>

          <div
            className="animate-fade-in-up opacity-0 flex flex-col sm:flex-row gap-4"
            style={{ animationDelay: '0.7s' }}
          >
            <Link
              href="/pipeline"
              className="group flex items-center gap-2 px-8 py-3 border border-cyan-500/40 text-cyan-400 rounded-lg font-medium transition-all duration-300 hover:border-cyan-400 hover:bg-cyan-500/10 hover:text-cyan-300"
            >
              了解原理
              <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
            <Link
              href="/demo"
              className="group flex items-center gap-2 px-8 py-3 bg-cyan-500 text-gray-900 rounded-lg font-semibold transition-all duration-300 hover:bg-cyan-400 animate-pulse-glow"
            >
              立即体验
              <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 animate-scroll-pulse z-10">
          <ChevronDown className="w-6 h-6 text-cyan-500/60" />
        </div>
      </section>

      {/* ===== Feature Cards ===== */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-white text-center mb-4">
            核心功能
          </h2>
          <p className="text-gray-500 text-center mb-16 max-w-xl mx-auto">
            全流程自动化，从照片到交互式 3D 模型只需简单几步
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <div
                key={feature.title}
                className="glass-card p-8 flex flex-col items-center text-center cursor-default opacity-0 animate-fade-in-up"
                style={{ animationDelay: `${0.2 + i * 0.15}s` }}
              >
                <div
                  className="w-16 h-16 rounded-xl flex items-center justify-center mb-6"
                  style={{ backgroundColor: `${feature.color}15` }}
                >
                  <feature.icon className="w-8 h-8" style={{ color: feature.color }} />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">{feature.title}</h3>
                <p className="text-gray-500 leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== Result Cards ===== */}
      <section className="py-24 px-6 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-white text-center mb-4">
            重建流程
          </h2>
          <p className="text-gray-500 text-center mb-16 max-w-xl mx-auto">
            从 2D 照片到 3D 高斯模型的完整步骤
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {results.map((result, i) => (
              <div
                key={result.title}
                className="glass-card overflow-hidden opacity-0 animate-fade-in-up"
                style={{ animationDelay: `${0.2 + i * 0.15}s` }}
              >
                {/* Placeholder gradient area */}
                <div
                  className={`h-48 bg-gradient-to-br ${result.gradient} flex items-center justify-center`}
                >
                  <result.icon className="w-16 h-16 text-white/30" />
                </div>
                <div className="p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-mono text-cyan-400">
                      Step {i + 1}
                    </span>
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{result.title}</h3>
                  <p className="text-gray-500 text-sm leading-relaxed">{result.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== Footer CTA ===== */}
      <section className="py-24 px-6 border-t border-white/5">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            开始你的 3D 重建之旅
          </h2>
          <p className="text-gray-500 mb-8">
            无需复杂配置，上传照片即刻生成可交互的 3D 模型
          </p>
          <Link
            href="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 bg-cyan-500 text-gray-900 rounded-lg font-semibold transition-all duration-300 hover:bg-cyan-400 animate-pulse-glow"
          >
            立即体验
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
