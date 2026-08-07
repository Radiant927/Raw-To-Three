# 环境配置

## 依赖

### COLMAP

```bash
# Ubuntu / Debian
sudo apt install colmap

# macOS
brew install colmap

# Windows — 从GitHub下载预编译版本
# https://github.com/colmap/colmap/releases
```

### Python环境

```bash
# 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# 安装依赖
pip install numpy open3d
```

### 2DGS训练框架

```bash
git clone https://github.com/hbb1/2d-gaussian-splatting.git 2d-gs
cd 2d-gs
pip install -r requirements.txt
```

2DGS需要CUDA toolkit和PyTorch with CUDA。参考其README配置。

### 去噪与后处理

```bash
pip install numpy open3d argparse
```

## 验证安装

```bash
# 测试COLMAP
colmap --help

# 测试去噪脚本
python scripts/denoise.py --help

# 测试Blender导出
python scripts/export_for_blender.py --help
```
