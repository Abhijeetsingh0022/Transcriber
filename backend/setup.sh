#!/usr/bin/env bash
# Setup script for Transcriber using uv package manager
# Supports macOS (Apple Silicon/Intel) and Linux/Windows (NVIDIA CUDA)

set -e

echo "=== Transcriber Setup (powered by uv) ==="

# 1. Ensure uv is installed
if ! command -v uv &> /dev/null && [ ! -f "$HOME/.local/bin/uv" ]; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

UV_BIN=$(command -v uv || echo "$HOME/.local/bin/uv")
echo "Using uv at: $UV_BIN"
$UV_BIN --version

# 2. Sync project dependencies
echo "Syncing dependencies with uv..."
$UV_BIN sync

# 3. Detect hardware & install CUDA PyTorch if NVIDIA GPU is present
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU detected via nvidia-smi! Installing PyTorch with CUDA 12.1..."
    $UV_BIN pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
else
    echo "Non-NVIDIA environment (Apple Silicon or CPU). Default PyTorch installed."
fi

# 4. Initialize SQLite Database
echo "Initializing database and storage directories..."
$UV_BIN run python -c "from db.database import init_db; init_db()"

echo ""
echo "=== Setup Complete! ==="
echo "To run Transcriber with uv:"
echo "  uv run python main.py"
echo ""
echo "Backend will be live at: http://localhost:8000"
