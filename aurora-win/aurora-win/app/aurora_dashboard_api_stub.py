"""
Aurora Dashboard API Stub
- Implements GET /dash/* endpoints used by dashboards.json
- Reads from SQLite (metrics.db) if present; otherwise returns safe placeholders
- Mount into FastAPI as a router: app.include_router(dash_router, prefix="/dash")
"""
from __future__ import annotations
import sqlite3, json, time, statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple

from fastapi import APIRouter, Query, Body
from pydantic import BaseModel

DB_PATH = Path("data/metrics.db")

dash_router = APIRouter()

# ------------------------- helpers -------------------------

def _connect():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH.as_posix())
    conn.row_factory = sqlite3.Row
    return conn


def _window_to_ts(window: str) -> float:
    # window in forms like '1h', '24h', '7d'
    unit = window[-1].lower()
    val = int(window[:-1])
    now = datetime.utcnow()
    if unit == 'm':
        delta = timedelta(minutes=val)
    elif unit == 'h':
        delta = timedelta(hours=val)
    elif unit == 'd':
        delta = timedelta(days=val)
    else:
        delta = timedelta(hours=1)
    return (now - delta).timestamp()


# ------------------------- models -------------------------
class KPIResponse(BaseModel):
    kpi: Dict[str, Any]

class ConsentTimelineItem(BaseModel):
    ts: str
    decision: str

class ErrorRow(BaseModel):
    tool: str
    err_code: str | None
    count: int

# ------------------------- endpoints -------------------------
@dash_router.get("/kpi", response_model=KPIResponse)
def get_kpi(window: str = Query("1h")):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        # placeholders if DB not ready
        return {"kpi": {"success": 0.0, "blocked": 0.0, "p95_ms": 0}}
    cur = conn.cursor()
    cur.execute("SELECT outcome, latency_ms FROM events_raw WHERE ts >= ?", (since,))
    rows = cur.fetchall()
    lat = [r["latency_ms"] for r in rows if r["latency_ms"] is not None]
    outcomes = [r["outcome"] for r in rows]
    total = max(len(outcomes), 1)
    success = sum(1 for o in outcomes if o == "success") / total
    blocked = sum(1 for o in outcomes if o == "blocked") / total
    p95 = int(sorted(lat)[int(0.95 * len(lat))]) if lat else 0
    return {"kpi": {"success": round(success, 4), "blocked": round(blocked, 4), "p95_ms": p95}}


@dash_router.get("/latency")
def get_latency(p: int = Query(95, ge=50, le=99), window: str = Query("1h"), tool: str | None = None):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"series": []}
    cur = conn.cursor()
    if tool:
        cur.execute("SELECT tool, latency_ms FROM events_raw WHERE ts >= ? AND tool=?", (since, tool))
    else:
        cur.execute("SELECT tool, latency_ms FROM events_raw WHERE ts >= ?", (since,))
    rows = cur.fetchall()
    buckets: Dict[str, List[int]] = {}
    for r in rows:
        if r["latency_ms"] is None: continue
        buckets.setdefault(r["tool"] or "unknown", []).append(int(r["latency_ms"]))
    data = []
    for k, v in buckets.items():
        v.sort()
        idx = int((p/100.0) * len(v)) - 1
        idx = max(0, min(idx, len(v)-1))
        data.append({"tool": k, "latency_ms": v[idx]})
    return {"series": data}


@dash_router.get("/consent/timeline")
def consent_timeline(window: str = Query("7d")):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"items": []}
    cur = conn.cursor()
    cur.execute("SELECT ts, decision FROM consent WHERE ts >= ? ORDER BY ts ASC", (since,))
    items = [{"ts": datetime.utcfromtimestamp(r["ts"]).isoformat()+"Z", "decision": r["decision"]} for r in cur.fetchall()]
    return {"items": items}


@dash_router.get("/errors/top")
def errors_top(window: str = Query("1h"), limit: int = Query(10, ge=1, le=100)):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"rows": []}
    cur = conn.cursor()
    cur.execute(
        """
        SELECT tool, err_code, COUNT(*) as cnt
        FROM events_raw
        WHERE ts >= ? AND outcome='error'
        GROUP BY tool, err_code
        ORDER BY cnt DESC
        LIMIT ?
        """, (since, limit)
    )
    rows = [{"tool": r["tool"], "err_code": r["err_code"], "count": r["cnt"]} for r in cur.fetchall()]
    return {"rows": rows}


@dash_router.get("/highrisk")
def high_risk(window: str = Query("24h")):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"rows": []}
    cur = conn.cursor()
    cur.execute(
        "SELECT ts, intent as action, decision, session_id FROM consent WHERE ts>=? AND risk='high' ORDER BY ts DESC",
        (since,)
    )
    rows = [
        {
            "ts": datetime.utcfromtimestamp(r["ts"]).isoformat()+"Z",
            "action": r["action"],
            "decision": r["decision"],
            "session_id": r["session_id"],
        }
        for r in cur.fetchall()
    ]
    return {"rows": rows}


@dash_router.get("/bandit/reward")
def bandit_reward(window: str = Query("7d")):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"points": []}
    cur = conn.cursor()
    cur.execute("SELECT ts, avg_reward FROM bandit WHERE ts>=? ORDER BY ts ASC", (since,))
    pts = [{"ts": datetime.utcfromtimestamp(r["ts"]).isoformat()+"Z", "avg_reward": r["avg_reward"]} for r in cur.fetchall()]
    return {"points": pts}


@dash_router.get("/bandit/weights")
def bandit_weights(window: str = Query("7d")):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"rows": []}
    cur = conn.cursor()
    cur.execute("SELECT tool, weight, MAX(ts) as ts FROM bandit_weights WHERE ts>=? GROUP BY tool", (since,))
    rows = [{"tool": r["tool"], "weight": r["weight"]} for r in cur.fetchall()]
    return {"rows": rows}


@dash_router.get("/rag/quality")
def rag_quality(window: str = Query("24h")):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"evidence_rate": 0.0}
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM events_raw WHERE ts>=? AND type='rag'", (since,))
    total = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM events_raw WHERE ts>=? AND type='rag' AND outcome='success' AND evidences>=1", (since,))
    with_ev = cur.fetchone()[0] or 0
    rate = (with_ev/total) if total else 0.0
    return {"evidence_rate": round(rate, 4)}


@dash_router.get("/rag/top-chunks")
def rag_top_chunks(window: str = Query("24h"), limit: int = Query(20, ge=1, le=100)):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"rows": []}
    cur = conn.cursor()
    cur.execute(
        """
        SELECT doc, chunk_idx, COUNT(*) AS hits
        FROM rag_hits
        WHERE ts>=?
        GROUP BY doc, chunk_idx
        ORDER BY hits DESC
        LIMIT ?
        """,
        (since, limit),
    )
    rows = [{"doc": r["doc"], "chunk": r["chunk_idx"], "hits": r["hits"]} for r in cur.fetchall()]
    return {"rows": rows}


class AuditVerifyReq(BaseModel):
    path: str = "data/audit.log"

@dash_router.post("/audit/verify")
def audit_verify(req: AuditVerifyReq):
    from subprocess import run, PIPE
    # Calls the bundled CLI (audit_verify.py) and returns result code + output
    p = run(["python", "audit_verify.py", req.path], stdout=PIPE, stderr=PIPE, text=True)
    return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
