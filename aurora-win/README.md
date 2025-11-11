## Quick Start (Windows 11)

```powershell
# 0) venv
python -m venv .venv
.\.venv\Scripts\activate

# 1) deps
pip install -r requirements.txt
python -m playwright install chromium

# 2) infra (Redis / Docker)
# 옵션 A: 로컬 설치 사용
# 옵션 B: Docker
docker run -d --name aurora-redis -p 6379:6379 redis:7-alpine

# 3) .env 구성 (.env.example 참고)
# - TESSERACT_PATH는 / 또는 \\ 사용
# - mail.py는 SMTP 전송을 하지 않음(From 표시에만 SMTP_USER 사용)

# 4) 프리플라이트 (DB 스키마/KPI/라우터/경로 점검)
pwsh ./scripts/preflight.ps1

# 5) (선택) 로컬 LLM 서버
.\start_local_models.bat  # 필요 시

# 6) API 서버 실행
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
