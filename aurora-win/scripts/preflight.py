# scripts/preflight.py
import json, os, socket, sqlite3, sys, shutil, subprocess
from pathlib import Path
from app.core.config import settings, ensure_directories

FAIL = 0
def fail(msg):  # noqa
    global FAIL
    print(f"[FAIL] {msg}")
    FAIL += 1

def ok(msg):
    print(f"[ OK ] {msg}")

def check_port(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect((host, port))
            return True
        except Exception:
            return False

def main():
    print("=== AURORA Preflight ===")
    ensure_directories()

    # 1) Tesseract
    if settings.TESSERACT_PATH and Path(settings.TESSERACT_PATH).exists():
        ok(f"Tesseract found: {settings.TESSERACT_PATH}")
    else:
        print("[WARN] TESSERACT_PATH not set or not found")

    # 2) Redis
    try:
        import redis  # type: ignore
        r = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5)
        r.ping()
        ok(f"Redis OK: {settings.REDIS_URL}")
    except Exception as e:
        fail(f"Redis not reachable: {settings.REDIS_URL} ({e})")

    # 3) DB & schema
    dbp = Path(settings.METRICS_DB_PATH)
    schema = Path("schema.sql")
    if not dbp.exists():
        if schema.exists():
            sqlite3.connect(dbp).close()
            os.system(f'sqlite3 "{dbp}" < "{schema}"')
            ok(f"DB created & schema applied: {dbp}")
        else:
            fail("metrics.db missing and schema.sql not found")
    else:
        ok(f"DB exists: {dbp}")

    # 4) KPI views (optional)
    if Path("kpi_views.sql").exists():
        os.system(f'sqlite3 "{dbp}" < "kpi_views.sql"')
        ok("KPI views ensured")

    # 5) Model router JSON
    mr = Path(settings.MODEL_ROUTER_PATH)
    if mr.exists():
        try:
            json.loads(mr.read_text(encoding="utf-8"))
            ok(f"Model router loaded: {mr}")
        except Exception as e:
            fail(f"Model router invalid JSON: {e}")
    else:
        fail(f"Model router missing: {mr}")

    # 6) Optional local llama servers (8081/8082) probe
    # If you proxy via model_router, this is informational only.
    if check_port("127.0.0.1", 8081):
        ok("Main LLM endpoint (8081) reachable")
    else:
        print("[INFO] 8081 not open (ok if using router)")

    if check_port("127.0.0.1", 8082):
        ok("Intent LLM endpoint (8082) reachable")
    else:
        print("[INFO] 8082 not open (ok if using router)")

    # 7) Files root
    fr = Path(settings.FILES_ROOT)
    if fr.exists() and fr.is_dir():
        ok(f"FILES_ROOT ok: {fr}")
    else:
        fail(f"FILES_ROOT not ready: {fr}")

    # 8) Policy file presence (optional)
    if Path(settings.POLICY_PATH).exists():
        ok("Policy file present")
    else:
        print("[INFO] Policy file not found (optional)")

    print(f"=== Preflight Done: {'OK' if FAIL==0 else 'FAILED'} ===")
    sys.exit(FAIL)

if __name__ == "__main__":
    main()
