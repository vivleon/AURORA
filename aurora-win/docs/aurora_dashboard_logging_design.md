# 📊 Aurora Dashboard & Logging System Design

## 1) 목적
운영 가시성과 신뢰성을 확보하기 위해 **실행 현황, 성능, 보안/동의 이력, 자가학습 효과**를 단일 대시보드로 통합한다. 모든 기록은 **불변성(append-only + 해시체인)**을 보장하며, 개인 데이터는 로컬 우선으로 관리한다.

---

## 2) 핵심 지표(KPIs)
- **Task Success Rate** = 완료/시도
- **Blocked Rate** = 정책/동의 미충족으로 차단된 비율
- **P50/P95 Latency** (전체 / 툴별 / RAG / 브라우저 / OCR)
- **Consent Actions** (approve/deny/expire)
- **Bandit Improvement** (최근 7일 평균 보상 변화, 툴별 가중치)
- **Error Matrix** (툴·원인·코드)

---

## 3) 아키텍처 개요
```
[App Services]
  ├─ Cognition (Planner/Verifier/Executor)
  ├─ Tools (calendar/mail/browser/files/ocr/nlp/system)
  └─ Policy+Consent Engine
        │  events(JSON)
        ▼
[Event Collector]  →  [Event Bus(Async)]  →  [Storage]
                          │                   ├─ audit.log (append-only + hash)
                          │                   ├─ metrics.db (SQLite)
                          │                   └─ traces.parquet (optional)
                          ▼
[Aggregator] → rollups (1m/5m/1h) → [Dashboard API]
                                         ▼
                                     [Web UI: Dashboard]
```

---

## 4) 이벤트 스키마(요약)
```json
{
  "ts": "2025-11-07T12:34:56.789Z",
  "type": "task|tool|policy|consent|error|bandit",
  "session_id": "uuid",
  "user": "local",
  "intent": "mail.send",
  "plan_id": "uuid",
  "tool": "mail.compose",
  "args_hash": "sha256(...)",
  "outcome": "success|blocked|error",
  "latency_ms": 842,
  "err_code": null,
  "consent_id": "uuid|null",
  "risk": "low|medium|high",
  "reward": 0.78
}
```

### 감사 로그(audit.log) 포맷
- **라인단위 JSONL** + `prev_hash` 체인
```json
{"ts":"...","event":{...},"prev":"e3b0...","hash":"c1a2..."}
```
- 검증 CLI: `audit_verify.py` → 전 라인 sha256 체인 검증

---

## 5) 저장소 설계
- **metrics.db (SQLite)**
  - 테이블: `events_raw`, `rollup_1m`, `rollup_5m`, `rollup_1h`, `consent`, `errors`, `bandit`
  - 인덱스: `ts`, `type`, `tool`, `intent`
- **audit.log (JSONL)**: 불변 기록, 주기적 스냅샷/압축
- **traces.parquet (선택)**: 성능 추적/리플레이용
- **보관정책**: raw 30일, rollup 180일, audit 365일(+암호화 아카이브)

---

## 6) 대시보드 패널 구성
1. **Overview**: Success/Blocked, P95, 동의 현황, 최근 알림
2. **Performance**: 툴별/경로별 지연 히트맵, 에러 TopN
3. **Security & Consent**: 승인/거부/만료 타임라인, 고위험 작업 로그
4. **Bandit Analytics**: 툴 가중치, 7일 보상 변화, 섀도우/프로덕션 비교
5. **RAG Quality**: 근거 포함률, 재질의율, 청크 히트 통계

---

## 7) 알림/임계치(예시)
- Success Rate < 75% (1h) → 경고
- P95 Latency > 4s (10m) → 경고
- High-risk 실행 동의 누락 발생 → 즉시 알림
- Error Spike (평균+3σ, 5m) → 경고
- Bandit 개선율 0% (3일 연속) → 점검 요청

---

## 8) API 엔드포인트(요약)
- `GET /dash/kpi?window=1h`
- `GET /dash/latency?tool=browser.scrape&p=95&window=24h`
- `GET /dash/consent/timeline?window=7d`
- `GET /dash/bandit/weights?window=7d`
- `POST /dash/audit/verify` (hash chain 검증)

---

## 9) 보안/프라이버시
- 로컬 우선 저장, PII 마스킹(메일/경로/토큰)
- 동의 이벤트는 별도 암호화 영역에 저장
- 감사 로그는 별도 키로 **암호화 압축**(선택)
- 포렌식 스냅샷 생성 기능(정책 위반/침입 의심 시)

---

## 10) 운영 및 유지보수
- **롤업 스케줄러**: 1m/5m/1h 집계 작업
- **컴팩션**: audit.log 주간 압축/아카이브
- **헬스체크**: 수집기/집계기 지연 감시
- **리포트**: 주간 PDF 리포트 생성(선택)

---

## 11) 성능 예산
- Ingest 처리량: ≥ 200 ev/s (로컬)
- 집계 작업: 1분 윈도우 < 500ms
- 대시보드 쿼리: P95 < 800ms (1h 윈도우)

---

## 12) 실패/복구 시나리오
- 수집기 다운 → 로컬 큐(디스크버퍼)로 유실 방지
- DB 락/오류 → 라이터 백오프 + 재시도, 감시 알림
- audit 손상 → 마지막 유효 스냅샷으로 롤백, 해시 검증

---

## 13) 인터페이스 예시(JSON)
```json
{
  "kpi": {"success": 0.88, "blocked": 0.04, "p95_ms": 2100},
  "consent": {"approve": 7, "deny": 1, "expire": 2},
  "bandit": {"browser.scrape": 0.74, "nlp.summarize": 0.86}
}
```

---

## 14) 향후 확장
- OpenTelemetry 호환 트레이싱
- eBPF 기반 시스템 콜 텔레메트리(고급 옵션)
- 시간여행 디버깅(시나리오 리플레이)
- 정책 위반에 대한 자동 플레이북(격리/롤백/키회전)

