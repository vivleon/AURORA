"""
EventCollector patch to publish to Redis bus after DB commit
- 멀티워커 환경에서 EventCollector/EventCollectorWithBus 대신 이 클래스를 사용합니다.
- (app/main.py (통합본)에서 사용됨)
"""
from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime
import os

# app.event_collector에서 기본 클래스 임포트
from app.event_collector import EventCollector
# app.redis_event_bus에서 Redis 버스 임포트
from app.redis_event_bus import get_redis_bus

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHANNEL = os.getenv("REDIS_CHANNEL", "aurora.events")

class EventCollectorRedis(EventCollector):
    def __init__(self, db_path: str, redis_url: str = REDIS_URL, channel: str = CHANNEL):
        super().__init__(db_path)
        self.redis_url = redis_url
        self.channel = channel
        print(f"[EventCollectorRedis] Initialized. Publishing to Redis: {redis_url}")

    def _write_batch(self, batch: List[Dict[str, Any]]):
        # 1. 부모 클래스의 _write_batch 호출 (SQLite에 먼저 쓰기)
        super()._write_batch(batch)
        
        # 2. Redis에 발행할 요약 이벤트 생성
        summaries = []
        now_iso = datetime.utcnow().isoformat()+"Z"
        for e in batch:
            summaries.append({
                "ts": e.get("ts") or now_iso, # 타임스탬프
                "type": e.get("type"),
                "tool": e.get("tool"),
                "intent": e.get("intent"),
                "outcome": e.get("outcome"),
                "risk": e.get("risk"),
                "latency_ms": e.get("latency_ms"),
            })
            
        # 3. Redis에 발행 (async 함수를 스레드에서 안전하게 호출)
        # (참고: _write_batch는 _flusher의 비동기 루프에서 실행되지만, 
        # DB 작업 자체가 동기(blocking)이므로, anyio/asyncio를 직접 사용하기보다
        # 스레드에서 비동기를 호출하는 것이 안전할 수 있습니다.
        # 여기서는 _flusher가 이미 비동기 루프에서 실행 중이라고 가정하고 await 사용)
        try:
            import anyio
            bus = get_redis_bus(self.redis_url, self.channel)
            
            # _write_batch는 동기 컨텍스트에서 실행될 수 있으므로
            # anyio.from_thread.run을 사용하여 비동기 publish_batch를 호출합니다.
            anyio.from_thread.run(bus.publish_batch, summaries)
            
        except Exception as e:
            # 예: Redis 연결 실패
            print(f"[EventCollectorRedis ERROR] Failed to publish batch to Redis: {e}")