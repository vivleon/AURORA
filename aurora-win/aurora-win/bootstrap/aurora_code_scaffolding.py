# Aurora Code Scaffolding (Windows MVP)

# Directory Structure
# aurora-win/
#  ├─ app/
#  │   ├─ main.py              # FastAPI entrypoint
#  │   ├─ cognition/           # Intent, Planner, Verifier, Executor
#  │   ├─ tools/               # Tool plugins (calendar, mail, browser, etc.)
#  │   ├─ memory/              # FAISS + session memory
#  │   ├─ policy/              # Consent engine + policy.json loader
#  │   └─ utils/               # Logging, config, security helpers
#  ├─ webui/                   # React/Vanilla web interface
#  ├─ data/                    # embeddings/, notes/, audit.log, policy.json
#  ├─ ocr/                     # Tesseract binaries
#  ├─ scripts/                 # PowerShell signed scripts
#  ├─ start.bat                # Windows launcher
#  └─ requirements.txt         # dependencies

# --- app/main.py ---
from fastapi import FastAPI
from app.cognition.router import cognition_router
from app.policy.router import policy_router
from app.tools.router import tools_router

app = FastAPI(title="Aurora Personal AI Assistant")

app.include_router(cognition_router, prefix="/cognition")
app.include_router(policy_router, prefix="/policy")
app.include_router(tools_router, prefix="/tools")

@app.get("/")
def root():
    return {"message": "Aurora is running locally."}

# --- app/cognition/planner.py ---
def generate_plan(user_input: str):
    # simple intent-to-tool mapping placeholder
    plan = {"intent": "summarize", "tool": "nlp.summarize", "args": {"text": user_input}}
    return plan

# --- app/memory/vector_store.py ---
import faiss, numpy as np

def init_index(dim: int = 768):
    index = faiss.IndexFlatL2(dim)
    return index

# --- app/policy/policy_engine.py ---
import json

with open("data/policy.json", "r") as f:
    POLICY = json.load(f)

def check_scope(scope: str) -> bool:
    return scope in POLICY["scopes"] and POLICY["scopes"][scope]["allow"]

# --- start.bat ---
# @echo off
# cd app
# python main.py
# pause
