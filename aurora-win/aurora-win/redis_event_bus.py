"""
Redis Pub/Sub Adapter for Multi-Worker SSE
- Allows horizontally scaled uvicorn/gunicorn workers to fan-out events
- Channel schema: aurora.events (JSON lines)

Usage:
    bus = RedisEventBus(url="redis://localhost:6379/0", channel="aurora.events")
    await bus.publish({"type": "tool", ...})
    async for ev in bus.subscribe():
        yield ev

Notes:
- Requires `redis>=4` (redis.asyncio).
- For high throughput, consider Redis Stream (XADD/XREAD) instead of Pub/Sub.
"""
from __future__ import annotations
import asyncio, json
from typing import AsyncGenerator, Dict, Any

from redis.asyncio import Redis

class RedisEventBus:
    def __init__(self, url: str = "redis://localhost:6379/0", channel: str = "aurora.events"):
        self.url = url
        self.channel = channel
        self._redis: Redis | None = None

    async def _client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.url, decode_responses=True)
        return self._redis

    async def publish(self, event: Dict[str, Any]):
        r = await self._client()
        await r.publish(self.channel, json.dumps(event, separators=(",", ":")))

    async def publish_batch(self, events: list[Dict[str, Any]]):
        if not events:
            return
        r = await self._client()
        pipe = r.pipeline()
        for e in events:
            pipe.publish(self.channel, json.dumps(e, separators=(",", ":")))
        await pipe.execute()

    async def subscribe(self) -> AsyncGenerator[Dict[str, Any], None]:
        r = await self._client()
        pubsub = r.pubsub()
        await pubsub.subscribe(self.channel)
        try:
            async for msg in pubsub.listen():
                if msg and msg.get("type") == "message":
                    data = msg.get("data")
                    try:
                        yield json.loads(data)
                    except Exception:
                        pass
        finally:
            await pubsub.unsubscribe(self.channel)
            await pubsub.close()

# Singleton factory (optional)
_redis_bus: RedisEventBus | None = None

def get_redis_bus(url: str = "redis://localhost:6379/0", channel: str = "aurora.events") -> RedisEventBus:
    global _redis_bus
    if _redis_bus is None:
        _redis_bus = RedisEventBus(url=url, channel=channel)
    return _redis_bus
