#!/bin/bash
set -e

echo "Starting x-reader services..."

# Install torch and omnivoice if not already installed
if ! python3 -c "import torch" 2>/dev/null; then
    echo "Installing torch and omnivoice (this may take a while)..."
    pip3 install torch torchaudio omnivoice
fi

# Ensure react-refresh is installed (needed by @vitejs/plugin-react v6)
if [ ! -d "/app/frontend/node_modules/react-refresh" ]; then
    echo "Installing react-refresh..."
    npm install --prefix /app/frontend react-refresh --save 2>&1
    rm -rf /app/frontend/node_modules/.vite
fi

# Check model files
if [ ! -f "/app/models/OmniVoice/model.safetensors" ]; then
    if [ "$ALLOW_MODEL_DOWNLOAD" = "true" ] || [ "$ALLOW_MODEL_DOWNLOAD" = "1" ]; then
        echo "Downloading OmniVoice model..."
        python3 -c "
from omnivoice import OmniVoice
import torch
OmniVoice.from_pretrained('k2-fsa/OmniVoice', device_map='cpu', dtype=torch.float32)
"
    else
        echo "ERROR: OmniVoice model not found at /app/models/OmniVoice/model.safetensors"
        echo "Set ALLOW_MODEL_DOWNLOAD=true to download, or mount the models directory."
        exit 1
    fi
else
    echo "OmniVoice model found."
fi

# Start backend (auto-restart on crash, exit container after 5 consecutive failures)
cd /app/backend
echo "Starting backend on port 8000..."
RETRY=0
LAST_CRASH=0
while true; do
    START_TIME=$(date +%s)
    PYTHONPATH=/app/backend uvicorn app.main:app --host 0.0.0.0 --port 8000
    EXIT_CODE=$?
    NOW=$(date +%s)
    ELAPSED=$((NOW - START_TIME))

    # 如果正常运行超过60秒，重置重试计数
    if [ $ELAPSED -ge 60 ]; then
        RETRY=0
    fi

    RETRY=$((RETRY + 1))
    if [ $RETRY -ge 5 ]; then
        echo "Backend failed 5 consecutive times, exiting container..."
        kill $FRONTEND_PID 2>/dev/null
        exit 1
    fi
    echo "Backend exited (code=$EXIT_CODE, ran=${ELAPSED}s), restarting in 3s (attempt $RETRY/5)..."
    sleep 3
done &
BACKEND_PID=$!

sleep 3

# Start frontend
cd /app/frontend
echo "Starting frontend on port 5173..."
npx vite --host 0.0.0.0 --force &
FRONTEND_PID=$!

echo "Services: frontend=:5173 backend=:8000"

# Wait for either process to exit, then exit the container
wait -n $BACKEND_PID $FRONTEND_PID
echo "A process exited, shutting down container..."
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
exit 1
