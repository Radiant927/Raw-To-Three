# RT Pipeline 展示平台 —— 设计文档

> **目的**：把现有的 photos→3D 高斯模型 pipeline 包装成 web 平台。
> 用户上传照片 → 后端触发 pipeline → 实时看进度 → 网页里查看 3D 结果。
>
> **规模**：小规模 demo，仅在本地运行（`localhost`），不上线公网。
> **计算资源**：Pipeline 在远端 服务器跑，本地后端通过 SSH 调用。
> **交付**：先按 Mock API 开发前后端，接入 服务器 由我最后完成。

---

## 1. Pipeline 概览（你需要知道的背景）

现有 pipeline 分 4 步，全部脚本已在 `RT pipeline/scripts/` 下：

| 步骤 | 脚本 | 输入 | 输出 | 耗时 |
|---|---|---|---|---|
| 1. COLMAP SfM | `run_colmap.py` | 一堆 JPG/PNG | `sparse/0/` 相机位姿+稀疏点云 | 5-15 分钟 |
| 2. 2DGS 训练 | `2d-gs/train.py` (外部) | COLMAP 输出 | `point_cloud.ply` (2DGS 格式) | 30-90 分钟（GPU） |
| 3. 去噪 | `denoise.py` | 原始 PLY | `denoised.ply` (清理过) | 1 分钟 |
| 4. 导出 | `convert_to_3dgs.py` / `export_glb.py` | `denoised.ply` | `denoised_3dgs.ply` (SuperSplat可看) / `walls_mesh.glb` (Blender) | 2-3 分钟 |

**一次完整跑：约 40-120 分钟**，取决于照片数量和 GPU 负载。

入口脚本 `run.sh` 已把上面串成一条命令：
```bash
bash run.sh --photos ./photos --output ./output
```

---

## 2. 技术选型建议

