import time
import json
import hashlib
import os
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable

class AuditMiddleware(BaseHTTPMiddleware):
    """
    FastAPI 미들웨어. 모든 API 요청을 해시체인 감사 로그('data/audit.log')에 기록합니다.
    (app/main.py (통합본)에서 사용됨)
    이 로직은 구형 app/security/hashlog.py [cite: vivleon/aurora/AURORA-main/aurora-win/app/security/hashlog.py]의 로직을 계승합니다.
    """
    def __init__(self, app, log_path: str = "data/audit.log"):
        super().__init__(app)
        self.log_path = log_path
        self.log_dir = os.path.dirname(log_path)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)
        if not os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'w', encoding='utf-8') as f:
                    f.write("")
            except IOError as e:
                print(f"[Audit ERROR] Failed to create audit log file: {e}")
        print(f"[Audit] Middleware initialized. Logging to: {self.log_path}")

    def _get_last_hash(self) -> str:
        """
        로그 파일의 마지막 해시를 읽어옵니다. (동기)
        """
        last_hash = "0" * 64
        try:
            with open(self.log_path, 'rb') as f:
                # 마지막 줄을 효율적으로 찾기
                try:
                    # 파일 끝에서 1024바이트 전으로 이동
                    f.seek(-1024, os.SEEK_END)
                except IOError:
                    # 파일이 1024바이트보다 작으면 처음으로 이동
                    f.seek(0)
                
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].decode('utf-8')
                    last_entry = json.loads(last_line)
                    last_hash = last_entry.get('hash', last_hash)
        except (IOError, IndexError, json.JSONDecodeError, FileNotFoundError):
            # 파일이 비어있거나 손상된 경우, 제네시스 해시 사용
            pass
        return last_hash

    def _record_entry(self, entry_data: dict) -> str:
        """
        새 로그 항목을 해시체인으로 기록합니다. (동기)
        """
        prev_hash = self._get_last_hash()
        
        # 해시 계산 (prev 포함, hash 미포함)
        entry_to_hash = entry_data.copy()
        entry_to_hash["prev"] = prev_hash
        
        raw = json.dumps(entry_to_hash, sort_keys=True).encode('utf-8')
        digest = hashlib.sha256(raw).hexdigest()
        
        # 최종 항목 (prev, hash 포함)
        final_entry = entry_to_hash
        final_entry["hash"] = digest
        
        # 파일에 추가 (JSONL)
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(final_entry, ensure_ascii=False) + "\n")
        except IOError as e:
            print(f"[Audit ERROR] Failed to write audit log: {e}")
            
        return digest

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        # 요청 정보 기록 (중요: body는 로깅하지 않음 - 민감 정보)
        entry = {
            "ts": start_time,
            "actor": request.client.host if request.client else "unknown",
            "action": f"API:{request.method}:{request.url.path}",
            "payload": {"query_params": str(request.query_params)},
        }
        
        response = await call_next(request)
        
        process_time = (time.time() - start_time) * 1000
        
        # 응답 정보 추가
        entry["status_code"] = response.status_code
        entry["latency_ms"] = int(process_time)
        
        # 해시체인 기록 (동기 I/O이므로 스레드에서 실행)
        await asyncio.to_thread(self._record_entry, entry)
        
        return response