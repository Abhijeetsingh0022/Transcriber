"""
Event Bus for Server-Sent Events (SSE) telemetry.
Allows background workers to broadcast job progress, state changes, and completion
to connected web clients without polling.
"""

import asyncio
import threading
from typing import Dict, Any, List
import json


class EventBus:
    """Thread-safe and async-compatible event hub for SSE broadcasting."""
    _subscribers: List[tuple] = []
    _lock = threading.Lock()

    @classmethod
    def subscribe(cls) -> asyncio.Queue:
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()
        with cls._lock:
            cls._subscribers.append((loop, queue))
        return queue

    @classmethod
    def unsubscribe(cls, queue: asyncio.Queue):
        with cls._lock:
            cls._subscribers = [(l, q) for (l, q) in cls._subscribers if q != queue]

    @classmethod
    def broadcast(cls, event_type: str, data: Dict[str, Any]):
        """Dispatches an event thread-safely to all active SSE subscriber queues."""
        message = {
            "event": event_type,
            "data": data
        }
        with cls._lock:
            subscribers = list(cls._subscribers)

        for loop, q in subscribers:
            try:
                if loop.is_running():
                    loop.call_soon_threadsafe(q.put_nowait, message)
            except Exception:
                pass


def broadcast_job_progress(job_id: str, progress: float, stage: str, status: str = "processing"):
    """Helper to dispatch job progress update."""
    EventBus.broadcast("job_progress", {
        "job_id": job_id,
        "progress": round(progress, 1),
        "stage": stage,
        "status": status,
    })


def broadcast_job_completed(job_id: str, duration: float):
    """Helper to dispatch job completion."""
    EventBus.broadcast("job_completed", {
        "job_id": job_id,
        "status": "completed",
        "duration_seconds": duration,
    })


def broadcast_job_failed(job_id: str, error: str):
    """Helper to dispatch job failure."""
    EventBus.broadcast("job_failed", {
        "job_id": job_id,
        "status": "failed",
        "error": error,
    })
