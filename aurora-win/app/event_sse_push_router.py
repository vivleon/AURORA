"""
Aurora Event SSE Router (Push)
- (app/main.py [cite: vivleon/aurora/AURORA-main/aurora-win/app/main.py]에서 사용되지 않음. Redis 라우터로 대체됨)
"""
from __future__ import annotations
import asyncio, json
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.event_bus import EventBus

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