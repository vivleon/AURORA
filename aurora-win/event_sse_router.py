"""
Aurora Event SSE Router
- Server-Sent Events (SSE) endpoint streaming recent events as compact summaries
- Mount: app.include_router(event_router, prefix="/events")

Notes:
- Uses a lightweight poll over metrics.db every 1s to pick new rows by id
- In production, replace with in-process pub/sub or SQLite update hook
"""
from __future__ import annotations
import asyncio, json, sqlite3
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

DB_PATH = Path("data/metrics.db")

event_router = APIRouter()


def _connect():
    conn = sqlite3.connect(DB_PATH.as_posix(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

async def _stream_events() -> AsyncGenerator[str, None]:
    last_id = 0
    conn = _connect()
    cur = conn.cursor()
    yield "event: ping\ndata: {}\n\n"
    while True:
        await asyncio.sleep(1.0)
        try:
            cur.execute(
                "SELECT id, ts, type, tool, intent, outcome, risk, latency_ms FROM events_raw WHERE id > ? ORDER BY id ASC LIMIT 100",
                (last_id,),
            )
            rows = cur.fetchall()
            if not rows:
                continue
            for r in rows:
                last_id = max(last_id, r["id"]) if r["id"] else last_id
                # compact summary for UI toast
                summary = {
                    "id": r["id"],
                    "ts": datetime.utcfromtimestamp(r["ts"]).isoformat()+"Z" if r["ts"] else None,
                    "type": r["type"],
                    "tool": r["tool"],
                    "intent": r["intent"],
                    "outcome": r["outcome"],
                    "risk": r["risk"],
                    "latency_ms": r["latency_ms"],
                }
                yield f"data: {json.dumps(summary, separators=(',',':'))}\n\n"
        except Exception:
            # keep-alive on error
            yield "event: ping\ndata: {}\n\n"

@event_router.get("/stream")
def sse_stream():
    return StreamingResponse(_stream_events(), media_type="text/event-stream")
