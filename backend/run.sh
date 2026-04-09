#!/bin/bash
set -e

echo "Starting x-reader backend..."
mkdir -p data/books data/audio

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
