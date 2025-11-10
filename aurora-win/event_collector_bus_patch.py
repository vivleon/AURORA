"""
EventCollector with EventBus publishing
- Drop-in subclass that publishes compact summaries to EventBus after DB commit
- Usage:
    from event_collector_bus_patch import EventCollectorWithBus
    collector = EventCollectorWithBus("data/metrics.db")
"""
from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime

from event_collector import EventCollector
from event_bus import EventBus

class EventCollectorWithBus(EventCollector):
    def _write_batch(self, batch: List[Dict[str, Any]]):
        # call parent to persist
        super()._write_batch(batch)
        # publish compact summaries
        summaries = []
        now_iso = datetime.utcnow().isoformat()+"Z"
        for e in batch:
            summaries.append({
                "ts": now_iso if not e.get("ts") else None,  # optional
                "type": e.get("type"),
                "tool": e.get("tool"),
                "intent": e.get("intent"),
                "outcome": e.get("outcome"),
                "risk": e.get("risk"),
                "latency_ms": e.get("latency_ms"),
            })
        # async publish (fire-and-forget)
        import anyio
        anyio.from_thread.run(EventBus.publish_batch, summaries)
