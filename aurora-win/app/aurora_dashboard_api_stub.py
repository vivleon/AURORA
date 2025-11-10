"""
Aurora Dashboard API Stub
- Implements GET /dash/* endpoints used by dashboards.json
- Reads from SQLite (metrics.db) if present; otherwise returns safe placeholders
- Mount into FastAPI as a router: app.include_router(dash_router, prefix="/dash")
"""
from __future__ import annotations
import sqlite3
import json
import time
import statistics
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple

from fastapi import APIRouter, Query, Body
from pydantic import BaseModel

DB_PATH = Path(os.getenv("METRICS_DB_PATH", "data/metrics.db"))

dash_router = APIRouter()

# ------------------------- helpers -------------------------

def _connect():
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(DB_PATH.as_posix())
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"[Dashboard API ERROR] Failed to connect to DB: {e}")
        return None


def _window_to_ts(window: str) -> float:
    # window in forms like '1h', '24h', '7d'
    unit = window[-1].lower()
    val = 1
    try:
        val = int(window[:-1])
    except ValueError:
        pass # 기본값 1 사용
        
    now = datetime.utcnow()
    if unit == 'm':
        delta = timedelta(minutes=val)
    elif unit == 'h':
        delta = timedelta(hours=val)
    elif unit == 'd':
        delta = timedelta(days=val)
    else:
        delta = timedelta(hours=1) # 기본값 1시간
    return (now - delta).timestamp()


# ------------------------- models -------------------------
class KPIResponse(BaseModel):
    kpi: Dict[str, Any]

class ConsentTimelineItem(BaseModel):
    ts: str
    decision: str

class ErrorRow(BaseModel):
    tool: str | None
    err_code: str | None
    count: int

# ------------------------- endpoints -------------------------
@dash_router.get("/kpi", response_model=KPIResponse)
def get_kpi(window: str = Query("1h")):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        # DB가 준비되지 않았을 때 플레이스홀더 반환
        return {"kpi": {"success": 0.0, "blocked": 0.0, "p95_ms": 0}}
    try:
        cur = conn.cursor()
        cur.execute("SELECT outcome, latency_ms FROM events_raw WHERE ts >= ?", (since,))
        rows = cur.fetchall()
    except sqlite3.Error as e:
        print(f"[Dashboard API ERROR] /kpi: {e}")
        rows = [] # 오류 시 빈 목록
    finally:
        if conn:
            conn.close()

    lat = [r["latency_ms"] for r in rows if r["latency_ms"] is not None and r["latency_ms"] >= 0]
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
        
    try:
        cur = conn.cursor()
        if tool:
            cur.execute("SELECT tool, latency_ms FROM events_raw WHERE ts >= ? AND tool=?", (since, tool))
        else:
            cur.execute("SELECT tool, latency_ms FROM events_raw WHERE ts >= ?", (since,))
        rows = cur.fetchall()
    except sqlite3.Error as e:
        print(f"[Dashboard API ERROR] /latency: {e}")
        rows = []
    finally:
        if conn:
            conn.close()
            
    buckets: Dict[str, List[int]] = {}
    for r in rows:
        if r["latency_ms"] is None or r["latency_ms"] < 0: continue
        buckets.setdefault(r["tool"] or "unknown", []).append(int(r["latency_ms"]))
        
    data = []
    for k, v in buckets.items():
        if not v:
            continue
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
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT ts, decision FROM consent WHERE ts >= ? ORDER BY ts ASC", (since,))
        items = [{"ts": datetime.utcfromtimestamp(r["ts"]).isoformat()+"Z", "decision": r["decision"]} for r in cur.fetchall()]
    except sqlite3.Error as e:
        print(f"[Dashboard API ERROR] /consent/timeline: {e}")
        items = []
    finally:
        if conn:
            conn.close()
            
    return {"items": items}


