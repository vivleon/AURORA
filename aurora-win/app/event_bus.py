"""
Aurora EventBus (in-proc async broadcast)
- (app/main.py [cite: vivleon/aurora/AURORA-main/aurora-win/app/main.py]에서 사용되지 않음. RedisEventBus로 대체됨)
- (event_sse_push_router.py [cite: vivleon/aurora/AURORA-main/aurora-win/event_sse_push_router.py]가 이 파일을 사용)
"""
from __future__ import annotations
import asyncio, json
from typing import AsyncGenerator, Dict, Any, List

class _EventBus:
    def __init__(self, max_queue: int = 5000):
        self._subscribers: List[asyncio.Queue] = []
        self._max_queue = max_queue
        self._lock = asyncio.Lock()

    async def subscribe(self) -> AsyncGenerator[Dict[str, Any], None]:
        q: asyncio.Queue = asyncio.Queue(self._max_queue)
        async with self._lock:
            self._subscribers.append(q)
        try:
            while True:
                item = await q.get()
                yield item
        finally:
            async with self._lock:
                if q in self._subscribers:
                    self._subscribers.remove(q)

    async def publish(self, event: Dict[str, Any]):
        # best-effort: drop if queue full
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def publish_batch(self, events: List[Dict[str, Any]]):
        for e in events:
            await self.publish(e)

EventBus = _EventBus()