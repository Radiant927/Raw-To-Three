'use client';

import Link from 'next/link';
import { Camera, Brain, Filter, FileOutput, Clock, Image, ArrowLeft, Box } from 'lucide-react';

export default function PipelinePage() {
  const steps = [
    {
      step: 1,
      icon: Camera,
      title: 'COLMAP SfM',
      subtitle: 'Structure from Motion',
      description:
        '从多张照片中提取特征点，通过匹配与几何验证估计相机位姿，生成稀疏 3D 点云。',
      inputs: '20-100 张 JPG/PNG 照片',
      time: '5-15 分钟',
      color: '#00d4aa',
      gradient: 'from-cyan-900/40 to-cyan-800/10',
    },
    {
      step: 2,
      icon: Brain,
      title: '2DGS 训练',
      subtitle: '2D Gaussian Splatting',
      description:
        '在稀疏点云基础上，使用 2D Gaussian Splatting 算法迭代优化高斯参数。通过神经网络学习颜色、不透明度与几何形状，实现高质量新视角合成。',
      inputs: 'COLMAP 输出 + GPU',
      time: '30-90 分钟（GPU 加速）',
      color: '#4a9eff',
      gradient: 'from-blue-900/40 to-blue-800/10',
    },
    {
      step: 3,
      icon: Filter,
      title: '去噪优化',
      subtitle: 'Opacity Denoising',
      description:
        '对训练后的高斯模型进行去噪处理，移除低不透明度高斯点（opacity < 0.09），减少文件体积，提升渲染质量。去噪后高斯点数量可减少 70-90%。',
      inputs: '原始 PLY 文件',
      time: '约 1 分钟',
      color: '#a855f7',
      gradient: 'from-purple-900/40 to-purple-800/10',
    },
    {
      step: 4,
      icon: FileOutput,
      title: '导出与预览',
      subtitle: 'Export & Preview',
      description:
        '导出优化后的 PLY 文件并在浏览器内进行实时 3D 预览。支持旋转、缩放、平移交互，可对比去噪前后的模型效果。',
      inputs: '去噪后 PLY 文件',
      time: '即时',
      color: '#f59e0b',
      gradient: 'from-amber-900/40 to-amber-800/10',
    },
  ];

  return (
    <div className="flex flex-col flex-1 bg-[#0a0e17] text-gray-300">
      {/* Title Section */}
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

      {/* Steps Section */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          {/* Vertical connector line */}
          <div className="relative">
            {/* Connecting line */}
            <div className="absolute left-8 md:left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-cyan-500/50 via-blue-500/30 to-amber-500/50 -translate-x-1/2 hidden md:block" />

            {steps.map((step, i) => {
              const isEven = i % 2 === 0;

              return (
                <div key={step.step} className="relative pb-20 last:pb-0">
                  {/* Step number badge */}
                  <div className="absolute left-8 md:left-1/2 top-0 -translate-x-1/2 z-10 hidden md:flex">
                    <div
                      className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold text-white border-2"
                      style={{
                        borderColor: step.color,
                        backgroundColor: `${step.color}15`,
                      }}
                    >
                      {step.step}
                    </div>
                  </div>

                  {/* Mobile step number */}
                  <div className="flex items-center gap-3 mb-6 md:hidden">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold text-white border-2 flex-shrink-0"
                      style={{
                        borderColor: step.color,
                        backgroundColor: `${step.color}15`,
                      }}
                    >
                      {step.step}
                    </div>
                    <h2 className="text-2xl font-bold text-white" style={{ color: step.color }}>
                      {step.title}
                    </h2>
                  </div>

                  {/* Content row */}
                  <div
                    className={`flex flex-col md:flex-row items-center gap-8 ${
                      isEven ? 'md:flex-row' : 'md:flex-row-reverse'
                    }`}
                  >
                    {/* Image placeholder */}
                    <div className="w-full md:w-1/2 opacity-0 animate-fade-in-up">
                      <div
                        className={`aspect-video rounded-xl bg-gradient-to-br ${step.gradient} border border-white/10 flex items-center justify-center relative overflow-hidden`}
                      >
                        <step.icon className="w-20 h-20 text-white/20" />
                        {/* Decorative grid */}
                        <div className="absolute inset-0 opacity-10">
                          <div
                            className="w-full h-full"
                            style={{
                              backgroundImage:
                                'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
                              backgroundSize: '20px 20px',
                            }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Text content */}
                    <div className="w-full md:w-1/2 opacity-0 animate-fade-in-up">
                      {/* Desktop title */}
                      <h2
                        className="hidden md:block text-2xl font-bold mb-1"
                        style={{ color: step.color }}
                      >
                        {step.title}
                      </h2>
                      <p className="text-sm text-gray-500 font-mono mb-4 hidden md:block">
                        {step.subtitle}
                      </p>

                      <p className="text-gray-300 leading-relaxed mb-6">{step.description}</p>

                      {/* Metadata */}
                      <div className="flex flex-wrap gap-4">
                        <div className="flex items-center gap-2 glass px-3 py-2 rounded-lg">
                          <Image className="w-4 h-4 text-gray-500" />
                          <span className="text-xs text-gray-400">{step.inputs}</span>
                        </div>
                        <div className="flex items-center gap-2 glass px-3 py-2 rounded-lg">
                          <Clock className="w-4 h-4 text-gray-500" />
                          <span className="text-xs text-gray-400">{step.time}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Step 4: Comparison Slider Section */}
            <div className="mt-8 pt-8 border-t border-white/5">
              <h3 className="text-xl font-bold text-white text-center mb-8">
                去噪效果对比
              </h3>
              <div className="glass-card p-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                  {/* Before */}
                  <div className="text-center">
                    <div className="aspect-video rounded-xl bg-gradient-to-br from-red-900/30 to-red-800/10 border border-red-500/20 flex items-center justify-center mb-3">
                      <div className="text-center">
                        <Box className="w-12 h-12 text-red-400/40 mx-auto mb-2" />
                        <span className="text-sm text-red-400/60">密集高斯点云</span>
                      </div>
                    </div>
                    <span className="text-sm font-medium text-red-400">去噪前</span>
                    <p className="text-xs text-gray-500 mt-1">Opacity ≥ 0，高斯点数量较多</p>
                  </div>

                  {/* After */}
                  <div className="text-center">
                    <div className="aspect-video rounded-xl bg-gradient-to-br from-emerald-900/30 to-emerald-800/10 border border-emerald-500/20 flex items-center justify-center mb-3">
                      <div className="text-center">
                        <Box className="w-12 h-12 text-emerald-400/40 mx-auto mb-2" />
                        <span className="text-sm text-emerald-400/60">清洗后稀疏点云</span>
                      </div>
                    </div>
                    <span className="text-sm font-medium text-emerald-400">去噪后</span>
                    <p className="text-xs text-gray-500 mt-1">Opacity ≥ 0.09，减少 70-90%</p>
                  </div>
                </div>

                {/* Opacity slider visualization */}
                <div className="max-w-md mx-auto">
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
                    <span>Opacity Min</span>
                    <span className="text-cyan-400 font-mono font-bold">0.09</span>
                    <span>Opacity Max</span>
                  </div>
                  <div className="relative h-3 rounded-full bg-white/5 border border-white/10 overflow-hidden">
                    <div
                      className="absolute h-full bg-gradient-to-r from-red-500/50 via-yellow-500/50 to-emerald-500/50"
                      style={{ left: '9%', right: '0%' }}
                    />
                    <div
                      className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-cyan-400 shadow-lg border-2 border-white"
                      style={{ left: 'calc(9% - 4px)' }}
                    />
                  </div>
                  <p className="text-center text-xs text-gray-600 mt-2">
                    拖动滑块调整去噪阈值（当前：opacity_min = 0.09）
                  </p>
                  {/* CSS-only range input styled as a comparison slider */}
                  <input
                    type="range"
                    min="0"
                    max="100"
                    defaultValue={9}
                    className="w-full mt-3 appearance-none h-2 rounded-full bg-white/5 border border-white/10 cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-cyan-400 [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white"
                  />
                  <div className="flex justify-between text-xs text-gray-600 mt-1">
                    <span>0.00</span>
                    <span>0.05</span>
                    <span>0.10</span>
                    <span>0.15</span>
                    <span>0.20</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
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
