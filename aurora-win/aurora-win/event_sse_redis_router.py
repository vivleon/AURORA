"""
SSE Router backed by Redis Pub/Sub
- Multi-worker compatible. Each client opens its own Redis subscription.
- Mount: app.include_router(sse_router, prefix="/events")
- Configure REDIS_URL via env or pass explicit URL to get_redis_bus.
"""
from __future__ import annotations
import os, json
from typing import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from redis_event_bus import get_redis_bus

sse_router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHANNEL = os.getenv("REDIS_CHANNEL", "aurora.events")

async def _gen() -> AsyncGenerator[str, None]:
    bus = get_redis_bus(REDIS_URL, CHANNEL)
    # kickstart
    yield "event: ping\ndata: {}\n\n"
    async for ev in bus.subscribe():
        try:
            yield f"data: {json.dumps(ev, separators=(',',':'))}\n\n"
        except Exception:
            yield "event: ping\ndata: {}\n\n"

@sse_router.get("/stream")
def stream():
    return StreamingResponse(_gen(), media_type="text/event-stream")
