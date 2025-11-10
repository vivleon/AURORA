"""
Aurora Audit Log Verifier
- JSONL append-only log with hash chain integrity
- Usage: python audit_verify.py data/audit.log
"""

import hashlib, json, sys, pathlib

RESET = "\x1b[0m"
GREEN = "\x1b[92m"
RED = "\x1b[91m"
YELLOW = "\x1b[93m"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def verify_chain(path: pathlib.Path) -> int:
    prev_hash = ""
    ok_count = 0
    with path.open("rb") as f:
        for i, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"{RED}[ERR]{RESET} line {i}: invalid JSON: {e}")
                return 2

            rec_prev = rec.get("prev", "")
            if rec_prev != prev_hash:
                print(f"{RED}[FAIL]{RESET} line {i}: prev mismatch (expected {prev_hash[:8]}, got {rec_prev[:8]})")
                return 3

            # compute current hash over the event payload only (canonicalized)
            event_bytes = json.dumps(rec.get("event", {}), sort_keys=True, separators=(",", ":")).encode()
            curr_hash = sha256_bytes(event_bytes)

            if rec.get("hash") != curr_hash:
                print(f"{RED}[FAIL]{RESET} line {i}: hash mismatch (expected {curr_hash[:8]}, got {str(rec.get('hash'))[:8]})")
                return 4

            prev_hash = curr_hash
            ok_count += 1

    print(f"{GREEN}[OK]{RESET} verified {ok_count} records, chain intact")
    return 0


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <audit_log_path>")
        sys.exit(1)
    path = pathlib.Path(sys.argv[1])
    if not path.exists():
        print(f"{YELLOW}[WARN]{RESET} file not found: {path}")
        sys.exit(1)
    rc = verify_chain(path)
    sys.exit(rc)


if __name__ == "__main__":
    main()
