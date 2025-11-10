"""
Aurora Weekly Audit Compaction
- Archives audit.log entries older than 7 days into gz snapshot and keeps recent lines
- Preserves hash chain by reseeding the first remaining record's prev=""
- Usage: python audit_compact_weekly.py --in data/audit.log --out data/archive
"""
from __future__ import annotations
import argparse, gzip, json
from datetime import datetime, timedelta
from pathlib import Path


def parse_ts(rec) -> datetime:
    ts = rec.get("event", {}).get("ts")
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/audit.log")
    ap.add_argument("--out", dest="out_dir", default="data/archive")
    args = ap.parse_args()

    inp = Path(args.inp)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not inp.exists():
        print(f"[WARN] no audit log at {inp}")
        return

    lines = [json.loads(l) for l in inp.read_text("utf-8").splitlines() if l.strip()]
    cutoff = datetime.utcnow() - timedelta(days=7)

    old = [l for l in lines if parse_ts(l) < cutoff]
    new = [l for l in lines if parse_ts(l) >= cutoff]

    if old:
        week = cutoff.isocalendar().week
        gz_path = out_dir / f"audit_until_w{week}.jsonl.gz"
        with gzip.open(gz_path, "wt", encoding="utf-8") as gz:
            for l in old:
                gz.write(json.dumps(l, separators=(",", ":")) + "\n")
        print(f"[OK] archived {len(old)} records → {gz_path}")

    # reseed chain for new part
    for i, rec in enumerate(new):
        if i == 0:
            rec["prev"] = ""
        # recompute hash from event
        ev = rec.get("event", {})
        rec["hash"] = __import__("hashlib").sha256(json.dumps(ev, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    inp.write_text("\n".join(json.dumps(r, separators=(",", ":")) for r in new) + ("\n" if new else ""), "utf-8")
    print(f"[OK] kept {len(new)} recent records, chain reseeded")


if __name__ == "__main__":
    main()
