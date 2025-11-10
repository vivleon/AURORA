import math, random


class Bandit:
def __init__(self, db, epsilon=0.1):
self.db = db; self.epsilon = epsilon


def select(self, context_key: str, tools: list[str]) -> str:
if random.random() < self.epsilon:
return random.choice(tools)
weights = {t: self.db.get_weight(context_key, t) for t in tools}
return max(weights, key=weights.get)


def update(self, context_key: str, tool: str, reward: float):
w = self.db.get_weight(context_key, tool)
self.db.set_weight(context_key, tool, w + 0.1 * (reward - w))