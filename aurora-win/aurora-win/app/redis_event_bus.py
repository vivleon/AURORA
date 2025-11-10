"""
Redis Pub/Sub Adapter for Multi-Worker SSE
- 수평 확장된 uvicorn/gunicorn 워커들이 이벤트를 팬아웃(fan-out)할 수 있도록 합니다.
- 채널 스키마: aurora.events (JSON lines)

Usage:
    bus = RedisEventBus(url="redis://localhost:6379/0", channel="aurora.events")
    await bus.publish({"type": "tool", ...})
    async for ev in bus.subscribe():
        yield ev
"""
from __future__ import annotations
import asyncio
import json
import os
from typing import AsyncGenerator, Dict, Any, List

try:
    from redis.asyncio import Redis
    from redis.exceptions import ConnectionError as RedisConnectionError
except ImportError:
    print("[ERROR] 'redis' package not found. Please install it: pip install redis")
    Redis = None
    RedisConnectionError = None

class RedisEventBus:
    def __init__(self, url: str = "redis://localhost:6379/0", channel: str = "aurora.events"):
        if Redis is None:
            raise ImportError("'redis' package is required for RedisEventBus.")
        self.url = url
        self.channel = channel
        self._redis: Redis | None = None
        self._pubsub = None

    async def _client(self) -> Redis:
        if self._redis is None or not self._redis.is_connected():
            try:
                self._redis = Redis.from_url(self.url, decode_responses=True)
                await self._redis.ping()
                print(f"[RedisEventBus] Connected to {self.url}")
            except RedisConnectionError as e:
                print(f"[RedisEventBus ERROR] Failed to connect to Redis: {e}")
                self._redis = None
                raise
        return self._redis

    async def publish(self, event: Dict[str, Any]):
        try:
            r = await self._client()
            await r.publish(self.channel, json.dumps(event, separators=(",", ":")))
        except RedisConnectionError as e:
            print(f"[RedisEventBus ERROR] Publish failed: {e}")
            self._redis = None # 연결 재생성 유도

    async def publish_batch(self, events: list[Dict[str, Any]]):
        if not events:
            return
        try:
            r = await self._client()
            pipe = r.pipeline()
            for e in events:
                pipe.publish(self.channel, json.dumps(e, separators=(",", ":")))
            await pipe.execute()
        except RedisConnectionError as e:
            print(f"[RedisEventBus ERROR] Publish batch failed: {e}")
            self._redis = None

    async def subscribe(self) -> AsyncGenerator[Dict[str, Any], None]:
        while True:
            try:
                r = await self._client()
                self._pubsub = r.pubsub()
                await self._pubsub.subscribe(self.channel)
                print(f"[RedisEventBus] Subscribed to channel '{self.channel}'")
                async for msg in self._pubsub.listen():
                    if msg and msg.get("type") == "message":
                        data = msg.get("data")
                        try:
                            yield json.loads(data)
                        except (json.JSONDecodeError, TypeError):
                            print(f"[RedisEventBus WARN] Failed to decode JSON from message: {data}")
            except RedisConnectionError as e:
                print(f"[RedisEventBus ERROR] Subscription connection lost: {e}. Reconnecting in 5s...")
                self._redis = None # 연결 초기화
                await asyncio.sleep(5)
            except Exception as e:
                print(f"[RedisEventBus ERROR] Subscriber loop failed: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
            finally:
                if self._pubsub:
                    try:
                        await self._pubsub.unsubscribe(self.channel)
                        await self._pubsub.close()
                    except Exception:
                        pass
                self._pubsub = None

# 싱글톤 팩토리
_redis_bus: RedisEventBus | None = None

def get_redis_bus(url: str = "redis://localhost:6379/0", channel: str = "aurora.events") -> RedisEventBus:
    global _redis_bus
    if _redis_bus is None:
        _redis_bus = RedisEventBus(url=url, channel=channel)
    return _redis_bus