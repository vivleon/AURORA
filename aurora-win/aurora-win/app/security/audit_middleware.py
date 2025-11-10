"""
Aurora Audit Writer Middleware
- FastAPI middleware that writes append-only JSONL with hash chain
- Integrate: app.add_middleware(AuditMiddleware, log_path="data/audit.log")
"""
from __future__ import annotations
import json, hashlib, threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, log_path: str = "data/audit.log"):
        super().__init__(app)
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._prev_hash = self._load_prev_hash()

    def _load_prev_hash(self) -> str:
        if not self.log_path.exists():
            return ""
        try:
            # read last non-empty line
            with self.log_path.open("rb") as f:
                f.seek(0, 2)
                size = f.tell()
                block = min(8192, size)
                while size > 0:
                    size -= block
                    f.seek(size)
                    chunk = f.read(block)
                    lines = chunk.splitlines()
                    if lines:
                        last = lines[-1].strip()
                        if last:
                            rec = json.loads(last)
                            return rec.get("hash", "")
        except Exception:
            return ""
        return ""

    @staticmethod
    def _sha256_event(event: Dict[str, Any]) -> str:
        b = json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(b).hexdigest()

    def _append_event(self, event: Dict[str, Any]):
        event.setdefault("ts", datetime.utcnow().isoformat()+"Z")
        line = {
            "event": event,
            "prev": self._prev_hash,
        }
        curr_hash = self._sha256_event(event)
        line["hash"] = curr_hash
        with self._lock:
            with self.log_path.open("ab") as f:
                f.write((json.dumps(line, separators=(",", ":")) + "\n").encode())
            self._prev_hash = curr_hash

    async def dispatch(self, request: Request, call_next):
        # Pre: trace seeds
        meta = {
            "type": "http",
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else None,
        }
        try:
            response: Response = await call_next(request)
            meta.update({
                "status": response.status_code,
                "outcome": "success" if response.status_code < 400 else "error"
            })
        except Exception as e:
            meta.update({"status": 500, "outcome": "error", "err": type(e).__name__})
            self._append_event(meta)
            raise
        else:
            self._append_event(meta)
            return response
