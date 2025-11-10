"""
SSE Router backed by Redis Pub/Sub
- 멀티워커 호환. 각 클라이언트는 고유한 Redis 구독을 엽니다.
- (app/main.py (통합본)에서 사용됨)
"""
from __future__ import annotations
import os
import json
from typing import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

# app.redis_event_bus에서 버스 임포트
from app.redis_event_bus import get_redis_bus

sse_router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHANNEL = os.getenv("REDIS_CHANNEL", "aurora.events")

async def _gen() -> AsyncGenerator[str, None]:
    """
    Redis 채널을 구독하고 SSE 이벤트를 생성하는 비동기 제너레이터
    """
    bus = get_redis_bus(REDIS_URL, CHANNEL)
    
    # 클라이언트 연결 즉시 핑(ping) 전송
    yield "event: ping\ndata: {}\n\n"
    
    async for ev in bus.subscribe():
        try:
            # data: {"type": "tool", ...}
            yield f"data: {json.dumps(ev, separators=(',',':'))}\n\n"
        except Exception:
            # 스트림이 끊기지 않도록 오류 발생 시 핑(ping) 전송
            yield "event: ping\ndata: {}\n\n"

@sse_router.get("/stream")
def stream():
    """
    실시간 이벤트 스트림 SSE 엔드포인트
    """
    return StreamingResponse(_gen(), media_type="text/event-stream")