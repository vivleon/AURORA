import json
import random
import os
from typing import List, Dict, Set

class Bandit:
    """
    Bandit-Lite (Thompson Sampling)
    'docs/aurora_self_learning_module.md'의 설계에 따라 구현되었습니다.
    보상(reward)은 -1.0 ~ +1.5 범위로 정규화되어야 합니다.
    """
    def __init__(self, state_path="data/bandit_state.json"):
        self.state_path = state_path
        self.state: Dict[str, Dict[str, float]] = {}
        self.tools: Set[str] = set()
        self._load_state()

    def _load_state(self):
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    self.state = json.load(f)
                    self.tools = set(self.state.keys())
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

    def _init_tool(self, tool: str):
        if tool not in self.state:
            # (mean: 0.0, count: 1) 대신 (alpha: 1, beta: 1)로 시작 (균일 분포)
            # reward가 [0, 1] 범위라고 가정. (원래 설계는 -1.0 ~ 1.5)
            # 보상 범위를 [0, 1]로 스케일링 (reward + 1.0) / 2.5
            self.state[tool] = {"alpha": 1.0, "beta": 1.0}
            self.tools.add(tool)

    def select(self, context_key: str, tools: List[str]) -> str:
        """
        Thompson Sampling: 각 도구의 베타분포에서 샘플링하여 가장 높은 값을 반환합니다.
        context_key는 향후 Contextual Bandit을 위해 유지됩니다.
        """
        if not tools:
            raise ValueError("No tools provided to select from")

        samples: Dict[str, float] = {}
        for tool in tools:
            self._init_tool(tool)
            s = self.state[tool]
            # 베타 분포 (alpha, beta)에서 샘플링
            samples[tool] = random.betavariate(s["alpha"], s["beta"])
        
        return max(samples, key=samples.get)

    def update(self, context_key: str, tool: str, reward: float):
        """
        보상(reward)으로 도구의 분포(alpha/beta)를 업데이트합니다.
        보상은 [0, 1] 범위로 정규화되어야 합니다.
        """
        self._init_tool(tool)
        s = self.state[tool]

        # 설계 문서의 보상 (-1.0 ~ +1.5)을 [0, 1]로 정규화
        normalized_reward = (reward + 1.0) / 2.5 
        normalized_reward = max(0.0, min(1.0, normalized_reward)) # 클리핑

        # 0.5를 기준으로 성공/실패로 이진화 (간단한 방법)
        if normalized_reward > 0.5:
            s["alpha"] += 1.0
        else:
            s["beta"] += 1.0
        
        self._save_state()