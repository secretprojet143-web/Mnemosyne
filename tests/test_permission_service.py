from app.services.permission_service import PermissionService
from app.services.tool_execution_service import ToolExecutionService


def test_user_can_use_low_risk_tool_without_confirmation():
    service = PermissionService()

    result = service.check_tool_permission(
        tool_name="calculator",
        source_type="user",
        confirmed=False
    )

    assert result["allowed"] is True
    assert result["risk_level"] == "low"


def test_user_cannot_use_high_risk_tool_without_confirmation():
    service = PermissionService()

    result = service.check_tool_permission(
        tool_name="file_write",
        source_type="user",
        confirmed=False
    )

    assert result["allowed"] is False
    assert result["requires_confirmation"] is True


def test_user_can_use_high_risk_tool_with_confirmation():
    service = PermissionService()

    result = service.check_tool_permission(
        tool_name="file_write",
        source_type="user",
        confirmed=True
    )

    assert result["allowed"] is True


def test_document_source_cannot_trigger_tool_action():
    service = PermissionService()

    result = service.check_tool_permission(
        tool_name="calculator",
        source_type="document",
        confirmed=False
    )

    assert result["allowed"] is False
    assert "not allowed to directly trigger tool actions" in result["reason"].lower()


def test_tool_output_source_cannot_trigger_tool_action():
    service = PermissionService()

    result = service.check_tool_permission(
        tool_name="memory_lookup",
        source_type="tool_output",
        confirmed=False
    )

    assert result["allowed"] is False


def test_unknown_tool_permission_check_fails():
    service = PermissionService()

    result = service.check_tool_permission(
        tool_name="nonexistent_tool",
        source_type="user",
        confirmed=False
    )

    assert result["allowed"] is False
    assert "not found" in result["reason"].lower()


def test_execute_tool_blocked_by_permission_from_document_source(test_db_path):
    service = ToolExecutionService()

    result = service.execute_tool(
        tool_name="calculator",
        payload={"expression": "2 + 2"},
        confirmed=False,
        initiative_mode="balanced",
        source_type="document"
    )

    assert result["execution_success"] is False
    assert result["permission"]["allowed"] is False


def test_execute_tool_allows_user_source_for_low_risk_tool(test_db_path):
    service = ToolExecutionService()

    result = service.execute_tool(
        tool_name="calculator",
        payload={"expression": "2 + 2"},
        confirmed=False,
        initiative_mode="balanced",
        source_type="user"
    )

    assert result["execution_success"] is True
    assert result["permission"]["allowed"] is True
