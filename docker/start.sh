#!/bin/bash
set -e

CONTAINER_NAME="x-reader"
IMAGE="172.16.240.100:5000/x-reader-cuda:latest"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 检查是否需要 sudo
if ! docker info &>/dev/null; then
  echo "需要 sudo 权限运行 docker"
  SUDO="sudo"
else
  SUDO=""
fi

echo "Stopping existing container..."
$SUDO docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo "Starting $CONTAINER_NAME..."
$SUDO docker run -d --name "$CONTAINER_NAME" \
  --gpus all \
  -p 5173:5173 -p 8080:8000 \
  -v "$PROJECT_DIR/data:/app/backend/data" \
  -v "$PROJECT_DIR/models:/app/models" \
  -v "$PROJECT_DIR/docker/entrypoint.sh:/entrypoint.sh:ro" \
  "$IMAGE"

echo "Following logs (Ctrl+C to detach, container keeps running)..."
sleep 2
$SUDO docker logs -f "$CONTAINER_NAME"
