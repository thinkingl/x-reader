#!/bin/bash

# 停止 x-reader 服务

BACKEND_PORT=8000
FRONTEND_PORT=5173

stop_port() {
    local port=$1
    local name=$2
    local pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null && echo "已停止 $name (PID: $pid)" || echo "停止 $name 失败"
    else
        echo "$name 未运行"
    fi
}

stop_port $BACKEND_PORT "后端"
stop_port $FRONTEND_PORT "前端"
