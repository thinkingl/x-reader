#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PATH="$SCRIPT_DIR/../.venv"
LOG_DIR="$SCRIPT_DIR/logs"

mkdir -p "$LOG_DIR"
mkdir -p "$SCRIPT_DIR/backend/data/books"
mkdir -p "$SCRIPT_DIR/backend/data/audio"

# 检查虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    echo "错误: 虚拟环境不存在: $VENV_PATH"
    exit 1
fi

# 检查前端依赖
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo "安装前端依赖..."
    cd "$SCRIPT_DIR/frontend" && npm install
fi

cleanup() {
    echo ""
    echo "停止服务..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "已停止"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 启动后端
echo "启动后端 (端口 8000)..."
cd "$SCRIPT_DIR/backend"
source "$VENV_PATH/bin/activate"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee "$LOG_DIR/backend.log" &
BACKEND_PID=$!
deactivate

# 等待后端启动
echo "等待后端启动..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/config > /dev/null 2>&1; then
        echo "后端已就绪"
        break
    fi
    sleep 1
done

# 启动前端
echo "启动前端 (端口 5173)..."
cd "$SCRIPT_DIR/frontend"
npm run dev 2>&1 | tee "$LOG_DIR/frontend.log" &
FRONTEND_PID=$!

echo ""
echo "========================================="
echo "  x-reader 服务已启动"
echo "========================================="
echo "  前端: http://localhost:5173"
echo "  后端: http://localhost:8000"
echo "  日志: $LOG_DIR/"
echo "========================================="
echo "按 Ctrl+C 停止服务"
echo ""

wait $BACKEND_PID $FRONTEND_PID