@dash_router.get("/errors/top")
def errors_top(window: str = Query("1h"), limit: int = Query(10, ge=1, le=100)):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"rows": []}
        
    try:
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
    except sqlite3.Error as e:
        print(f"[Dashboard API ERROR] /errors/top: {e}")
        rows = []
    finally:
        if conn:
            conn.close()
            
    return {"rows": rows}


@dash_router.get("/highrisk")
def high_risk(window: str = Query("24h")):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"rows": []}
        
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT ts, action, decision, session_id FROM consent WHERE ts>=? AND risk='high' ORDER BY ts DESC",
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
    except sqlite3.Error as e:
        print(f"[Dashboard API ERROR] /highrisk: {e}")
        rows = []
    finally:
        if conn:
            conn.close()
            
    return {"rows": rows}


@dash_router.get("/bandit/reward")
def bandit_reward(window: str = Query("7d")):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"points": []}
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT ts, avg_reward FROM bandit WHERE ts>=? ORDER BY ts ASC", (since,))
        pts = [{"ts": datetime.utcfromtimestamp(r["ts"]).isoformat()+"Z", "avg_reward": r["avg_reward"]} for r in cur.fetchall()]
    except sqlite3.Error as e:
        print(f"[Dashboard API ERROR] /bandit/reward: {e}")
        pts = []
    finally:
        if conn:
            conn.close()
            
    return {"points": pts}


@dash_router.get("/bandit/weights")
def bandit_weights(window: str = Query("7d")):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"rows": []}
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT tool, weight, MAX(ts) as ts FROM bandit_weights WHERE ts>=? GROUP BY tool", (since,))
        rows = [{"tool": r["tool"], "weight": r["weight"]} for r in cur.fetchall()]
    except sqlite3.Error as e:
        print(f"[Dashboard API ERROR] /bandit/weights: {e}")
        rows = []
    finally:
        if conn:
            conn.close()
            
    return {"rows": rows}


@dash_router.get("/rag/quality")
def rag_quality(window: str = Query("24h")):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"evidence_rate": 0.0}
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM events_raw WHERE ts>=? AND type='rag'", (since,))
        total = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM events_raw WHERE ts>=? AND type='rag' AND outcome='success' AND evidences>=1", (since,))
        with_ev = cur.fetchone()[0] or 0
    except sqlite3.Error as e:
        print(f"[Dashboard API ERROR] /rag/quality: {e}")
        total, with_ev = 0, 0
    finally:
        if conn:
            conn.close()
            
    rate = (with_ev/total) if total else 0.0
    return {"evidence_rate": round(rate, 4)}


@dash_router.get("/rag/top-chunks")
def rag_top_chunks(window: str = Query("24h"), limit: int = Query(20, ge=1, le=100)):
    since = _window_to_ts(window)
    conn = _connect()
    if not conn:
        return {"rows": []}
        
    try:
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
    except sqlite3.Error as e:
        print(f"[Dashboard API ERROR] /rag/top-chunks: {e}")
        rows = []
    finally:
        if conn:
            conn.close()
            
    return {"rows": rows}


class AuditVerifyReq(BaseModel):
    path: str = "data/audit.log"

@dash_router.post("/audit/verify")
def audit_verify(req: AuditVerifyReq):
    # audit_verify.py 스크립트를 직접 호출합니다.
    from subprocess import run, PIPE
    
    # app/main.py가 있는 루트에서 scripts/audit_verify.py를 찾도록 경로 수정
    script_path = "scripts/audit_verify.py"
    if not Path(script_path).exists():
        script_path = Path(__file__).parent.parent / "scripts" / "audit_verify.py"
        if not script_path.exists():
            return {"returncode": -1, "stdout": "", "stderr": "audit_verify.py not found"}
            
    # 'python' 대신 sys.executable을 사용하여 현재 venv의 Python을 사용
    import sys
    
    p = run([sys.executable, str(script_path), req.path], stdout=PIPE, stderr=PIPE, text=True, encoding='utf-8')
    return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
