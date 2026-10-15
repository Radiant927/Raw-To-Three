"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle, Loader2, RotateCcw, Maximize2 } from "lucide-react";

interface SplatViewerProps {
  plyUrl: string;
}

// 简单向量工具
const sub = (a: number[], b: number[]) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a: number[], b: number[]) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a: number[], b: number[]) => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
const norm = (a: number[]) => {
  const l = Math.hypot(a[0], a[1], a[2]) || 1;
  return [a[0] / l, a[1] / l, a[2] / l];
};

export default function SplatViewer({ plyUrl }: SplatViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const axisCanvasRef = useRef<HTMLCanvasElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!plyUrl) {
      setLoading(false);
      setError("无 PLY 文件路径");
      return;
    }

    let cancelled = false;
    let frame: number | null = null;
    let controls: any = null;
    let splat: any = null;
    let renderer: any = null;
    let scene: any = null;
    let camera: any = null;
    let resizeObserver: ResizeObserver | null = null;

    let initialPos: { x: number; y: number; z: number } | null = null;
    let initialTarget: { x: number; y: number; z: number } | null = null;

    const canvas = canvasRef.current;
    const container = containerRef.current;
    const axisCanvas = axisCanvasRef.current;
    if (!canvas || !container) return;

    setLoading(true);
    setError(null);

    const init = (async () => {
      try {
        const GS = await import("gsplat");
        const rect = container.getBoundingClientRect();
        const width = rect.width || 800;
        const height = rect.height || 500;

        canvas.width = width * window.devicePixelRatio;
        canvas.height = height * window.devicePixelRatio;
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        canvas.style.touchAction = "none";

        renderer = new GS.WebGLRenderer(canvas);
        renderer.setSize(canvas.width, canvas.height);

        scene = new GS.Scene();
        camera = new GS.Camera();

        controls = new GS.OrbitControls(camera, canvas);
        controls.orbitSpeed = 0.9;
        controls.zoomSpeed = 1;
        controls.panSpeed = 1;
        controls.dampening = 0.1;
        // 关键：俯仰角限制在 ±70°，左右方位角不受限（天然 360°），
        // 这样既能绕一圈看，又永远不会上下颠倒
        controls.minAngle = -70;
        controls.maxAngle = 70;
        controls.minZoom = 0.2;
        controls.maxZoom = 100;

        await GS.PLYLoader.LoadAsync(plyUrl, scene, () => {}, undefined, true);
        if (cancelled) return;

        splat = scene.findObjectOfType(GS.Splat);
        let centerVec: any = null;
        if (splat) {
          splat.recalculateBounds();
          const bounds = splat.bounds;
          const center = bounds.center();
          const size = bounds.size();
          const maxDim = Math.max(size.x, size.y, size.z) || 1;
          const distance = maxDim * 2.2;

          centerVec = new GS.Vector3(center.x, center.y, center.z);
          controls.setCameraTarget(centerVec);

          // 初始视角：右前方 + 30° 俯视
          const azimuth = Math.PI * 0.15;
          const elev = Math.PI * 0.28;
          camera.position.x = center.x + distance * Math.sin(azimuth) * Math.cos(elev);
          camera.position.y = center.y + distance * Math.sin(elev);
          camera.position.z = center.z + distance * Math.cos(azimuth) * Math.cos(elev);

          initialPos = {
            x: camera.position.x,
            y: camera.position.y,
            z: camera.position.z,
          };
          initialTarget = { x: center.x, y: center.y, z: center.z };
        }

        const resetView = () => {
          if (!initialPos || !initialTarget || !controls || !camera || !GS) return;
          controls.setCameraTarget(
            new GS.Vector3(initialTarget.x, initialTarget.y, initialTarget.z),
          );
          camera.position.x = initialPos.x;
          camera.position.y = initialPos.y;
          camera.position.z = initialPos.z;
        };
        (canvas as any).__resetView = resetView;
        canvas.addEventListener("dblclick", resetView);

        // 绘制右下角坐标轴
        const drawAxis = () => {
          if (!axisCanvas || !camera) return;
          const dpr = window.devicePixelRatio || 1;
          const S = 72;
          if (axisCanvas.width !== S * dpr) {
            axisCanvas.width = S * dpr;
            axisCanvas.height = S * dpr;
            axisCanvas.style.width = `${S}px`;
            axisCanvas.style.height = `${S}px`;
          }
          const ctx = axisCanvas.getContext("2d");
          if (!ctx) return;
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          ctx.clearRect(0, 0, S, S);

          const cx = S / 2;
          const cy = S / 2;
          const L = S * 0.3;

          // 相机基向量：forward = target - pos
          const pos = [camera.position.x, camera.position.y, camera.position.z];
          const tgt = centerVec
            ? [centerVec.x, centerVec.y, centerVec.z]
            : [0, 0, 0];
          const f = norm(sub(tgt, pos));
          const r = norm(cross(f, [0, 1, 0]));
          const u = cross(r, f);

          // 背景圆
          ctx.beginPath();
          ctx.arc(cx, cy, S * 0.42, 0, Math.PI * 2);
          ctx.fillStyle = "rgba(10,13,20,0.55)";
          ctx.fill();
          ctx.strokeStyle = "rgba(255,255,255,0.12)";
          ctx.lineWidth = 1;
          ctx.stroke();

          const axes = [
            { v: [1, 0, 0], color: "#ef4444", label: "X" },
            { v: [0, 1, 0], color: "#22c55e", label: "Y" },
            { v: [0, 0, 1], color: "#3b82f6", label: "Z" },
          ];
          // 按深度排序：指向远处的先画（被近处遮挡）
          const projected = axes
            .map((a) => ({
              ...a,
              sx: dot(a.v, r),
              sy: -dot(a.v, u),
              depth: dot(a.v, f), // <0 表示指向相机
            }))
            .sort((a, b) => b.depth - a.depth);

          for (const a of projected) {
            const x2 = cx + a.sx * L;
            const y2 = cy + a.sy * L;
            const front = a.depth < 0;
            ctx.globalAlpha = front ? 1 : 0.35;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(x2, y2);
            ctx.strokeStyle = a.color;
            ctx.lineWidth = front ? 2.5 : 1.5;
            ctx.stroke();
            // 轴端小点 + 标签
            ctx.beginPath();
            ctx.arc(x2, y2, front ? 2.5 : 1.8, 0, Math.PI * 2);
            ctx.fillStyle = a.color;
            ctx.fill();
            ctx.fillStyle = a.color;
            ctx.font = "10px ui-monospace, monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(a.label, cx + a.sx * L * 1.32, cy + a.sy * L * 1.32);
            ctx.globalAlpha = 1;
          }
        };

        canvas.style.visibility = "visible";
        setLoading(false);

        resizeObserver = new ResizeObserver(() => {
          if (cancelled || !renderer || !container) return;
          const r = container.getBoundingClientRect();
          const w = r.width || 800;
          const h = r.height || 500;
          const nw = w * window.devicePixelRatio;
          const nh = h * window.devicePixelRatio;
          if (canvas.width !== nw || canvas.height !== nh) {
            canvas.width = nw;
            canvas.height = nh;
            canvas.style.width = `${w}px`;
            canvas.style.height = `${h}px`;
            renderer.setSize(nw, nh);
          }
        });
        resizeObserver.observe(container);

        const loop = () => {
          if (cancelled) return;
          controls?.update();
          renderer.render(scene, camera);
          drawAxis();
          frame = requestAnimationFrame(loop);
        };
        loop();
      } catch (e) {
        if (cancelled) return;
        console.error("GSplat viewer error:", e);
        const message = e instanceof Error ? e.message : "3D 模型加载失败";
        setError(`3D 模型加载失败: ${message}`);
        setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      if (frame !== null) cancelAnimationFrame(frame);
      controls?.dispose?.();
      resizeObserver?.disconnect();
      renderer?.dispose?.();
      splat?.dispose?.();
    };
  }, [plyUrl]);

  const handleReset = () => {
    (canvasRef.current as any)?.__resetView?.();
  };

  const handleFullscreen = () => {
    if (!containerRef.current) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      containerRef.current.requestFullscreen();
    }
  };

  return (
    <div
      ref={containerRef}
      className="relative w-full min-h-[400px] rounded-xl overflow-hidden bg-[#0a0d14] border border-gray-700/50"
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 cursor-grab active:cursor-grabbing"
        style={{ visibility: loading ? "hidden" : "visible" }}
      />

      {/* 右下角坐标轴 */}
      {!loading && !error && (
        <canvas
          ref={axisCanvasRef}
          className="absolute bottom-3 right-3 z-10 pointer-events-none"
        />
      )}

      {/* 右上角按钮 */}
      {!loading && !error && (
        <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5">
          <button
            onClick={handleReset}
            title="重置视角（双击画布也可以）"
            className="p-1.5 rounded-lg bg-black/40 hover:bg-black/60 text-gray-300 hover:text-white transition-colors border border-white/10 backdrop-blur-sm"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={handleFullscreen}
            title="全屏"
            className="p-1.5 rounded-lg bg-black/40 hover:bg-black/60 text-gray-300 hover:text-white transition-colors border border-white/10 backdrop-blur-sm"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 左下角操作说明 */}
      {!loading && !error && (
        <div className="absolute bottom-3 left-3 z-10 px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 backdrop-blur-sm text-xs text-gray-300">
          <span className="text-cyan-400">左键</span> 旋转（左右 360°）
          <span className="text-white/20 mx-2">|</span>
          <span className="text-cyan-400">右键</span> 平移
          <span className="text-white/20 mx-2">|</span>
          <span className="text-cyan-400">滚轮</span> 缩放
        </div>
      )}

      {loading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 z-10">
          <Loader2 className="w-10 h-10 text-cyan-400 animate-spin" />
          <span className="text-gray-400">加载 3D 模型中...</span>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 z-10">
          <AlertCircle className="w-10 h-10 text-red-400" />
          <span className="text-red-400 text-sm text-center px-4">
            {error}
          </span>
        </div>
      )}
    </div>
  );
}
