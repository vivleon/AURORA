"""
Aurora Event SSE Router (Push)
- Uses in-process EventBus (no DB poll). Zero-latency streaming.
- Mount: app.include_router(event_router, prefix="/events")
- Integration: from event_bus import EventBus; producers call EventBus.publish(...)
"""
from __future__ import annotations
import asyncio, json
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from event_bus import EventBus

event_router = APIRouter()

async def _gen() -> AsyncGenerator[str, None]:
    # initial ping so clients start
    yield "event: ping\ndata: {}\n\n"
    async for ev in EventBus.subscribe():
        try:
            yield f"data: {json.dumps(ev, separators=(',',':'))}\n\n"
        except Exception:
            # keep stream alive
            yield "event: ping\ndata: {}\n\n"

@event_router.get("/stream")
def stream():
    return StreamingResponse(_gen(), media_type="text/event-stream")
