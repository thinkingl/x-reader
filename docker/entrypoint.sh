#!/bin/bash
set -e

echo "Starting x-reader services..."

# Install torch and omnivoice if not already installed
if ! python3 -c "import torch" 2>/dev/null; then
    echo "Installing torch and omnivoice (this may take a while)..."
    pip3 install --no-cache-dir torch torchaudio omnivoice
fi

# Download OmniVoice model if not exists
if [ ! -d "/app/hf_cache" ]; then
    echo "Downloading OmniVoice model (this may take a while)..."
    python3 -c "
from omnivoice import OmniVoice
import torch
print('Downloading OmniVoice model...')
model = OmniVoice.from_pretrained('k2-fsa/OmniVoice', device_map='cpu', dtype=torch.float32)
print('OmniVoice model downloaded successfully!')
"
fi

# Start backend in background
cd /app/backend
echo "Starting backend on port 8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend..."
sleep 5

# Start frontend in background
cd /app/frontend
echo "Starting frontend on port 5173..."
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

# Wait for frontend to be ready
echo "Waiting for frontend..."
sleep 5

echo "All services started:"
echo "  - Backend: http://localhost:8000"
echo "  - Frontend: http://localhost:5173"

# Wait for all processes
wait $BACKEND_PID $FRONTEND_PID
