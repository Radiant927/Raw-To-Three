# Raw-To-Three

从手机 / 无人机照片，重建建筑与小物体 3D 高斯模型（3DGS）的一站式流程。

## 流程

```
照片 → COLMAP 位姿解算(SIMPLE_RADIAL) → 图片去畸变(k1→0, PINHOLE)
  → 纯颜色 2DGS 训练 → 去噪(opacity<0.09) → 导出(3DGS / GLB)
```

关键点：2DGS 默认假设相机无畸变，COLMAP 解出的 k1 会被丢弃导致像素错位，
因此训练前必须在数据端做去畸变、把相机改成 PINHOLE——这是小物体 / 近拍场景能重建成功的前提。

## 目录

```
docs/                     说明文档（环境搭建 / 流程 / 拍摄指南 / 平台设计）
scripts/                  核心 pipeline 脚本
  run_colmap.py           COLMAP SfM（含注册率检查）
  pipeline3/undistort_images.py   图片去畸变（保留原文件名）
  pipeline3/patch_cameras.py      SIMPLE_RADIAL → PINHOLE
  denoise.py              去噪（opacity 预过滤 + 统计/半径离群去除）
  convert_to_3dgs.py      2DGS → 3DGS（Supersplat 可查看）
  export_glb.py           导出 GLB（必须 --z_min 1.0，否则泊松 blob 吞目标）
web/                      展示平台：上传照片 → 实时进度 → 3D 结果查看 / 下载
  frontend/               Next.js 前端（端口 3000）
  backend/                FastAPI 后端（端口 8000，当前 Mock 模式）
examples/                 示例结果模型
```

## 快速开始

### 跑一遍 pipeline（脚本级）

```bash
python scripts/run_colmap.py --image_path <照片目录> --output_path out/colmap
python scripts/pipeline3/undistort_images.py --colmap_dir out/colmap --output_dir out/undistort
python scripts/pipeline3/patch_cameras.py --input out/colmap/sparse/0/cameras.bin --output out/train/cameras.bin --cam_updates out/undistort/cam_updates.json
# 然后 2DGS 训练，输出 point_cloud.ply
python scripts/denoise.py --input point_cloud.ply --output denoised.ply --opacity_min 0.09
python scripts/convert_to_3dgs.py --input denoised.ply --output denoised_3dgs.ply
python scripts/export_glb.py --input denoised.ply --output walls_mesh.glb --z_min 1.0
```

### 启动展示平台（Mock 模式）

```bash
cd web/backend && pip install -r requirements.txt && python main.py --mock
cd web/frontend && npm install && npm run dev
# 浏览器打开 http://localhost:3000
```

## 示例

图书馆场景 3DGS 模型，约 16.3 万高斯（7 月 30 日结果）：

| 正面 | 侧面 |
|---|---|
| ![front](examples/front_view.png) | ![side](examples/side_view.png) |

模型文件：`examples/denoised_3dgs.ply`（3DGS 格式，可拖入 [superspl.at](https://superspl.at) 查看）。

## 说明

- 深度监督（DA3 深度）暂未接入：深度估计的尺度必须与 COLMAP 对齐，否则模型会炸（16 万 → 600 万高斯、拖 45 米）。尺度对齐解决后再启用。
- 平台当前为 Mock 模式（模拟五步流程、约 50 秒出占位模型）；真 pipeline 通过 `pipeline_runner.py` 用 SSH 调服务器执行（待接入）。
