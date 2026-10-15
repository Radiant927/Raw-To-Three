# Raw-To-Three

从手机 / 无人机拍摄的**照片或视频**，重建建筑与小物体的干净 3D 高斯（3DGS）模型。

## 流程

```
照片 / 视频(抽帧)
  → COLMAP 位姿解算（exhaustive/sequential；注册不足 → SuperPoint+SuperGlue+hloc 兜底）
  → splatfacto 训练（nerfstudio，dataparser: colmap）
  → ns-export 导出 splat.ply（nerfstudio 缩放坐标）
  → 坐标转回 COLMAP 米制
  → 去噪：离群点去除 → 自动半径裁剪(+投影投票) → DBSCAN 保留主簇
  → 导出标准 3DGS ply（superspl.at 查看定稿）
```

关键点：

- 训练用 nerfstudio 的 **splatfacto**（3DGS）。COLMAP 匹配用 `exhaustive`（全量，稳）或 `sequential`（绕圈拍，快）；SIFT 注册不足/模型被切碎时自动 fallback 到 SuperGlue + hloc。
- 导出在 **nerfstudio 缩放坐标系**，后处理必须先按 `xyz_colmap = R.T @ (xyz_ns / scale − t)` 转回 COLMAP 米制，再做任何几何操作。
- 去噪**默认不 mask**，见下。

## 去噪决策树（核心，默认不 mask）

```
① 定位 + 切半径（第一招）
   中心 = 小高斯密度峰（勿用 median，会被远背景带偏→主体被削）
   半径出 2~3 档供 superspl.at 挑选
      ├─ 效果 OK ───────────────→ 定稿
      └─ 效果不好：先判病，别乱上 mask
         ├─ 病1 主体被削(去太多) → 调中心 / 放宽半径（几何问题，上 mask 无用）
         └─ 病2 背景残留(主体完整) → ② 语义 mask 投票
② 语义 mask 投票（叠在①选好的半径基底上）
   u2netp 显著对象分割（逐帧自校验剔坏帧）/ SAM / 用户手工 mask
   投票阈值 = 取舍旋钮（0.25 温和 / 0.35 默认 / 0.50 更强去墙）
✗ 反例：用单帧深度(DA3)自动生成 mask —— 环绕近围合场景帧间跳变、投票近似无效，只能当弱先验
```

## 目录

```
docs/                     说明文档（环境搭建 / 流程 / 拍摄指南 / 平台设计）
scripts/                  管线脚本
  run_colmap.py           COLMAP SfM（含注册率检查）
  pipeline3/undistort_images.py   图片去畸变（可选，保留原文件名）
  pipeline3/patch_cameras.py      SIMPLE_RADIAL → PINHOLE
  denoise.py              去噪：opacity 预过滤 + 统计/半径离群点去除
  convert_to_3dgs.py      导出标准 3DGS ply（superspl.at 可查看）
  export_glb.py           导出 GLB
web/                      展示平台：上传照片 → 实时进度 → 3D 结果查看 / 下载
  start.sh / start.bat    一键启动（演示 / Mock 模式）
  frontend/               Next.js 前端（端口 3000）
  backend/                FastAPI 后端（端口 8010）
  backend/mock_data/      演示用占位模型
examples/                 示例结果模型
```

## 快速开始

### 一键启动演示（推荐）

```bash
bash web/start.sh
```

Windows 下直接双击 `web\start.bat`。

脚本会自动安装前后端依赖并启动服务，然后浏览器打开 http://localhost:3000 ：
上传 20 张以上 JPG/PNG 照片 → 实时进度 → 查看结果模型。
演示模式用 `mock_data/` 里的占位模型，**不需要 GPU / COLMAP**，任何装了 Python 3 和 Node.js 的机器都能跑（首次安装依赖需要联网）。

### 手动启动（演示 / Mock 模式）

```bash
# 后端（端口 8010）
cd web/backend && pip install -r requirements.txt && python main.py --mock

# 前端（端口 3000）
cd web/frontend && npm install && npm run dev
# 打开 http://localhost:3000
```

### 跑真实重建（需要 GPU 环境）

展示平台的真实模式会让后端在本机执行重建脚本 `run.sh`（COLMAP → splatfacto → 去噪 → 导出），因此需要一台装好 COLMAP / nerfstudio 的机器（环境搭建见 `docs/setup.md`）：

```bash
export RT_PIPELINE_DIR=/path/to/huolong_run   # 该目录下需有 run.sh
cd web/backend && python main.py               # 不带 --mock，即真实模式
```

前端同样 `npm run dev` 打开 http://localhost:3000 。真实重建依赖本机 GPU，无法在普通笔记本上克隆即跑。

### 跑一遍 pipeline（脚本级）

```bash
# 1. COLMAP 位姿（注册不足会在 run.sh 里自动走 SuperGlue 兜底）
python scripts/run_colmap.py --image_path <照片目录> --output_path out/colmap --quality high --matcher exhaustive

# 2. splatfacto 训练（nerfstudio）
ns-train splatfacto --output-dir out --experiment-name trainrun \
  --max-num-iterations 30000 colmap --data out/ns_data

# 3. 导出
ns-export gaussian-splat --load-config out/trainrun/splatfacto/<时间戳>/config.yml --output-dir out/export

# 4. 去噪
python scripts/denoise.py --input out/export/splat.ply --output out/denoised.ply \
  --opacity_min 0.09 --nb_neighbors 30 --std_ratio 1.5 --radius 0.05 --min_neighbors 10

# 5. 导出标准 3DGS（superspl.at 可查看）
python scripts/convert_to_3dgs.py --input out/denoised.ply --output out/denoised_3dgs.ply
```

## 示例

图书馆场景 3DGS 模型，约 16.3 万高斯（7 月 30 日结果）：

| 正面 | 侧面 |
|---|---|
| ![front](examples/front_view.png) | ![side](examples/side_view.png) |

模型文件：`examples/denoised_3dgs.ply`（3DGS 格式，可拖入 [superspl.at](https://superspl.at) 查看）。

## 说明

- 深度监督（DA3 深度）暂未接入：深度估计的尺度必须与 COLMAP 对齐，否则模型会炸（16 万 → 600 万高斯、拖 45 米）；DA3 深度也不能用来做自动 mask（见去噪决策树反例）。
- 展示平台默认走 **Mock 模式**（用 `web/backend/mock_data/` 的占位模型，便于无 GPU 演示）；真实重建通过环境变量 `RT_PIPELINE_DIR` 指向本机含 `run.sh` 的目录，由 `web/backend/local_runner.py` 本地执行。
- 完整的一键编排（COLMAP → SuperGlue 兜底 → 去畸变 → splatfacto → 导出 → 三步去噪）在部署用的 `run.sh` 里；本仓库 `scripts/` 提供其中的 COLMAP / 去畸变 / 去噪 / 导出步骤脚本。
