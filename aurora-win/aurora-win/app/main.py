from fastapi import FastAPI, HTTPException
from app.core import planner, verifier, executor, consent
from app.security.policy import Policy
from app.security.hashlog import AuditLogger
from app.memory.store import DB
from app.memory.bandit import Bandit


app = FastAPI(title="AURORA", version="0.2")
policy = Policy.from_file("data/policy.json")
audit = AuditLogger("data/audit.log")
db = DB("data/aurora.db")
bandit = Bandit(db)


@app.post("/aurora/plan")
async def plan(req: dict):
intent = req.get("input", "")
ctx = req.get("context", {})
plan_obj = planner.make_plan(intent, ctx)
return {"plan": plan_obj}


@app.post("/aurora/execute")
async def execute(req: dict):
plan_obj = req.get("plan")
if not plan_obj:
raise HTTPException(400, "plan missing")
risk = verifier.assess_risk(plan_obj, policy)
if verifier.need_consent(risk, plan_obj, policy):
token = consent.issue(plan_obj, policy)
return {"status": "consent_required", "token": token}
result = await executor.run(plan_obj, policy, audit, db, bandit)
return {"status": "ok", "result": result}


@app.post("/aurora/consent/approve")
async def approve(req: dict):
token = req.get("token")
consent.save(token, approved=True, db=db)
plan_obj = consent.resolve_plan(token)
result = await executor.run(plan_obj, policy, audit, db, bandit)
return {"status": "ok", "result": result}