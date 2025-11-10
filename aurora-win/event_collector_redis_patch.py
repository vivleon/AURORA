"""
EventCollector patch to publish to Redis bus after DB commit
- Swap this in place of EventCollector/EventCollectorWithBus when running multi-workers

Usage:
    from event_collector_redis_patch import EventCollectorRedis
    collector = EventCollectorRedis("data/metrics.db", redis_url="redis://localhost:6379/0")
"""
from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime

from event_collector import EventCollector
from redis_event_bus import get_redis_bus

class EventCollectorRedis(EventCollector):
    def __init__(self, db_path: str, redis_url: str = "redis://localhost:6379/0", channel: str = "aurora.events"):
        super().__init__(db_path)
        self.redis_url = redis_url
        self.channel = channel

    def _write_batch(self, batch: List[Dict[str, Any]]):
        super()._write_batch(batch)
        summaries = []
        now_iso = datetime.utcnow().isoformat()+"Z"
        for e in batch:
            summaries.append({
                "ts": e.get("ts") or now_iso,
                "type": e.get("type"),
                "tool": e.get("tool"),
                "intent": e.get("intent"),
                "outcome": e.get("outcome"),
                "risk": e.get("risk"),
                "latency_ms": e.get("latency_ms"),
            })
        # publish via redis (async safe from thread)
        import anyio
        bus = get_redis_bus(self.redis_url, self.channel)
        anyio.from_thread.run(bus.publish_batch, summaries)
