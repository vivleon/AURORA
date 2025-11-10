"""
Aurora EventBus (in-proc async broadcast)
- Lightweight pub/sub for real-time event streaming
- Producer: await EventBus.publish(event_dict) or publish_batch(list)
- Consumer (SSE): async for e in EventBus.subscribe(): yield e
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
