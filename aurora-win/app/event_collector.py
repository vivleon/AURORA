"""
Aurora Event Collector (Base Class)
- Async ingestion for metrics.db (SQLite) [cite: vivleon/aurora/AURORA-main/aurora-win/data/metrics.db] + periodic rollups
"""
from __future__ import annotations
import asyncio
import json
import math
import sqlite3
import statistics
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List, Set

DB_PATH = Path(os.getenv("METRICS_DB_PATH", "data/metrics.db"))

@dataclass
class CollectorConfig:
    db_path: Path = DB_PATH
    flush_interval: float = 0.5  # 초
    rollup_interval: float = 60.0  # 초
    batch_size: int = 200
    queue_size: int = 5000

class EventCollector:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.cfg = CollectorConfig(db_path=Path(db_path))
        self._q: asyncio.Queue = asyncio.Queue(maxsize=self.cfg.queue_size)
        self._flush_task: Optional[asyncio.Task] = None
        self._rollup_task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._known_tables: Set[str] = set() # DB 테이블 캐시
        self._ensure_db()

    # ------------- public API -------------
    async def start(self):
        self._stop.clear()
        self._flush_task = asyncio.create_task(self._flusher())
        self._rollup_task = asyncio.create_task(self._roller())
        print(f"[EventCollector] Started. DB: {self.cfg.db_path}, \
Flush: {self.cfg.flush_interval}s, Rollup: {self.cfg.rollup_interval}s")

    async def stop(self):
        self._stop.set()
        
        # 큐에 남은 항목 플러시 시도
        if not self._q.empty():
            print(f"[EventCollector] Stopping... flushing {self._q.qsize()} remaining events.")
            await self._flush_remaining()
            
        if self._flush_task:
            try:
                self._flush_task.cancel()
                await self._flush_task
            except asyncio.CancelledError:
                pass
        if self._rollup_task:
            try:
                self._rollup_task.cancel()
                await self._rollup_task
            except asyncio.CancelledError:
                pass
        print("[EventCollector] Stopped.")

    async def enqueue(self, event: Dict[str, Any]):
        """
        이벤트를 비동기 큐에 추가합니다. (executor.py [cite: vivleon/aurora/AURORA-main/aurora-win/app/core/executor.py]가 호출)
        """
        # 기본값 및 정제 (schema.sql [cite: vivleon/aurora/AURORA-main/aurora-win/schema.sql] 참조)
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
        try:
            self._q.put_nowait(e)
        except asyncio.QueueFull:
            print(f"[WARN] EventCollector queue full. Discarding event: {e.get('type')}")

    # ------------- internals -------------
    def _ensure_db(self):
        self.cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.cfg.db_path.exists():
            print(f"[WARN] EventCollector: DB file not found at {self.cfg.db_path}. \
It will be created, but 'schema.sql' must be run.")
        self._check_tables()

    def _check_tables(self, conn: sqlite3.Connection = None):
        """DB에 필요한 테이블이 있는지 확인 (캐시)"""
        local_conn = False
        if conn is None:
            conn = self._connect()
            local_conn = True
        
        if not conn:
            return

        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            self._known_tables = {r[0] for r in cur.fetchall()}
        except sqlite3.Error as e:
            print(f"[EventCollector ERROR] Failed to check tables: {e}")
        finally:
            if local_conn:
                conn.close()

    def _connect(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.cfg.db_path.as_posix(), timeout=10.0)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"[EventCollector ERROR] Failed to connect to DB: {e}")
            return None

    async def _flusher(self):
        """
        백그라운드 태스크: 큐의 이벤트를 주기적으로 DB에 배치(batch) 쓰기
        """
        while not self._stop.is_set():
            try:
                # 첫 번째 아이템을 기다림
                first_item = await asyncio.wait_for(self._q.get(), self.cfg.flush_interval)
                batch = [first_item]
                # 큐가 빌 때까지 또는 배치 크기에 도달할 때까지 나머지 아이템 수집
                while len(batch) < self.cfg.batch_size:
                    batch.append(self._q.get_nowait())
            except asyncio.TimeoutError:
                continue # 타임아웃 (배치 비었음)
            except asyncio.QueueEmpty:
                continue # 큐 비었음
            except asyncio.CancelledError:
                break # 중지
                
            if batch:
                try:
                    # DB 쓰기 (동기 작업을 스레드에서 실행)
                    await asyncio.to_thread(self._write_batch, batch)
                except Exception as e:
                    print(f"[EventCollector ERROR] Flusher failed to write batch: {e}")

    async def _flush_remaining(self):
        """앱 종료 시 큐에 남은 모든 항목 쓰기"""
        batch = []
        while not self._q.empty():
            try:
                batch.append(self._q.get_nowait())
            except asyncio.QueueEmpty:
                break
        if batch:
            print(f"[EventCollector] Writing final {len(batch)} events.")
            try:
                await asyncio.to_thread(self._write_batch, batch)
            except Exception as e:
                print(f"[EventCollector ERROR] Final flush failed: {e}")

    def _write_batch(self, batch: List[Dict[str, Any]]):
        """
        이벤트를 DB에 씁니다. (동기)
        [중요] 이 메서드는 event_collector_redis_patch.py [cite: vivleon/aurora/AURORA-main/aurora-win/app/event_collector_redis_patch.py]에서 오버라이드됩니다.
        """
        conn = self._connect()
        if not conn:
            return

        if "events_raw" not in self._known_tables:
            self._check_tables(conn) # 테이블 캐시 갱신
            if "events_raw" not in self._known_tables:
                print(f"[EventCollector ERROR] 'events_raw' table missing. \
Run 'schema.sql'. Discarding {len(batch)} events.")
                conn.close()
                return

        try:
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
        except sqlite3.Error as e:
            print(f"[EventCollector ERROR] _write_batch failed: {e}")
        finally:
            if conn:
                conn.close()

    async def _roller(self):
        """
        백그라운드 태스크: 주기적인 롤업(rollup) 집계기 (1m/5m/1h 윈도우)
        """
        while not self._stop.is_set():
            try:
                await asyncio.sleep(self.cfg.rollup_interval)
                await asyncio.to_thread(self._compute_rollups) # DB 작업을 스레드에서 실행
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[EventCollector ERROR] Rollup failed: {e}")

    def _compute_rollups(self):
        """
        롤업을 계산하고 rollup_* 테이블에 UPSERT합니다. (동기)
        (raw_to_rollup_p_95.py [cite: vivleon/aurora/AURORA-main/aurora-win/raw_to_rollup_p_95.py]의 로직과 유사)
        """
        now = datetime.utcnow().timestamp()
        windows = [60, 300, 3600] # 1m, 5m, 1h
        
        conn = self._connect()
        if not conn:
            return
            
        if "rollup_1m" not in self._known_tables:
            self._check_tables(conn)
            if "rollup_1m" not in self._known_tables:
                print(f"[EventCollector WARN] Rollup tables (e.g., 'rollup_1m') missing. \
Run 'schema.sql'. Skipping rollups.")
                conn.close()
                return

        try:
            cur = conn.cursor()
            for w in windows:
                # 지난 10개 버킷 계산
                since = now - (w * 10)
                cur.execute("SELECT ts, outcome, latency_ms FROM events_raw WHERE ts >= ? AND latency_ms IS NOT NULL ORDER BY ts ASC", (since,))
                rows = cur.fetchall()
                
                buckets: Dict[int, Dict[str, Any]] = {}
                for r in rows:
                    if r["latency_ms"] is None or r["latency_ms"] < 0:
                        continue
                    b = int(r["ts"] // w) * w
                    x = buckets.setdefault(b, {"lat": [], "s": 0, "b": 0, "e": 0})
                    x["lat"].append(int(r["latency_ms"]))
                    o = r["outcome"]
                    if o == "success": x["s"] += 1
                    elif o == "blocked": x["b"] += 1
                    elif o == "error": x["e"] += 1
                
                # UPSERT
                for b, v in buckets.items():
                    lat = sorted(v["lat"]) if v["lat"] else []
                    p95 = lat[int(0.95*len(lat))-1] if lat and len(lat) > 0 else 0
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
        except sqlite3.Error as e:
             print(f"[EventCollector ERROR] _compute_rollups failed: {e}")
        finally:
            if conn:
                conn.close()