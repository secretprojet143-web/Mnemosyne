from app.services.tool_policy_service import ToolPolicyService
from app.services.tool_execution_service import ToolExecutionService


def test_low_risk_tool_allowed_without_confirmation():
    service = ToolPolicyService()

    result = service.authorize_tool_use("calculator", confirmed=False, initiative_mode="balanced")

    assert result["allowed"] is True
    assert result["risk_level"] == "low"


def test_high_risk_tool_blocked_without_confirmation():
    service = ToolPolicyService()

    result = service.authorize_tool_use("file_write", confirmed=False, initiative_mode="balanced")

    assert result["allowed"] is False
    assert result["requires_confirmation"] is True
    assert "requires confirmation" in result["reason"].lower()


def test_high_risk_tool_allowed_with_confirmation():
    service = ToolPolicyService()

    result = service.authorize_tool_use("file_write", confirmed=True, initiative_mode="balanced")

    assert result["allowed"] is True
    assert result["risk_level"] == "high"


def test_quiet_mode_blocks_medium_or_higher_risk_tools():
    service = ToolPolicyService()

    result = service.authorize_tool_use("file_read", confirmed=False, initiative_mode="quiet")

    assert result["allowed"] is False
    assert "blocked in quiet initiative mode" in result["reason"].lower()


def test_unknown_tool_not_authorized():
    service = ToolPolicyService()

    result = service.authorize_tool_use("does_not_exist", confirmed=False)

    assert result["allowed"] is False
    assert "not found" in result["reason"].lower()


def test_quiet_mode_allows_low_risk_tools():
    service = ToolPolicyService()

    result = service.authorize_tool_use("calculator", confirmed=False, initiative_mode="quiet")

    assert result["allowed"] is True


def test_coach_mode_allows_high_risk_with_confirmation():
    service = ToolPolicyService()

    result = service.authorize_tool_use("file_write", confirmed=True, initiative_mode="coach")

    assert result["allowed"] is True


def test_execute_high_risk_tool_blocked_without_confirmation(test_db_path):
    service = ToolExecutionService()

    result = service.execute_tool(
        "file_write",
        {"path": "/tmp/test.txt", "content": "hello"},
        confirmed=False,
        initiative_mode="balanced"
    )

    assert result["execution_success"] is False
    assert result["policy"]["allowed"] is False


def test_execute_low_risk_tool_includes_policy(test_db_path):
    service = ToolExecutionService()

    result = service.execute_tool(
        "calculator",
        {"expression": "1 + 1"},
        confirmed=False,
        initiative_mode="balanced"
    )

    assert result["execution_success"] is True
    assert result["policy"]["allowed"] is True
    assert result["policy"]["risk_level"] == "low"
