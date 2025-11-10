"""
Aurora Raw→Rollup Precise P95 Recomputer
- Recomputes P95 latency per bucket directly from raw events (no approximation)
- Updates rollup_1m / rollup_5m / rollup_1h with exact P95
- Safe to run periodically (idempotent upserts)

Usage examples:
  python raw_to_rollup_p95.py --db data/metrics.db --window 3600   # last 1h
  python raw_to_rollup_p95.py --db data/metrics.db --window 86400  # last 24h
  python raw_to_rollup_p95.py --db data/metrics.db --full          # all time (costly)
"""
from __future__ import annotations
import argparse, sqlite3, math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

TABLE_FOR = {60: "rollup_1m", 300: "rollup_5m", 3600: "rollup_1h"}
WINDOWS = [60, 300, 3600]


def percentile(sorted_vals: List[int], q: float) -> int:
    if not sorted_vals:
        return 0
    # nearest-rank method
    k = max(1, math.ceil(q * len(sorted_vals))) - 1
    return int(sorted_vals[min(k, len(sorted_vals)-1)])


def recompute(db: Path, horizon_sec: int | None):
    conn = sqlite3.connect(db.as_posix())
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    now = datetime.utcnow().timestamp()
    since = 0 if horizon_sec is None else (now - horizon_sec)

    cur.execute("SELECT ts, outcome, latency_ms FROM events_raw WHERE ts >= ? AND latency_ms IS NOT NULL ORDER BY ts ASC", (since,))
    rows = cur.fetchall()

    for w in WINDOWS:
        buckets: Dict[int, Dict[str, List[int] | int]] = {}
        for r in rows:
            b = int(r["ts"] // w) * w
            rec = buckets.setdefault(b, {"lat": [], "s": 0, "b": 0, "e": 0})
            rec["lat"].append(int(r["latency_ms"]))
            o = r["outcome"]
            if o == "success": rec["s"] += 1
            elif o == "blocked": rec["b"] += 1
            elif o == "error": rec["e"] += 1

        table = TABLE_FOR[w]
        for b, v in buckets.items():
            v["lat"].sort()
            p95 = percentile(v["lat"], 0.95)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/metrics.db")
    ap.add_argument("--window", type=int, help="seconds horizon (e.g., 3600 for 1h)")
    ap.add_argument("--full", action="store_true", help="recompute all time (may be slow)")
    args = ap.parse_args()

    horizon = None if args.full else (args.window or 3600)
    recompute(Path(args.db), horizon)
    print("[OK] rollups updated with precise P95")

if __name__ == "__main__":
    main()
