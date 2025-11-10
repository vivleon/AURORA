# tests/integration/test_api_flow.py
# (aurora_test_scenarios.md 시나리오 2, 3 기반)
# Usage: 
# 1. uvicorn app.main:app --port 8000
# 2. pytest

import pytest
import httpx # (requirements.txt에 추가 필요: pip install httpx)
import os

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

@pytest.mark.asyncio
async def test_api_plan_and_execute_safe():
    """
    안전한 작업(nlp.summarize)에 대한 /plan -> /execute 플로우 테스트
    (동의(consent)가 필요 없어야 함)
    """
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # 1. Plan
        plan_resp = await client.post("/aurora/plan", json={"input": "간단한 요약"})
        assert plan_resp.status_code == 200
        plan = plan_resp.json().get("plan")
        assert plan["steps"][0]["tool"] == "nlp"
        assert plan["steps"][0]["op"] == "summarize"

        # 2. Execute
        exec_resp = await client.post("/aurora/execute", json={"plan": plan, "session_id": "int-test-1"})
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        
        # 'requires_consent'가 없어야 함
        assert "requires_consent" not in exec_data
        assert exec_data.get("status") == "ok"
        assert "Summary of" in exec_data["result"][0]["out"]

@pytest.mark.asyncio
async def test_api_plan_and_execute_high_risk():
    """
    고위험 작업(mail.send)에 대한 /plan -> /execute 플로우 테스트
    (동의(consent)가 필요해야 함)
    """
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # 1. Plan (고위험 작업)
        plan_resp = await client.post("/aurora/plan", json={"input": "중요 메일 보내줘"})
        assert plan_resp.status_code == 200
        plan = plan_resp.json().get("plan")
        assert plan["steps"][0]["tool"] == "mail"
        assert plan["steps"][0]["op"] == "send" # planner.py가 'send'로 라우팅

        # 2. Execute (동의 요청 반환)
        exec_resp = await client.post("/aurora/execute", json={"plan": plan, "session_id": "int-test-2"})
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        
        # 'status' == 'ok'가 아니어야 함
        assert exec_data.get("status") != "ok"
        
        # 'requires_consent' 객체가 반환되어야 함
        assert "requires_consent" in exec_data
        consent_req = exec_data["requires_consent"]
        assert consent_req["action"] == "mail.send"
        assert consent_req["risk"] == "high"
        assert "rationale" in consent_req