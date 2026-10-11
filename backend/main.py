"""
Main entry point for Transcriber Backend Application.
Initializes SQLite database, boots background queue worker, and serves FastAPI app.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load local environment variables from .env
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager
from db.database import init_db
from engine.worker import start_worker, QueueWorker
from api.router import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: manages boot sequence and graceful worker shutdown."""
    print("Initializing Transcriber SQLite Database...")
    init_db()
    from db.crud import recover_orphaned_jobs
    recover_orphaned_jobs()
    print("Starting background queue worker...")
    start_worker()
    print("Transcriber ready.")
    yield
    print("Shutting down Transcriber queue worker...")
    QueueWorker.get_instance().stop()
    print("Checkpointing SQLite WAL & optimizing database...")
    try:
        from db.database import wal_checkpoint, optimize_db
        optimize_db()
        wal_checkpoint("TRUNCATE")
        print("Database cleanly checkpointed.")
    except Exception as e:
        print(f"Warning: Failed to checkpoint database on shutdown: {e}")


app = FastAPI(
    title="Transcriber API",
    description="High-accuracy local AI transcription, speaker diarization, and batch queue engine.",
    version="1.0.0",
    lifespan=lifespan,
)

import time
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class ServerTimingMiddleware(BaseHTTPMiddleware):
    """Measures precise request processing duration and emits standard Server-Timing headers."""
    async def dispatch(self, request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        response.headers["Server-Timing"] = f"total;dur={elapsed_ms:.2f}"
        response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
        return response


# Precise latency tracking in browser DevTools Network tab
app.add_middleware(ServerTimingMiddleware)

# Response compression for large transcripts, waveforms, dialogues, and script previews
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Enable CORS for seamless Next.js frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:7860",
        "http://127.0.0.1:7860",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|.*\.hf\.space|.*\.huggingface\.co)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["ETag", "Server-Timing", "X-Response-Time", "Content-Disposition", "Content-Length"],
    max_age=86400,
)

# Mount REST API
app.include_router(api_router)

# Mount static production frontend build if frontend/out exists (Next.js export)
web_out_dir = Path(__file__).resolve().parent.parent / "frontend" / "out"
if web_out_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_out_dir), html=True), name="web_prod")
else:
    @app.get("/")
    def root_health():
        return {
            "status": "online",
            "service": "Transcriber API Engine",
            "version": "1.0.0",
            "docs": "/docs",
            "frontend_dev_server": "http://localhost:3000"
        }


if __name__ == "__main__":
    import uvicorn
    reload_mode = os.environ.get("RELOAD", "true").lower() in ("true", "1")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload_mode)
