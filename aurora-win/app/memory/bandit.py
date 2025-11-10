import json
import random
import os
from typing import List, Dict, Set, Optional

class Bandit:
    """
    [업그레이드] Contextual Bandit (Thompson Sampling)
    'docs/aurora_self_learning_module.md'의 설계를 기반으로,
    'context_key'를 실제 사용하여 컨텍스트별 가중치를 관리합니다.
    
    - state 구조: {"context_key": {"tool_name": {"alpha": 1.0, "beta": 1.0}}}
    - 'context_key' 예: "intent:schedule", "time:morning"
    """
    def __init__(self, state_path="data/bandit_state.json"):
        self.state_path = state_path
        # [수정] 중첩된 Dict 구조로 변경
        self.state: Dict[str, Dict[str, Dict[str, float]]] = {}
        self.tools: Set[str] = set()
        self._load_state()

    def _load_state(self):
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    self.state = json.load(f)
                    # 모든 컨텍스트의 모든 도구를 tools 집합에 추가
                    for context, tools in self.state.items():
                        self.tools.update(tools.keys())
            else:
                self.state = {}
        except (IOError, json.JSONDecodeError):
            print(f"[WARN] Failed to load bandit state from {self.state_path}. Starting fresh.")
            self.state = {}

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
        except IOError as e:
            print(f"[ERROR] Failed to save bandit state: {e}")

    def _get_or_init_state(self, context_key: str, tool: str) -> Dict[str, float]:
        """
        [신규] 컨텍스트와 도구에 해당하는 state를 가져오거나 초기화합니다.
        """
        if context_key not in self.state:
            self.state[context_key] = {}
            
        if tool not in self.state[context_key]:
            # (alpha: 1, beta: 1)로 시작 (균일 분포)
            self.state[context_key][tool] = {"alpha": 1.0, "beta": 1.0}
            
        self.tools.add(tool)
        return self.state[context_key][tool]

    def select(self, context_key: Optional[str], tools: List[str]) -> str:
        """
        Thompson Sampling: [수정] 'context_key'를 사용하여 해당 컨텍스트의
        베타분포에서 샘플링하여 가장 높은 값을 반환합니다.
        """
        if not tools:
            raise ValueError("No tools provided to select from")

        # [수정] 컨텍스트 키가 없으면 'global' 컨텍스트 사용
        ctx = context_key or "global"

        samples: Dict[str, float] = {}
        for tool in tools:
            s = self._get_or_init_state(ctx, tool)
            # 베타 분포 (alpha, beta)에서 샘플링
            try:
                samples[tool] = random.betavariate(s["alpha"], s["beta"])
            except ValueError: # alpha/beta가 0 이하일 경우 대비
                samples[tool] = 0.5 
        
        return max(samples, key=samples.get)

    def update(self, context_key: Optional[str], tool: str, reward: float):
        """
        [수정] 'context_key'를 사용하여 해당 컨텍스트의 분포(alpha/beta)를 업데이트합니다.
        보상은 [0, 1] 범위로 정규화되어야 합니다.
        """
        # [수정] 컨텍스트 키가 없으면 'global' 컨텍스트 사용
        ctx = context_key or "global"
        
        s = self._get_or_init_state(ctx, tool)

        # 설계 문서의 보상 (-1.0 ~ +1.5)을 [0, 1]로 정규화
        normalized_reward = (reward + 1.0) / 2.5 
        normalized_reward = max(0.0, min(1.0, normalized_reward)) # 클리핑

        # 0.5를 기준으로 성공/실패로 이진화 (간단한 방법)
        if normalized_reward > 0.5:
            s["alpha"] += 1.0
        else:
            s["beta"] += 1.0
        
        self._save_state()