| 层 | 选型 | 理由 |
|---|---|---|
| 前端 | **Next.js 14 (App Router) + TypeScript + Tailwind** | 现代化、静态导出方便部署演示 |
| 3D 查看器 | **[gsplat.js](https://github.com/dylanebert/gsplat.js)** 或 iframe 嵌入 [SuperSplat](https://superspl.at/editor) | gsplat.js 更灵活，可自定义 UI |
| 后端 | **FastAPI + Uvicorn**（Python 3.10+） | 与现有 pipeline 一致（Python），WebSocket 原生支持 |
| 任务队列 | 简易：`asyncio.create_task`（单机单任务，本 demo 够用）；进阶：Celery + Redis | Demo 阶段一个用户一次一个任务，不需要复杂队列 |
| 存储 | 文件系统 `~/rt_platform_jobs/{job_id}/`，元数据用 SQLite | 简单，无需数据库服务 |
| 通信 | REST（提交/查询）+ WebSocket（实时进度） | 标准方案 |
| SSH 调用 | **paramiko** 或 **fabric**（Python 库） | 后端通过 SSH 到 服务器 跑 `run.sh` |

**启动方式**：写一个 `start.sh` 同时起前端（`npm run dev`）和后端（`uvicorn main:app --reload`），浏览器打开 `http://localhost:3000` 即可演示。

---

## 3. 页面/模块划分

### 3.1 页面地图

```
/                    首页（Landing + 项目介绍）
/pipeline            Pipeline 原理说明页
/demo                核心功能：上传照片跑 pipeline
  ├─ 上传区
  ├─ 提交后跳转 → /demo/[job_id]
/demo/[job_id]       实时进度页
/result/[job_id]     结果展示页（3D viewer + 下载）
/gallery             历史成果展示（预生成的 demo 模型）
/about               关于/技术栈
```

### 3.2 板块详细设计

#### 板块 A：首页 (`/`)

**目的**：吸引访客、快速展示能力。

**内容**：
- Hero 区：一句话标语 + 一个 **旋转的 3D 高斯模型**（用 gsplat.js 加载预生成的图书馆 PLY）
- "看看它是怎么做到的" → 跳转 `/pipeline`
- "试一下" → 跳转 `/demo`
- 3 张成果对比卡片：原图 → COLMAP 点云 → 最终 3DGS 模型

#### 板块 B：Pipeline 原理页 (`/pipeline`)

**目的**：给访客科普整套流程，为下一步"自己跑一遍"做铺垫。

**内容**：4 张卡片，纵向排列。每张卡片：

```
┌────────────────────────────────────────┐
│ Step 1 · COLMAP SfM                    │
│ ─────────────────────────                │
│ [左图: 原始照片墙]  [右图: 稀疏点云可视化]│
│                                          │
│ 说明: 从多张照片估计相机位姿+稀疏点云    │
│ 输入: 20-100张 JPG/PNG                   │
│ 耗时: 5-15 分钟                           │
└────────────────────────────────────────┘
```

Step 4 卡片里嵌入一个**去噪前后对比滑块**（`react-compare-image`），展示 `opacity_min=0.09` 的效果差异。

#### 板块 C：Demo 核心（3 个子页面）

**C1. 上传页 `/demo`**

```
┌─────────────────────────────────────────┐
│  上传你的照片                            │
│  ─────────────                          │
│  [拖拽上传区 / 点击选择]                  │
│  已选: 45 张 (128 MB)                    │
│                                          │
│  ⚙️ 参数（默认即可，可展开调节）          │
│    ▷ 去噪强度: opacity_min = 0.09  [滑块]│
│    ▷ 训练迭代: 30000              [固定] │
│    ▷ 质量:    high                [选择] │
│                                          │
│  [ 开始处理 →  预计 60 分钟 ]           │
└─────────────────────────────────────────┘
```

**校验**：
- 图片数量 20-100 张
- 单张 ≤ 10MB
- 总大小 ≤ 500MB
- 格式：JPG/PNG

**提交后**：POST `/api/jobs` → 后端返回 `job_id` → 前端跳转 `/demo/{job_id}`

**C2. 进度页 `/demo/[job_id]`**

```
┌─────────────────────────────────────────┐
│  任务 #a3f2  ⏱ 已运行 12:35              │
│  ─────────────                          │
│                                          │
│  ✅ 1. 照片上传          (45 张, 128MB)   │
│  ✅ 2. COLMAP SfM        (8 分钟)         │
│  🔵 3. 2DGS 训练         67% ▓▓▓▓░       │
│     iter 20000/30000 · loss 0.023        │
│  ⏳ 4. 去噪                              │
│  ⏳ 5. 导出                              │
│                                          │
│  ┌── 实时日志 ────────────────────┐      │
│  │ [17:23:45] Training iter 20000  │      │
│  │ [17:23:44] Loss: 0.0234         │      │
│  │ ...                             │      │
│  └─────────────────────────────────┘     │
└─────────────────────────────────────────┘
```

- WebSocket 实时更新每步状态和百分比
- 日志区可滚动，最新在下
- 完成后自动跳转 `/result/{job_id}` 或按钮引导

**C3. 结果页 `/result/[job_id]`**

```
┌─────────────────────────────────────────┐
│  完成 ✨  总耗时: 58:23                    │
│  ─────────────                          │
│                                          │
│  ┌───────── 3D Viewer ─────────┐        │
│  │                             │        │
│  │  (gsplat.js 渲染 PLY)       │        │
│  │  鼠标拖拽旋转/滚轮缩放         │        │
│  └─────────────────────────────┘        │
│                                          │
│  📥 下载:                                │
│  • denoised_3dgs.ply  (39 MB) — SuperSplat│
│  • walls_mesh.glb     (12 MB) — Blender  │
│  • denoised.ply       (39 MB) — 原始2DGS │
│                                          │
│  📊 统计: 163,420 Gaussians · 45 张照片   │
└─────────────────────────────────────────┘
```

#### 板块 D：Gallery `/gallery`

- 展示已经跑好的 demo 项目（图书馆等）
- 每个 case 缩略图 + 点击进入 3D viewer
- 用来兜底：如果 服务器 关机时也有内容可看

#### 板块 E：About `/about`

- 技术栈：COLMAP + 2D Gaussian Splatting + Open3D
- 团队/致谢
- GitHub 链接（如果开源）

---

## 4. API 契约（后端接口规范）

**Base URL**: `http://localhost:8000`

### 4.1 REST 接口

#### `POST /api/jobs` — 创建任务

请求（multipart/form-data）:
```
photos: File[]           # 20-100 张照片
opacity_min: float = 0.09
iterations: int = 30000
quality: "high" | "medium" = "high"
```

响应 200:
```json
{
  "job_id": "a3f2b7c1",
  "status": "queued",
  "created_at": "2026-07-30T12:34:56Z",
  "estimated_seconds": 3600
}
```

错误 400:
```json
{ "error": "photos_count_invalid", "message": "需要 20-100 张照片" }
```

#### `GET /api/jobs/{job_id}` — 查询状态

响应:
```json
{
  "job_id": "a3f2b7c1",
  "status": "running",   // queued | running | done | failed
  "current_step": "train",  // upload | colmap | train | denoise | export | done
  "steps": [
    { "name": "upload",  "status": "done",    "progress": 100, "duration_sec": 12 },
    { "name": "colmap",  "status": "done",    "progress": 100, "duration_sec": 480 },
    { "name": "train",   "status": "running", "progress": 67, "duration_sec": null },
    { "name": "denoise", "status": "pending", "progress": 0,  "duration_sec": null },
    { "name": "export",  "status": "pending", "progress": 0,  "duration_sec": null }
  ],
  "created_at": "2026-07-30T12:34:56Z",
  "started_at": "2026-07-30T12:34:58Z",
  "finished_at": null,
  "error": null
}
```

#### `GET /api/jobs/{job_id}/logs?since=<timestamp>` — 拉取增量日志

响应:
```json
{
  "logs": [
    { "ts": "2026-07-30T13:20:11Z", "level": "info", "line": "Training iter 20000/30000" }
  ],
  "cursor": "2026-07-30T13:20:11Z"
}
```

#### `GET /api/jobs/{job_id}/result` — 获取产物列表

响应:
```json
{
  "job_id": "a3f2b7c1",
  "artifacts": [
    { "name": "denoised_3dgs.ply", "size_bytes": 40529691, "url": "/files/a3f2b7c1/denoised_3dgs.ply", "kind": "3dgs_ply" },
    { "name": "walls_mesh.glb",    "size_bytes": 12000000, "url": "/files/a3f2b7c1/walls_mesh.glb",    "kind": "glb" },
    { "name": "denoised.ply",      "size_bytes": 39875988, "url": "/files/a3f2b7c1/denoised.ply",      "kind": "2dgs_ply" }
  ],
  "stats": {
    "num_gaussians": 163420,
    "num_photos": 45,
    "total_duration_sec": 3503
  }
}
```

#### `GET /files/{job_id}/{filename}` — 下载文件（静态服务）

直接返回文件流。

#### `GET /api/gallery` — Gallery 列表

响应:
```json
{
  "items": [
    {
      "id": "library",
      "title": "图书馆",
      "thumbnail_url": "/gallery/library/thumb.jpg",
      "ply_url": "/gallery/library/denoised_3dgs.ply",
      "num_gaussians": 163420,
      "num_photos": 45
    }
  ]
}
```

### 4.2 WebSocket 接口

#### `WS /ws/jobs/{job_id}` — 实时进度推送

连接后服务端推送事件，格式：
```json
{ "type": "step_update", "step": "train", "progress": 68, "message": "iter 20500/30000" }
{ "type": "log",         "level": "info", "line": "Loss: 0.0231" }
{ "type": "status",      "status": "done" }
{ "type": "error",       "message": "COLMAP failed: not enough matches" }
```

前端订阅这个 WS 就够更新 UI。

---

## 5. Mock API（可以先脱离 服务器 开发）

**核心思路**：后端提供一个 `--mock` 模式，不真调 服务器，纯本地假数据，5 分钟"跑完"整个流程。这样同学能独立完成前后端联调。

Mock 实现建议：
- `POST /api/jobs`：接收上传，存到本地文件夹，返回 job_id
- Mock 任务：起个 asyncio 定时器，30 秒推进一个 step（upload → colmap → train → denoise → export → done）
- 完成后返回预置的 `denoised_3dgs.ply`（我会提供）作为"结果"
- 提供 `mock_data/` 目录，含有：`library_3dgs.ply`, `library_thumb.jpg`, 假的 log 文件

启动命令：
```bash
uvicorn main:app --reload            # 真实模式（需 服务器）
uvicorn main:app --reload --mock     # Mock 模式（本地假跑）
```

我最后会实现"真实模式"的 服务器 调用逻辑，同学只需保证 API 契约不变。

---

## 6. 目录结构建议

```
RT pipeline/
├── scripts/           (现有 pipeline 脚本，不动)
├── run.sh             (现有入口，不动)
├── examples/          (预生成的 demo PLY, 用于 Gallery)
│   └── library/
│       ├── denoised_3dgs.ply
│       └── thumb.jpg
└── web/                       ← 新增
    ├── frontend/              Next.js
    │   ├── app/
    │   │   ├── page.tsx
    │   │   ├── pipeline/page.tsx
    │   │   ├── demo/page.tsx
    │   │   ├── demo/[jobId]/page.tsx
    │   │   ├── result/[jobId]/page.tsx
    │   │   ├── gallery/page.tsx
    │   │   └── about/page.tsx
    │   ├── components/
    │   │   ├── GSplatViewer.tsx     3D 查看器封装
    │   │   ├── UploadZone.tsx       拖拽上传
    │   │   ├── ProgressStepper.tsx  步骤进度
    │   │   ├── LogPanel.tsx         滚动日志
    │   │   └── CompareSlider.tsx    去噪前后对比
    │   ├── lib/
    │   │   └── api.ts               API 客户端
    │   └── package.json
    ├── backend/               FastAPI
    │   ├── main.py              FastAPI app
    │   ├── models.py            SQLite / Pydantic 模型
    │   ├── job_manager.py       任务生命周期
    │   ├── pipeline_runner.py   真调 服务器 (我来写)
    │   ├── mock_runner.py       Mock 模式
    │   ├── requirements.txt
    │   └── mock_data/           假数据
    ├── docs/
    │   ├── PLATFORM_DESIGN.md   本文档
    │   └── API.md               API 详细规范
    └── start.sh                 一键启动脚本
```

---

## 7. 开发路线（建议给同学的执行顺序）

**Phase 1 — 前端骨架 + Mock 后端**（2-3 天）
1. 搭 Next.js + Tailwind + 布局
2. 实现 6 个页面，UI 完成度先到 80%
3. 用 Mock 后端跑通一整条：上传 → 进度 → 结果 3D 展示
4. 交付：能在本地 `start.sh` 跑通全流程，全用假数据

**Phase 2 — 3D Viewer 精修**（1 天）
1. 集成 `gsplat.js`，加载 PLY 显示
2. 相机控制、加载进度、错误处理

**Phase 3 — 我接入 服务器**（0.5 天，我做）
- 实现 `pipeline_runner.py`：scp 照片上去 → ssh 跑 `run.sh` → 解析 stdout → 更新 job 状态 → scp 拉产物回来
- 需要 `run.sh` 加进度输出（我改）：`echo "[PROGRESS] step=train pct=67"`

**Phase 4 — 联调 + 演示打磨**（1 天）
- 真跑一遍图书馆的照片，确认所有环节
- 加错误页、404、加载态
- 首页 Gallery 内容准备

**总工作量：约 4-5 天**

---

## 8. 交付验收标准

- [ ] `bash web/start.sh` 一条命令启动前后端
- [ ] 浏览器打开 `localhost:3000` 能看到首页
- [ ] 6 个页面全部可访问，无 404
- [ ] Mock 模式下能完整走一遍：上传 → 进度更新 → 结果 3D 展示 → 下载
- [ ] `/gallery` 至少显示 1 个 demo 模型（图书馆），可 3D 查看
- [ ] API 契约与本文档一致（我会用真 backend 替换 mock，接口不变）
- [ ] README 说明如何切换 mock/真实模式

---

## 9. 常见问题

**Q: 前端怎么加载 40MB 的 PLY？会卡吗？**
A: `gsplat.js` 支持流式加载，40MB 在本地网络是几秒内的事。可以加个加载进度条。

**Q: 上传照片时怎么显示进度？**
A: 用 `fetch` + `ReadableStream` 或 `axios` 的 `onUploadProgress`。

**Q: WebSocket 断开怎么办？**
A: 前端 5 秒重连一次；也可以退化到轮询 `GET /api/jobs/{id}` 每 2 秒一次。

**Q: 同时多个任务？**
A: Demo 阶段 **只支持一个任务** 排队。第二个提交时返回 `409 Conflict`，提示"当前有任务进行中"。

**Q: Mock 数据从哪来？**
A: 我会提供 `mock_data/`：一个 PLY + 一段日志 + 一张缩略图。放到 `backend/mock_data/` 即可。

---

## 10. 联系与协作

- 前后端 API 契约以 `docs/API.md` 为准（本文档节选，详细版见 API.md，我会补充）
- 遇到不清楚的字段/流程，直接问我
- Phase 3 服务器 接入我来做，你保证 Mock 模式跑通即可

---

**祝顺利！**
