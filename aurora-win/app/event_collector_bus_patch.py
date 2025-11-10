"""
EventCollector with EventBus publishing
- (app/main.py [cite: vivleon/aurora/AURORA-main/aurora-win/app/main.py]에서 사용되지 않음. Redis 패치로 대체됨)
"""
from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime

from app.event_collector import EventCollector
from app.event_bus import EventBus

class EventCollectorWithBus(EventCollector):
    def _write_batch(self, batch: List[Dict[str, Any]]):
        # call parent to persist
        super()._write_batch(batch)
        # publish compact summaries
        summaries = []
        now_iso = datetime.utcnow().isoformat()+"Z"
        for e in batch:
            summaries.append({
                "ts": now_iso if not e.get("ts") else None,
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