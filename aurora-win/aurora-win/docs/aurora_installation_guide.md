## 🧩 Aurora Installation Guide (Windows 11)

### 1️⃣ System Requirements
- **OS:** Windows 10/11 (64-bit)
- **Python:** 3.11+
- **Browser:** Microsoft Edge (WebView2 runtime installed)
- **RAM:** 8GB minimum, 16GB recommended
- **Disk:** 2GB free space (임베딩 + 로그 포함)

---

### 2️⃣ 필수 구성 요소 설치
1. **Python 설치**
   - https://www.python.org/downloads/windows/ 에서 Python 3.11 이상 다운로드
   - 설치 시 `Add Python to PATH` 옵션 체크

2. **Tesseract OCR 설치**
   - https://github.com/UB-Mannheim/tesseract/wiki 에서 Windows용 배포본 설치
   - 설치 경로 예시: `C:\Program Files\Tesseract-OCR`
   - 환경변수 PATH에 추가

3. **Microsoft Edge WebView2 런타임 설치**
   - https://developer.microsoft.com/en-us/microsoft-edge/webview2/#download-section

4. **Visual C++ Build Tools** (Playwright 설치용)
   - https://visualstudio.microsoft.com/visual-cpp-build-tools/

---

### 3️⃣ 프로젝트 설치 절차
1. **리포지토리 클론**
   ```bash
   git clone https://github.com/yourname/aurora-win.git
   cd aurora-win
   ```

2. **가상환경 생성 및 활성화**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **의존성 설치**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Tesseract 경로 환경변수 설정 (예시)**
   ```bash
   setx TESSDATA_PREFIX "C:\Program Files\Tesseract-OCR\tessdata"
   ```

---

### 4️⃣ 실행
1. **FastAPI 서버 실행**
   ```bash
   cd app
   uvicorn main:app --reload --port 8000
   ```

2. **웹 UI 접근**
   - 브라우저 또는 WebView2에서 `http://127.0.0.1:8000` 접속

3. **자동 실행 스크립트 사용 (Windows)**
   - `start.bat` 실행 시 서버 + UI 자동 실행

---

### 5️⃣ 기본 폴더 구조 확인
```
aurora-win/
 ├─ app/
 ├─ webui/
 ├─ data/
 ├─ ocr/
 └─ scripts/
```

---

### 6️⃣ 테스트 및 초기 설정
1. **정책 파일 수정 (`data/policy.json`)**
   - 동의 범위, TTL, 위험도 설정 가능

2. **테스트 실행**
   ```bash
   pytest tests/
   ```

3. **정상 동작 확인 항목**
   - 브라우저 요약 정상
   - OCR 텍스트 추출 정상
   - 동의창 작동 및 로그 기록 정상

---

### 7️⃣ 트러블슈팅
| 증상 | 해결 방법 |
|------|-------------|
| Tesseract 인식 안 됨 | 환경변수 TESSDATA_PREFIX 확인 |
| Playwright 실행 오류 | `playwright install chromium` 재실행 |
| 포트 충돌 | `uvicorn main:app --port 8080` 등 다른 포트 사용 |
| WebUI 미출력 | Edge WebView2 설치 확인 |

---

### ✅ 설치 완료 후
- `http://127.0.0.1:8000` 실행 시 “Aurora is running locally.” 출력되면 성공
- 다음 단계: RAG 인제스트 / 동의 정책 / Bandit 자가학습 활성화

