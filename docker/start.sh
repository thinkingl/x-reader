#!/bin/bash
set -e

CONTAINER_NAME="x-reader"
IMAGE="172.16.240.100:5000/x-reader-cuda:latest"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Network cache servers
NEXUS_HOST="172.16.240.100"
NEXUS_PORT="8081"

# 检查是否需要 sudo
if ! docker info &>/dev/null; then
  SUDO="sudo"
else
  SUDO=""
fi

# Auto-detect internal cache availability
USE_CACHE="false"
echo "Checking internal cache services..."
if curl -s --max-time 3 "http://${NEXUS_HOST}:${NEXUS_PORT}/service/rest/v1/status" > /dev/null 2>&1; then
  USE_CACHE="true"
  echo "  Nexus cache: AVAILABLE (using internal proxies)"
else
  echo "  Nexus cache: not reachable (using direct network)"
fi

# Build image with cache detection
echo "Building image..."
if [ "$USE_CACHE" = "true" ]; then
  $SUDO docker build --network=host \
    --build-arg USE_INTERNAL_CACHE=true \
    -t "$IMAGE" -f "$PROJECT_DIR/Dockerfile.cuda" "$PROJECT_DIR"
else
  $SUDO docker build --network=host \
    --build-arg USE_INTERNAL_CACHE=false \
    -t "$IMAGE" -f "$PROJECT_DIR/Dockerfile.cuda" "$PROJECT_DIR"
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
