#!/bin/bash

# 查看 x-reader 服务状态

check_port() {
    local port=$1
    local name=$2
    local pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        echo "$name: 运行中 (端口 $port, PID: $pid)"
    else
        echo "$name: 未运行"
    fi
}

echo "========================================="
echo "  x-reader 服务状态"
echo "========================================="
check_port 8000 "后端"
check_port 5173 "前端"
echo "========================================="
