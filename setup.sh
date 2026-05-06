#!/bin/bash
# x-reader 一键部署脚本
# 用法: ./setup.sh [install_dir]
# 默认安装到当前目录

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${1:-$SCRIPT_DIR}"

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $1"; }

# ─── 基础检查 ───
info "检查环境..."
command -v python3 >/dev/null 2>&1 || { echo "错误: 需要 python3"; exit 1; }
command -v node    >/dev/null 2>&1 || { echo "错误: 需要 node";  exit 1; }
command -v npm     >/dev/null 2>&1 || { echo "错误: 需要 npm";   exit 1; }
ok "python3: $(python3 --version)"
ok "node:    $(node --version)"
ok "npm:     $(npm --version)"

# ─── 创建目录结构 ───
info "创建目录结构..."
mkdir -p "$INSTALL_DIR/data/books"
mkdir -p "$INSTALL_DIR/data/audio"
mkdir -p "$INSTALL_DIR/data/reference"
mkdir -p "$INSTALL_DIR/logs"
ok "目录结构已创建"

# ─── 创建 Python 虚拟环境 ───
VENV_PATH="$INSTALL_DIR/.venv"
if [ ! -d "$VENV_PATH" ]; then
    info "创建 Python 虚拟环境: $VENV_PATH"
    python3 -m venv "$VENV_PATH"
    ok "虚拟环境已创建"
else
    ok "虚拟环境已存在，跳过创建"
fi

# ─── 安装 Python 依赖 ───
info "安装 Python 依赖..."
source "$VENV_PATH/bin/activate"
pip install --upgrade pip -q -i https://mirrors.aliyun.com/pypi/simple/ 2>/dev/null
pip install -r "$SCRIPT_DIR/backend/requirements.txt" -i https://mirrors.aliyun.com/pypi/simple/ 2>&1 | tail -5
deactivate 2>/dev/null || true
ok "Python 依赖安装完成"

# ─── 安装前端依赖 ───
info "安装前端依赖..."
cd "$SCRIPT_DIR/frontend"
npm install --registry=https://registry.npmmirror.com --silent
ok "前端依赖安装完成"
cd "$SCRIPT_DIR"

# ─── 下载模型（如果不存在）───
if [ ! -d "$SCRIPT_DIR/models/OmniVoice" ] || [ ! -f "$SCRIPT_DIR/models/OmniVoice/config.json" ]; then
    echo ""
    info "模型文件不存在，请手动下载模型到 $SCRIPT_DIR/models/"
    info "  - OmniVoice  TTS 模型 -> models/OmniVoice/"
    info "  - whisper  ASR 模型  -> models/whisper-large-v3-turbo/"
else
    ok "模型文件已就绪"
fi

# ─── 启动服务 ───
echo ""
echo "========================================="
echo "  启动 x-reader 服务"
echo "========================================="

cleanup() {
    echo ""
    info "停止服务..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    ok "已停止"
    exit 0
}
trap cleanup SIGINT SIGTERM

# 启动后端
info "启动后端 (端口 8000)..."
cd "$SCRIPT_DIR/backend"
source "$VENV_PATH/bin/activate"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee "$SCRIPT_DIR/logs/backend.log" &
BACKEND_PID=$!

# 等待后端就绪
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/api/config > /dev/null 2>&1; then
        ok "后端已就绪"
        break
    fi
    sleep 1
done

# 启动前端
info "启动前端 (端口 5173)..."
cd "$SCRIPT_DIR/frontend"
npm run dev 2>&1 | tee "$SCRIPT_DIR/logs/frontend.log" &
FRONTEND_PID=$!

echo ""
echo "========================================="
echo "  x-reader 服务已启动"
echo "========================================="
echo "  前端: http://localhost:5173"
echo "  后端: http://localhost:8000"
echo "  日志: $SCRIPT_DIR/logs/"
echo "========================================="
echo "  按 Ctrl+C 停止"
echo ""

wait $BACKEND_PID $FRONTEND_PID
