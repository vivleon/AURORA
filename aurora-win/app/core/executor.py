from typing import Dict, Any
from app.tools import calendar, mail, browser, files, notes, screen, system, nlp


TOOL_MAP = {
"calendar": calendar,
"mail": mail,
"browser": browser,
"files": files,
"notes": notes,
"screen": screen,
"system": system,
"nlp": nlp,
}


async def run(plan: Dict[str, Any], policy, audit, db, bandit):
results = []
for step in plan.get("steps", []):
tool = step["tool"]; op = step["op"]; args = step.get("args", {})
mod = TOOL_MAP[tool]
func = getattr(mod, op)
audit.record(actor="aurora", action=f"{tool}.{op}", payload=args)
# bandit 가중치 참조 가능 (상세 구현은 bandit.py)
out = await func(args, policy=policy, db=db)
results.append({"step": f"{tool}.{op}", "out": out})
return results