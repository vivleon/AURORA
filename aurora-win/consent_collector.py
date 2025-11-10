"""
Aurora Consent Event Collector
- Dedicated ingress for consent decisions + TTL management (expire job)
- Inserts into `consent` table and mirrors summary into `events_raw` for cohesion

Integration (FastAPI):
    from consent_collector import ConsentCollector, ConsentEvent
    consent = ConsentCollector("data/metrics.db")
    app.state.consent = consent

    @app.on_event("startup")
    async def _boot():
        await consent.start()

    @app.on_event("shutdown")
    async def _stop():
        await consent.stop()

    # Record a decision
    await app.state.consent.record(ConsentEvent(
        session_id=sid,
        action="mail.send",
        decision="approved",
        risk="high",
        ttl_hours=24
    ))
"""
from __future__ import annotations
import asyncio, sqlite3, time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

@dataclass
class ConsentEvent:
    session_id: str
    action: str               # e.g., mail.send
    decision: str             # approved|denied|expired
    risk: str                 # low|medium|high
    ttl_hours: int = 0        # 0 => one-shot
    ts: float = 0.0

class ConsentCollector:
    def __init__(self, db_path: str | Path = "data/metrics.db", sweep_interval_sec: int = 60):
        self.db_path = Path(db_path)
        self.sweep_interval = sweep_interval_sec
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def start(self):
        self._stop.clear()
        self._task = asyncio.create_task(self._sweeper())

    async def stop(self):
        self._stop.set()
        if self._task:
            await self._task

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path.as_posix())
        conn.row_factory = sqlite3.Row
        return conn

    async def record(self, ev: ConsentEvent):
        ts = ev.ts or datetime.utcnow().timestamp()
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO consent(ts, session_id, action, decision, risk, ttl_hours)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ts, ev.session_id, ev.action, ev.decision, ev.risk, ev.ttl_hours)
        )
        # mirror minimal record into events_raw for unified queries
        cur.execute(
            """
            INSERT INTO events_raw(ts, type, session_id, intent, outcome, risk)
            VALUES (?, 'consent', ?, ?, ?, ?)
            """,
            (ts, ev.session_id, ev.action, ('success' if ev.decision == 'approved' else 'blocked'), ev.risk)
        )
        conn.commit()
        conn.close()

    async def _sweeper(self):
        # periodically mark expired consents (decision becomes 'expired')
        while not self._stop.is_set():
            await asyncio.sleep(self.sweep_interval)
            try:
                self._expire_due()
            except Exception:
                pass

    def _expire_due(self):
        """
        TTL semantics: A consent row with decision='approved' and ttl_hours>0
        becomes 'expired' when now > ts + ttl_hours*3600. We insert a new row
        to reflect expiration event (immutable log), not UPDATE.
        """
        now = datetime.utcnow().timestamp()
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ts, session_id, action, risk, ttl_hours
            FROM consent
            WHERE decision='approved' AND ttl_hours > 0
            AND (? > ts + ttl_hours*3600)
            """,
            (now,)
        )
        rows = cur.fetchall()
        for r in rows:
            exp_ts = now
            # insert expiration event
            cur.execute(
                "INSERT INTO consent(ts, session_id, action, decision, risk, ttl_hours) VALUES (?, ?, ?, 'expired', ?, 0)",
                (exp_ts, r["session_id"], r["action"], r["risk"]) 
            )
            cur.execute(
                "INSERT INTO events_raw(ts, type, session_id, intent, outcome, risk) VALUES (?, 'consent', ?, ?, 'blocked', ?)",
                (exp_ts, r["session_id"], r["action"], r["risk"]) 
            )
        conn.commit()
        conn.close()

# Quick test
if __name__ == "__main__":
    async def _demo():
        c = ConsentCollector()
        await c.start()
        await c.record(ConsentEvent(session_id="demo", action="mail.send", decision="approved", risk="high", ttl_hours=0))
        await asyncio.sleep(1)
        await c.stop()
    import asyncio
    asyncio.run(_demo())
