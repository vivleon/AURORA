## 🤖 Aurora 자가학습 모듈 설계서 (Bandit-Lite 기반)

### 1️⃣ 개요
Aurora의 자가학습 모듈은 **강화학습 전체를 단순화한 경량형 구조**로, RL 대신 **Multi-Armed Bandit (MAB)** 원리를 사용한다. 목적은 “사용자의 만족도, 성공률, 지연시간 등”을 기반으로 도구/프롬프트 선택 확률을 최적화하는 것이다.

- **목표:** 성능 향상, 반복 태스크 최적화, 비효율적 툴 조합 자동 감축
- **기반 모델:** Thompson Sampling / LinUCB
- **학습 데이터:** 감사로그 및 성공/실패 피드백

---

### 2️⃣ 모듈 구성
| 구성요소 | 설명 |
|-----------|------|
| **Logger** | 모든 태스크 실행결과를 기록 (성공률, 시간, 오류코드) |
| **Analyzer** | 로그 분석 후 가중치 업데이트를 위한 보상값 계산 |
| **Bandit Engine** | 각 툴/프롬프트 조합의 확률적 선택 담당 |
| **Updater** | 업데이트된 가중치를 로컬 저장소(`bandit_state.json`)에 반영 |
| **Shadow Validator** | 변경된 가중치가 실제 개선을 유발하는지 검증 (비활성 상태로 테스트 수행) |

---

### 3️⃣ 데이터 플로우
```
사용자 입력
 → Cognition (Planner/Verifier)
 → Tool Executor (실행)
 → Logger (결과 기록)
 → Analyzer (보상 계산)
 → Bandit Engine (우선순위 조정)
 → Updater (가중치 갱신)
 → Shadow Validator (안정성 검증)
```

---

### 4️⃣ 보상 함수 정의
```
reward = (success * 1.0) - (latency * 0.1) - (error * 0.5) + (feedback_score * 0.5)
```
- **success:** 태스크 정상 완료 시 1, 실패 시 0
- **latency:** 응답 시간(초) 단위 패널티
- **error:** 예외 발생 시 0.5 패널티
- **feedback_score:** 사용자가 만족으로 표시한 경우 +0.5 보상

결과값은 -1.0 ~ +1.5 범위 내 정규화되어 확률 업데이트에 반영된다.

---

### 5️⃣ 학습 로직 (의사코드)
```python
# bandit_engine.py
import random, json, numpy as np

class BanditEngine:
    def __init__(self, tools, state_path="data/bandit_state.json"):
        self.tools = tools
        self.state_path = state_path
        self.state = self._load_state()

    def _load_state(self):
        try:
            with open(self.state_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {tool: {"mean": 0.0, "count": 1} for tool in self.tools}

    def choose_tool(self):
        # Thompson Sampling: 도구별 베타분포에서 샘플링
        samples = {t: random.betavariate(self.state[t]['mean']+1, self.state[t]['count']-self.state[t]['mean']+1) for t in self.tools}
        return max(samples, key=samples.get)

    def update(self, tool, reward):
        s = self.state[tool]
        s['mean'] = (s['mean']*s['count'] + reward) / (s['count']+1)
        s['count'] += 1
        with open(self.state_path, 'w') as f:
            json.dump(self.state, f, indent=2)
```

---

### 6️⃣ Shadow Validation 메커니즘
- 업데이트된 가중치의 조합을 실제 환경에 바로 적용하지 않고, **섀도우 환경에서 병렬 시뮬레이션**.
- 기존 정책 대비 개선율이 `+5% 이상`일 때만 프로덕션 반영.
- 모든 검증 로그는 `bandit_shadow.log`에 보관.

---

### 7️⃣ 데이터 구조
**bandit_state.json**
```json
{
  "browser.navigate": {"mean": 0.72, "count": 35},
  "files.read": {"mean": 0.63, "count": 41},
  "nlp.summarize": {"mean": 0.89, "count": 57}
}
```

---

### 8️⃣ 통합 포인트
- **Cognition 모듈** → Tool Planner 단계에서 BanditEngine 호출 (`choose_tool()`)
- **Logger** → 실행 후 Analyzer를 통해 보상 계산 후 BanditEngine.update()
- **Dashboard** → 가중치 평균/승률/지연 통계 시각화

---

### 9️⃣ 발전 로드맵
| 단계 | 확장 기능 |
|-------|-------------|
| 1 | Bandit-Lite (단일 툴 선택 확률) |
| 2 | Contextual Bandit (문맥 기반 가중치, LinUCB) |
| 3 | Multi-objective Optimization (성공률+에너지+시간) |
| 4 | Continual Learning (가중치 이동 평균 + decay) |
| 5 | Federated Aggregation (다중 기기 간 동기화) |

---

### ✅ 기대 효과
- 사용자 피드백 없이도 실행 성공률 향상
- 실패 패턴 자동 감축 → 반복작업 자동 최적화
- 보안·동의 체계와 충돌 없이 작동 (읽기 전용 로그 기반)
- 완전한 로컬 학습 → 데이터 외부 전송 없음

