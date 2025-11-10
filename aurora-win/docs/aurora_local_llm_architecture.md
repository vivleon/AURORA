# 🧩 Aurora 로컬 LLM 연동 아키텍처 (Windows)

## 1) 목표
- **로컬 퍼스트** 원칙을 유지하면서, 질의/요약/분류/의도판단을 **오프라인에서도 수행**
- 성능·품질·비용을 균형 있게 달성하기 위한 **하이브리드 라우팅**(Local ↔ Cloud)
- 안전/정책 준수: 모든 로컬 모델은 **서명 검증**, 권한/동의 엔진과 통합

---

## 2) 구성 옵션
### (A) 완전 로컬
- 엔진: **llama.cpp**(GGUF), **ONNX Runtime(DirectML)**
- 모델: 3B~7B(4bit/5bit) 지향, 예: Llama-3.2 3B, Phi-3-mini, Qwen2.5 3B
- 장점: 오프라인, 프라이버시 최고
- 단점: 긴 텍스트/복잡 작업 품질 한계

### (B) 하이브리드(권장)
- 라우터가 작업 유형/길이/리스크에 따라 Local/Cloud 선택
- 예: 분류/의도/RAG 후처리 → Local, 장문 생성/복합 계획 → Cloud

---

## 3) Windows 가속
- **DirectML(ONNX Runtime)**: NVIDIA/AMD/Intel GPU 공통 가속
- **CPU 경량 경로**: 4bit 양자화 + AVX2/AVX512
- 권장: RAM 16GB+, VRAM 6~8GB(가속 시)

---

## 4) 라우팅 정책(의사결정)
```
if risk == high → cloud=False (로컬 우선)
elif tokens_in < 1.5k and task in {intent, classify, extract, short_summarize} → local
elif latency_slo < 1.5s → local
else → cloud
```
- 정책은 `model_router.json`으로 관리, UI에서 동적 변경 가능

---

## 5) 컴포넌트
```
[Cognition]
  ├─ IntentClassifier (local small)
  ├─ Planner (cloud/local selectable)
  ├─ Verifier (rule-based)
  └─ Generator (local or cloud)
       │
       ├─ Local Engines
       │    ├─ llama.cpp server (GGUF)
       │    └─ onnxruntime + DirectML (Llama/phi/qwen)
       │
       └─ Cloud Providers (fallback)
```

- **Embedding**: 로컬 e5-small/mini(ONNX) → FAISS 인덱스
- **Tokenizer**: sentencepiece(BPE) 공용, 모델 번들 내장

---

## 6) 모델 관리
- 저장소: `models/` (서브폴더: `llm/`, `embedding/`, `tts/`, `asr/`)
- 메타: `model_manifest.json` (이름, 버전, 해시, 서명, 메모리/VRAM 요구, 권장 토큰 한도)
- 설치: `model_fetch.py` (해시 검증, 서명 확인 후 배치)
- 롤백: `model_switch --version x.y.z`

예시 메타
```json
{
  "name": "phi3-mini-4bit-gguf",
  "version": "1.1.0",
  "format": "gguf",
  "hash": "sha256:...",
  "signature": "ed25519:...",
  "ram_gb": 6,
  "vram_gb": 0,
  "max_context": 4096,
  "tasks": ["classify","summarize","generate_short"]
}
```

---

## 7) 호출 계약(추상화)
```json
{
  "model": "local://phi3-mini-gguf",
  "task": "summarize",
  "prompt": "...",
  "max_tokens": 256,
  "temperature": 0.4,
  "slo_ms": 1500,
  "risk": "low"
}
```

---

## 8) 메모리/성능 예산(현실치)
- 3B 4bit GGUF: **RAM ~4–6GB**, 토큰속도 20–60 tok/s(CPU), GPU DML 가속 시 2–3배
- 7B 4bit GGUF: **RAM ~8–12GB**, tok/s 10–30(CPU), GPU 2배+
- 임베딩(e5-small): 배치 64 기준 10–30K 청크/분 인덱싱(가속 시)

---

## 9) 안전/정책 연동
- 로컬 LLM 호출 전 **Policy 스코프 검사**(risk high인 경우 생성 금지/로컬 고정)
- 프롬프트 선필터/후필터(금칙어, 민감정보 마스킹)
- 출력 검증: Verifier가 정규식/룰로 포맷 검사(예: JSON schema)

---

## 10) 로드/언로드 전략
- **온디맨드 로딩**: 최초 호출 시 메모리에 로딩, 10분 비사용 시 언로드
- **Warm-up**: 자주 쓰는 소형 모델 상시 대기, 대형은 필요 시 로딩
- **핀 고정**: 중요 세션 동안 강제 유지

---

## 11) 개발/운영 플로우
1. `model_fetch.py`로 모델 다운로드(해시·서명 검증)
2. `model_manifest.json`에 등록, Router에 정책 반영
3. 로컬 엔진 기동: `llama.cpp --server` 또는 ONNX Runtime 세션 준비
4. 통합테스트: intent/classify/summarize 20개 리그
5. 대시보드에서 토큰속도/지연 그래프 확인

---

## 12) 장애/대비
- 로컬 엔진 실패 → 즉시 클라우드 폴백(정책 허용 시)
- 메모리 부족 → 언로드 후 재시작, 경고 알림
- 출력 비정상 → 재시도/대체 모델 라우팅

---

## 13) 라우터 정책 예시
```json
{
  "router_version": "1.0",
  "defaults": {"target": "local", "slo_ms": 1500},
  "rules": [
    {"if": {"risk": "high"}, "then": {"target": "local"}},
    {"if": {"task": "intent"}, "then": {"target": "local", "model": "phi3-mini-gguf"}},
    {"if": {"task": "summarize", "tokens_in": {"lte": 1500}}, "then": {"target": "local"}},
    {"if": {"task": "generate_long"}, "then": {"target": "cloud"}}
  ]
}
```

---

## 14) 향후 확장
- Mixture-of-Experts(LoRA experts) 온디맨드 조합
- KV-Cache 디스크 스와핑(긴 문서 요약 최적화)
- Whisper/EdgeTTS 로컬 음성 파이프라인
- Federated distillation: 다중 장치간 로컬 지식 동기화

---

## ✅ 결론
Windows 환경에서 **DirectML/ONNX/llama.cpp** 기반의 로컬 LLM을 **안전하게** 통합하고, 작업 특성에 따라 **하이브리드 라우팅**으로 품질과 비용을 최적화한다. 모든 모델은 **서명·해시**로 검증되며, 정책 엔진과 결합해 프라이버시와 통제권을 보장한다.

