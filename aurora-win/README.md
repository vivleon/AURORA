AURORA (Windows Self-Evolving Personal Assistant)

이 문서는 AURORA 프로젝트의 Windows 11 로컬 실행 가이드입니다.
(상세 가이드: docs/aurora_installation_guide.md [cite: vivleon/aurora/AURORA-main/aurora-win/docs/aurora_installation_guide.md])

1. 필수 구성 요소

Python 3.11+

Tesseract OCR (환경 변수 TESSERACT_PATH 설정 필요)

Redis (대시보드 및 실시간 SSE용, docker run -p 6379:6379 redis:7-alpine)

2. 설치

# 1. 가상환경 생성 및 활성화
python -m venv .venv
.\.venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. Playwright 브라우저 설치
python -m playwright install chromium

# 4. (중요) 데이터베이스 스키마 초기화
# data/metrics.db 파일이 생성됩니다.
sqlite3 data/metrics.db < schema.sql

# 5. (선택) KPI 뷰 생성 (대시보드 성능 향상)
sqlite3 data/metrics.db < kpi_views.sql


3. 환경 변수 설정

루트 디렉터리에 .env 파일을 생성하고, app/tools/mail.py [cite: vivleon/aurora/AURORA-main/aurora-win/app/tools/mail.py]가 사용할 SMTP 설정을 입력합니다. (.env.example 참조)

# .env
REDIS_URL="redis://localhost:6379/0"
TESSERACT_PATH="C:\Program Files\Tesseract-OCR\tesseract.exe"

# 이메일 발송(mail.send) 기능 사용 시
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USER="your-email@gmail.com"
SMTP_PASS="your-app-password"


4. 실행

# 1. (권장) 로컬 LLM 서버 실행 (별도 터미널)
# (models/bin/llama-server.exe 필요)
.\start_local_models.bat

# 2. 메인 FastAPI 서버 실행
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload


5. 테스트

# 1. API 스모크 테스트 (Node.js 필요)
node scripts/smoke.mjs [http://127.0.0.1:8000](http://127.0.0.1:8000)

# 2. Pytest 통합 테스트
pytest tests/integration/test_api_flow.py

# 3. Playwright E2E 테스트
npx playwright test --project=chromium
