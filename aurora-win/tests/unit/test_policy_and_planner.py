# tests/unit/test_policy_and_planner.py
# (aurora_test_scenarios.md 시나리오 11, 12 기반)
# Usage: pytest

import sys
import os
from pathlib import Path
import pytest

# 프로젝트 루트를 sys.path에 추가 (app 임포트를 위해)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.security.policy import Policy
from app.core import planner

# 테스트용 정책 데이터
TEST_POLICY_DATA = {
    "policy_version": "1.1",
    "scopes": {
        "files.read": {"allow": True},
        "system.exec": {"allow": False}
    },
    "risk_rules": {
        "high_risk": ["system.exec"],
        "require_consent_each_time": True
    }
}

@pytest.fixture
def test_policy():
    """
    app/security/policy.py의 Policy 객체를 테스트합니다.
    """
    return Policy(TEST_POLICY_DATA)

def test_policy_allowed(test_policy):
    assert test_policy.allowed("files.read") == True

def test_policy_denied(test_policy):
    assert test_policy.allowed("system.exec") == False

def test_policy_not_found(test_policy):
    assert test_policy.allowed("mail.send") == False

def test_policy_consent_flag(test_policy):
    assert test_policy.require_each_time == True

def test_planner_routes_to_calendar():
    """
    app/core/planner.py가 '일정' 키워드를 'calendar.create'로 라우팅하는지 테스트
    """
    plan = planner.make_plan("내일 10시 팀 미팅 일정", {})
    assert plan["steps"][0]["tool"] == "calendar"
    assert plan["steps"][0]["op"] == "create"