# tests/integration/test_api_flow.py
# (aurora_test_scenarios.md 시나리오 2, 3 기반)
# Usage: 
# 1. uvicorn app.main:app --port 8000
# 2. pytest

import pytest
import httpx # (requirements.txt에 추가 필요)
import os
from pathlib import Path

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

# [신규] 테스트 실행 전 .ics 파일을 정리하기 위한 픽스처(fixture)
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_files():
    """테스트 시작 전과 완료 후에 테스트용 .ics 파일을 정리합니다."""
    ics_path = Path("data/calendar/my_calendar.ics")
    
    # 시작 전: 기존 파일 삭제
    if ics_path.exists():
        ics_path.unlink()
        
    yield # 테스트 실행
    
    # 완료 후: 생성된 파일 삭제 (선택 사항)
    # if ics_path.exists():
    #     ics_path.unlink()

@pytest.mark.asyncio
async def test_api_plan_and_execute_safe_summary():
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
        exec_resp = await client.post("/aurora/execute", json={"plan": plan, "session_id": "int-test-summary"})
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        
        assert "requires_consent" not in exec_data
        assert exec_data.get("status") == "ok"
        # nlp.py가 model_runner.py를 호출하므로, 실제 LLM 응답을 확인 (스텁 응답이 아님)
        assert exec_data["result"][0]["out"].get("summary") is not None
        assert "Stub" not in exec_data["result"][0]["out"].get("summary", "")


@pytest.mark.asyncio
async def test_api_plan_and_execute_safe_calendar():
    """
    [신규] 안전한 작업(calendar.create)이 .ics 파일을 생성하는지 테스트
    """
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # 1. Plan (일정 생성)
        plan_resp = await client.post("/aurora/plan", json={"input": "테스트 일정 잡아줘"})
        assert plan_resp.status_code == 200
        plan = plan_resp.json().get("plan")
        assert plan["steps"][0]["tool"] == "calendar"
        assert plan["steps"][0]["op"] == "create"

        # 2. Execute
        exec_resp = await client.post("/aurora/execute", json={"plan": plan, "session_id": "int-test-calendar"})
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        
        assert "requires_consent" not in exec_data
        assert exec_data.get("status") == "ok"
        
        # 3. [검증] 실제 .ics 파일이 생성되었는지 확인
        ics_path_str = exec_data["result"][0]["out"].get("ics_path")
        assert ics_path_str == "data/calendar/my_calendar.ics"
        
        ics_path = Path(ics_path_str)
        assert ics_path.exists()
        
        # [검증] .ics 파일에 이벤트 내용이 포함되었는지 확인
        content = ics_path.read_text('utf-8')
        assert "BEGIN:VEVENT" in content
        assert "SUMMARY:테스트 일정 잡아줘" in content


@pytest.mark.asyncio
async def test_api_plan_and_execute_high_risk_consent():
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
        exec_resp = await client.post("/aurora/execute", json={"plan": plan, "session_id": "int-test-risk"})
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        
        assert exec_data.get("status") != "ok"
        
        # 'requires_consent' 객체가 반환되어야 함
        assert "requires_consent" in exec_data
        consent_req = exec_data["requires_consent"]
        assert consent_req["action"] == "mail.send"
        assert consent_req["risk"] == "high"
        assert "rationale" in consent_req