"""
SSE event stream endpoint.
"""

import json
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from api.events import EventBus

router = APIRouter()


@router.get("/events")
async def events_stream():
    """SSE endpoint streaming live job progress and stage transitions."""
    async def event_generator():
        queue = EventBus.subscribe()
        try:
            while True:
                msg = await queue.get()
                yield {"event": msg["event"], "data": json.dumps(msg["data"])}
        finally:
            EventBus.unsubscribe(queue)

    return EventSourceResponse(event_generator(), ping=15)
