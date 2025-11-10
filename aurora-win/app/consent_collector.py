"""
Aurora Consent Event Collector
- 동의 결정을 'consent' 테이블에 기록하고, 'events_raw' 테이블에도 미러링합니다.
- 만료된 동의를 'expired'로 처리하는 백그라운드 스위퍼를 실행합니다.
"""
from __future__ import annotations
import asyncio
import sqlite3
import time
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DB_PATH = Path(os.getenv("METRICS_DB_PATH", "data/metrics.db"))

@dataclass
class ConsentEvent:
    session_id: str
    action: str               # e.g., mail.send
    decision: str             # approved|denied|expired
    risk: str                 # low|medium|high
    ttl_hours: int = 0        # 0 => one-shot
    ts: float = 0.0

class ConsentCollector:
    def __init__(self, db_path: str | Path = DB_PATH, sweep_interval_sec: int = 60):
        self.db_path = Path(db_path)
        self.sweep_interval = sweep_interval_sec
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def start(self):
        self._stop.clear()
        self._task = asyncio.create_task(self._sweeper())
        print(f"[ConsentCollector] Started. Sweeping expired consents every {self.sweep_interval}s.")

    async def stop(self):
        self._stop.set()
        if self._task:
            try:
                self._task.cancel()
                await self._task
            except asyncio.CancelledError:
                pass
        print("[ConsentCollector] Stopped.")


    def _connect(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.db_path.as_posix())
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"[ConsentCollector ERROR] Failed to connect to DB: {e}")
            return None

    async def record(self, ev: ConsentEvent):
        """
        동의 결정을 DB에 기록합니다.
        """
        ts = ev.ts or datetime.utcnow().timestamp()
        conn = self._connect()
        if not conn:
            return
            
        try:
            cur = conn.cursor()
            # 1. 'consent' 테이블에 상세 기록
            cur.execute(
                """
                INSERT INTO consent(ts, session_id, action, decision, risk, ttl_hours)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ts, ev.session_id, ev.action, ev.decision, ev.risk, ev.ttl_hours)
            )
            # 2. 'events_raw' 테이블에 요약 미러링 (대시보드 KPI용)
            cur.execute(
                """
                INSERT INTO events_raw(ts, type, session_id, intent, outcome, risk)
                VALUES (?, 'consent', ?, ?, ?, ?)
                """,
                (ts, ev.session_id, ev.action, ('success' if ev.decision == 'approved' else 'blocked'), ev.risk)
            )
            conn.commit()
        except sqlite3.Error as e:
            print(f"[ConsentCollector ERROR] Failed to record event: {e}")
        finally:
            if conn:
                conn.close()

    async def _sweeper(self):
        """
        백그라운드에서 주기적으로 만료된(approved) 동의를 찾아
        'expired' 레코드를 추가로 삽입합니다.
        """
        while not self._stop.is_set():
            try:
                await asyncio.sleep(self.sweep_interval)
                self._expire_due()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ConsentCollector ERROR] Sweeper failed: {e}")

    def _expire_due(self):
        """
        'approved' 상태이고 TTL이 지난 동의를 찾아 'expired' 이벤트를 기록합니다.
        """
        now = datetime.utcnow().timestamp()
        conn = self._connect()
        if not conn:
            return
            
        new_expirations = []
        try:
            cur = conn.cursor()
            # 1. 만료 대상 조회
            # (ts + ttl_hours * 3600) < now 이고, 아직 'expired' 이벤트가 없는 것
            cur.execute(
                """
                SELECT t1.ts, t1.session_id, t1.action, t1.risk, t1.ttl_hours
                FROM consent t1
                WHERE t1.decision='approved' AND t1.ttl_hours > 0
                  AND (? > (t1.ts + t1.ttl_hours * 3600))
                  AND NOT EXISTS (
                    SELECT 1 FROM consent t2
                    WHERE t2.action = t1.action
                      AND t2.session_id = t1.session_id
                      AND t2.decision = 'expired'
                      AND t2.ts > t1.ts
                  )
                GROUP BY t1.session_id, t1.action
                """,
                (now,)
            )
            rows = cur.fetchall()
            
            if not rows:
                return

            print(f"[ConsentCollector] Found {len(rows)} consents to expire.")
            
            # 2. 만료 이벤트 기록
            exp_ts = now
            for r in rows:
                new_expirations.append(r)
                # 'consent' 테이블에 'expired' 기록
                cur.execute(
                    "INSERT INTO consent(ts, session_id, action, decision, risk, ttl_hours) VALUES (?, ?, ?, 'expired', ?, 0)",
                    (exp_ts, r["session_id"], r["action"], r["risk"]) 
                )
                # 'events_raw'에도 미러링
                cur.execute(
                    "INSERT INTO events_raw(ts, type, session_id, intent, outcome, risk) VALUES (?, 'consent', ?, ?, 'blocked', ?)",
                    (exp_ts, r["session_id"], r["action"], r["risk"]) 
                )
            conn.commit()
        except sqlite3.Error as e:
            print(f"[ConsentCollector ERROR] Failed to expire consents: {e}")
        finally:
            if conn:
                conn.close()