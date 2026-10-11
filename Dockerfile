# ==============================================================================
# Stage 1: Build Next.js 16 Static Frontend
# ==============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
ENV NEXT_PUBLIC_API_URL=/api
RUN npm run build

# ==============================================================================
# Stage 2: Production Python Backend with FFmpeg & Unified Web Serving
# ==============================================================================
FROM python:3.11-slim AS production

# Install system media libraries (FFmpeg is required for PyAV, audio extraction & muxing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python backend dependencies
COPY backend/pyproject.toml ./backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ./backend

# Copy backend source code
COPY backend/ ./backend/

# Copy static frontend export from Stage 1 into frontend/out
COPY --from=frontend-builder /app/frontend/out ./frontend/out

# Set up user 1000 for Hugging Face Spaces & security best practices
RUN useradd -m -u 1000 user && \
    mkdir -p /app/backend/data /home/user/.cache/huggingface && \
    chown -R user:user /app /home/user

USER user

# Environment configuration (Port 7860 is the official default for HF Spaces)
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    DATA_DIR=/app/backend/data

EXPOSE 7860

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7860/api/system/status || exit 1

WORKDIR /app/backend
CMD ["python", "main.py"]
