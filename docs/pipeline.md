# Pipeline详解

从原始照片到干净3D高斯模型的完整流程。

## 总览

```
原始照片 → COLMAP(SfM) → 2DGS训练 → 去噪 → 3DGS模型
  ↓           ↓              ↓         ↓        ↓
photos/    sparse/       train.py   denoise   clean.ply
```

## Step 1: 拍摄照片

- 环绕建筑拍摄50-200张照片
- 相邻照片重叠率>60%
- 覆盖所有立面，仰拍捕捉屋顶
- 避免运动模糊、过曝

## Step 2: COLMAP 稀疏重建

```bash
colmap automatic_reconstructor \
  --workspace_path ./data \
  --image_path ./photos \
  --quality high
```

输出：
- `data/sparse/0/cameras.bin` — 相机内参
- `data/sparse/0/images.bin` — 相机位姿
- `data/sparse/0/points3D.bin` — 稀疏点云

## Step 3: 2DGS 训练

使用 [2d-gaussian-splatting](https://github.com/hbb1/2d-gaussian-splatting)：

```bash
git clone https://github.com/hbb1/2d-gaussian-splatting.git 2d-gs
cd 2d-gs
python train.py \
  --source_path ../data \
  --model_path output/run1
```

输出：
- `output/run1/point_cloud/iteration_30000/point_cloud.ply` — 原始2DGS模型

## Step 4: 去噪

```bash
cd ../RT-pipeline
python scripts/denoise.py \
  --input ../2d-gs/output/run1/point_cloud/iteration_30000/point_cloud.ply \
  --output output/denoised.ply
```

使用统计离群点移除 + 半径离群点移除，清除漂浮噪声，保留建筑结构。

参数：
- `--nb_neighbors 30` — 统计滤波邻域数
- `--std_ratio 1.5` — 标准差阈值
- `--radius 0.05` — 半径滤波搜索半径(米)
- `--min_neighbors 10` — 半径内最少邻域数

## Step 5: 可视化

用任意3DGS查看器打开`output/denoised.ply`：

- [SuperSplat](https://superspl.at) — 浏览器内查看
- [gsplat.js](https://github.com/huggingface/gsplat.js) — Web查看器
- [SIBR](https://github.com/graphdeco-inria/gaussian-splatting) — 桌面查看器

## 可选：Blender协作

导出建筑结构供Blender建模：

```bash
python scripts/export_for_blender.py \
  --input output/denoised.ply \
  --output output/walls.ply \
  --z_min 1.0
```

## 可选：结构补全

如有缺失结构（屋顶等），通过以下流程补全：
1. 在Blender中建模缺失结构 → 导出PLY
2. `completion/mesh_to_gaussians.py` → 网格采样为Gaussians
3. `completion/frozen_finetune.py` → 冻结原有Gaussians，微调新增的

详见`docs/completion.md`。

## 数据要求

| 参数 | 建议值 |
|------|--------|
| 照片数量 | 50-200张 |
| 照片分辨率 | 任意（推荐>2MP） |
| 重叠率 | >60% |
| 拍摄距离 | 5-20米 |
| 场景尺寸 | 1-50米 |

## 硬件要求

| 步骤 | CPU/GPU | 典型耗时(100张) |
|------|---------|----------------|
| COLMAP | CPU | 30-60分钟 |
| 2DGS训练 | GPU(≥8GB VRAM) | 1-3小时 |
| 去噪 | CPU | <10秒 |
