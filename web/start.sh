#!/usr/bin/env bash
# Raw-To-Three 展示平台一键启动（演示 / Mock 模式）
# 用法：bash start.sh   然后浏览器打开 http://localhost:3000
# 依赖：Python 3、Node.js。首次会自动安装前后端依赖。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8010}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

PYTHON="$(command -v python3 || command -v python || true)"
[ -n "$PYTHON" ] || { echo "[ERROR] 未找到 Python 3"; exit 1; }
command -v node >/dev/null || { echo "[ERROR] 未找到 Node.js"; exit 1; }

echo "[1/3] 安装后端依赖..."
"$PYTHON" -m pip install -q -r "$HERE/backend/requirements.txt"

echo "[2/3] 安装前端依赖..."
(cd "$HERE/frontend" && npm install --silent)

echo "[3/3] 启动服务..."
# 后端：Mock 模式（用 mock_data 里的占位模型，不需要 GPU / COLMAP）
(cd "$HERE/backend" && "$PYTHON" main.py --mock --port "$BACKEND_PORT") &
BACKEND_PID=$!

sleep 3

# 前端
(cd "$HERE/frontend" && NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT" npm run dev) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' INT TERM

echo ""
echo "========================================"
echo "  前端:  http://localhost:$FRONTEND_PORT"
echo "  后端:  http://localhost:$BACKEND_PORT   （API 文档 /docs）"
echo "  演示说明: 上传 20 张以上 JPG/PNG，走完流程会返回占位模型"
echo "  Ctrl+C 停止全部服务"
echo "========================================"
wait
