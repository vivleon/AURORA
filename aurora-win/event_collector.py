"""
Aurora Event Collector
- Async ingestion for metrics.db (SQLite) + periodic rollups
- Usage: run as a background task in FastAPI startup

Example integration (app/main.py):
    from event_collector import EventCollector
    collector = EventCollector(db_path="data/metrics.db")
    app.state.collector = collector
    @app.on_event("startup")
    async def _boot():
        await collector.start()
    @app.on_event("shutdown")
    async def _stop():
        await collector.stop()
    # push events anywhere via: await app.state.collector.enqueue({...})
"""
from __future__ import annotations
import asyncio, json, math, sqlite3, statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List

@dataclass
class CollectorConfig:
    db_path: Path = Path("data/metrics.db")
    flush_interval: float = 0.5  # seconds
    rollup_interval: float = 60.0  # seconds
    batch_size: int = 200


class EventCollector:
    def __init__(self, db_path: str | Path = "data/metrics.db"):
        self.cfg = CollectorConfig(db_path=Path(db_path))
        self._q: asyncio.Queue = asyncio.Queue(maxsize=5000)
        self._flush_task: Optional[asyncio.Task] = None
        self._rollup_task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._ensure_db()

    # ------------- public API -------------
    async def start(self):
        self._stop.clear()
        self._flush_task = asyncio.create_task(self._flusher())
        self._rollup_task = asyncio.create_task(self._roller())

    async def stop(self):
        self._stop.set()
        if self._flush_task:
            await self._flush_task
        if self._rollup_task:
            await self._rollup_task

    async def enqueue(self, event: Dict[str, Any]):
        # sanitize + defaults
        e = {
            "ts": event.get("ts") or datetime.utcnow().timestamp(),
            "type": event.get("type", "task"),
            "session_id": event.get("session_id"),
            "user": event.get("user", "local"),
            "intent": event.get("intent"),
            "plan_id": event.get("plan_id"),
            "tool": event.get("tool"),
            "outcome": event.get("outcome"),
            "latency_ms": event.get("latency_ms"),
            "err_code": event.get("err_code"),
            "risk": event.get("risk"),
            "evidences": event.get("evidences", 0),
            "args_hash": event.get("args_hash"),
        }
        await self._q.put(e)

    # ------------- internals -------------
    def _ensure_db(self):
        self.cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
        # expect schema.sql already applied

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.cfg.db_path.as_posix())
        conn.row_factory = sqlite3.Row
        return conn

    async def _flusher(self):
        while not self._stop.is_set():
            await asyncio.sleep(self.cfg.flush_interval)
            batch: List[Dict[str, Any]] = []
            try:
                while len(batch) < self.cfg.batch_size:
                    batch.append(self._q.get_nowait())
            except asyncio.QueueEmpty:
                pass
            if not batch:
                continue
            self._write_batch(batch)

    def _write_batch(self, batch: List[Dict[str, Any]]):
        conn = self._connect()
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO events_raw
            (ts, type, session_id, user, intent, plan_id, tool, outcome, latency_ms, err_code, risk, evidences, args_hash)
            VALUES (:ts, :type, :session_id, :user, :intent, :plan_id, :tool, :outcome, :latency_ms, :err_code, :risk, :evidences, :args_hash)
            """,
            batch,
        )
        conn.commit()
        conn.close()

    async def _roller(self):
        # periodic rollup aggregator for 1m/5m/1h windows
        while not self._stop.is_set():
            await asyncio.sleep(self.cfg.rollup_interval)
            try:
                self._compute_rollups()
            except Exception:
                # swallow aggregator errors to keep service running
                pass

    def _compute_rollups(self):
        now = datetime.utcnow().timestamp()
        windows = [60, 300, 3600]
        conn = self._connect()
        cur = conn.cursor()
        for w in windows:
            since = now - (w * 10)  # compute last 10 buckets
            cur.execute("SELECT ts, outcome, latency_ms FROM events_raw WHERE ts >= ? ORDER BY ts ASC", (since,))
            rows = cur.fetchall()
            buckets: Dict[int, Dict[str, Any]] = {}
            for r in rows:
                b = int(r["ts"] // w) * w
                x = buckets.setdefault(b, {"lat": [], "s": 0, "b": 0, "e": 0})
                if r["latency_ms"] is not None:
                    x["lat"].append(int(r["latency_ms"]))
                o = r["outcome"]
                if o == "success": x["s"] += 1
                elif o == "blocked": x["b"] += 1
                elif o == "error": x["e"] += 1
            # upsert
            for b, v in buckets.items():
                lat = sorted(v["lat"]) if v["lat"] else []
                p95 = lat[int(0.95*len(lat))-1] if lat else 0
                table = {60: "rollup_1m", 300: "rollup_5m", 3600: "rollup_1h"}[w]
                cur.execute(
                    f"""
                    INSERT INTO {table}(bucket, success_cnt, blocked_cnt, error_cnt, p95_latency)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(bucket) DO UPDATE SET
                        success_cnt=excluded.success_cnt,
                        blocked_cnt=excluded.blocked_cnt,
                        error_cnt=excluded.error_cnt,
                        p95_latency=excluded.p95_latency
                    """,
                    (b, v["s"], v["b"], v["e"], p95)
                )
        conn.commit()
        conn.close()

# ------------- convenience -------------
async def demo_feed(collector: EventCollector):
    import random
    tools = ["browser.scrape", "nlp.summarize", "files.read", "mail.compose"]
    outcomes = ["success", "blocked", "error"]
    for _ in range(100):
        e = {
            "type": "tool",
            "tool": random.choice(tools),
            "outcome": random.choices(outcomes, weights=[0.8, 0.1, 0.1])[0],
            "latency_ms": random.randint(50, 3000),
        }
        await collector.enqueue(e)
        await asyncio.sleep(0.01)

if __name__ == "__main__":
    async def _main():
        c = EventCollector()
        await c.start()
        await demo_feed(c)
        await asyncio.sleep(2)
        await c.stop()
    asyncio.run(_main())
