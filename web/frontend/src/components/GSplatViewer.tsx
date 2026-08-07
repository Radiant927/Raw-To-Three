"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, AlertCircle } from "lucide-react";

interface GSplatViewerProps {
  plyUrl: string;
}

export default function GSplatViewer({ plyUrl }: GSplatViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!plyUrl) {
      setLoading(false);
      setError("无 PLY 文件路径");
      return;
    }

    let cancelled = false;
    let animId: number | null = null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let controls: any = null;

    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    setLoading(true);
    setError(null);

    async function initViewer() {
      try {
        // Dynamically import gsplat
        const SPLAT = await import("gsplat");

        // Set canvas to a reasonable initial size
        const rect = container!.getBoundingClientRect();
        const w = rect.width || 800;
        const h = rect.height || 500;
        canvas!.width = w * window.devicePixelRatio;
        canvas!.height = h * window.devicePixelRatio;
        canvas!.style.width = w + "px";
        canvas!.style.height = h + "px";

        // Create renderer
        const renderer = new SPLAT.WebGLRenderer(canvas!);
        renderer.setSize(canvas!.width, canvas!.height);

        // Create scene and camera
        const scene = new SPLAT.Scene();
        const camera = new SPLAT.Camera();

        // Orbit controls
        controls = new SPLAT.OrbitControls(camera, canvas!);
        controls.orbitSpeed = 0.5;
        controls.zoomSpeed = 1.0;

        // Load PLY
        await SPLAT.PLYLoader.LoadAsync(plyUrl, scene, (progress: number) => {
          // progress is 0-1
          if (!cancelled) {
            // Could show a progress indicator here
          }
        }, undefined, true);

        if (cancelled) return;

        // Make canvas visible and hide loader
        canvas!.style.visibility = "visible";
        setLoading(false);

        // Handle resize
        const ro = new ResizeObserver(() => {
          if (cancelled) return;
          const r = container!.getBoundingClientRect();
          const dw = r.width * window.devicePixelRatio;
          const dh = r.height * window.devicePixelRatio;
          if (canvas!.width !== dw || canvas!.height !== dh) {
            canvas!.width = dw;
            canvas!.height = dh;
            canvas!.style.width = r.width + "px";
            canvas!.style.height = r.height + "px";
            renderer.setSize(dw, dh);
          }
        });
        ro.observe(container!);

        // Render loop
        function animate() {
          if (cancelled) return;
          controls!.update();
          renderer.render(scene, camera);
          animId = requestAnimationFrame(animate);
        }
        animate();

        return () => {
          ro.disconnect();
        };
      } catch (err: unknown) {
        if (cancelled) return;
        console.error("GSplat viewer error:", err);
        const msg = err instanceof Error ? err.message : "3D 模型加载失败";
        setError(`3D 模型加载失败: ${msg}`);
        setLoading(false);
      }
    }

    const cleanupPromise = initViewer();

    return () => {
      cancelled = true;
      if (animId !== null) cancelAnimationFrame(animId);
      controls?.dispose();
      cleanupPromise.then((cleanup) => {
        if (typeof cleanup === "function") cleanup();
      });
    };
  }, [plyUrl]);

  return (
    <div
      ref={containerRef}
      className="relative w-full min-h-[400px] rounded-xl overflow-hidden bg-[#0a0d14] border border-gray-700/50"
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0"
        style={{ visibility: loading ? "hidden" : "visible", width: "100%", height: "100%" }}
      />

      {loading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 z-10">
          <Loader2 className="w-10 h-10 text-cyan-400 animate-spin" />
          <span className="text-gray-400">加载 3D 模型中...</span>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 z-10">
          <AlertCircle className="w-10 h-10 text-red-400" />
          <span className="text-red-400 text-sm text-center px-4">{error}</span>
        </div>
      )}
    </div>
  );
}
