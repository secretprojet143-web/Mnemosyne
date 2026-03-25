from app.services.tool_control_service import ToolControlService
from app.services.tool_execution_service import ToolExecutionService


def test_precheck_allows_tool_with_no_recent_failures(test_db_path):
    service = ToolControlService()

    result = service.precheck_tool_invocation(
        tool_name="calculator",
        payload={"expression": "2+2"}
    )

    assert result["allowed"] is True
    assert result["recommended_action"] == "proceed"


def test_precheck_blocks_same_payload_after_repeated_failures(test_db_path):
    service = ToolControlService()

    payload = {"expression": "__import__('os').system('bad')"}
    service.record_tool_invocation("calculator", payload, success=False, error_message="Unsafe expression")
    service.record_tool_invocation("calculator", payload, success=False, error_message="Unsafe expression")

    result = service.precheck_tool_invocation(
        tool_name="calculator",
        payload=payload
    )

    assert result["allowed"] is False
    assert result["recommended_action"] == "inspect_or_change_input"


def test_precheck_blocks_tool_after_many_recent_failures(test_db_path):
    service = ToolControlService()

    for i in range(4):
        service.record_tool_invocation(
            "calculator",
            {"expression": f"bad_{i}"},
            success=False,
            error_message="Unsafe"
        )

    result = service.precheck_tool_invocation(
        tool_name="calculator",
        payload={"expression": "1+1"}
    )

    assert result["allowed"] is False
    assert result["recommended_action"] == "pause_or_inspect_tool"


def test_tool_execution_records_invocations(test_db_path):
    service = ToolExecutionService()
    control = ToolControlService()

    service.execute_tool("calculator", {"expression": "2 + 2"})
    invocations = control.list_recent_tool_invocations(tool_name="calculator", limit=10)

    assert len(invocations) >= 1
    assert invocations[0]["tool_name"] == "calculator"


def test_tool_execution_precheck_blocks_repeated_bad_calls(test_db_path):
    service = ToolExecutionService()

    bad_payload = {"expression": "__import__('os').system('bad')"}
    service.execute_tool("calculator", bad_payload)
    service.execute_tool("calculator", bad_payload)

    third = service.execute_tool("calculator", bad_payload)

    assert third["execution_success"] is False
    assert third["precheck"]["allowed"] is False


def test_make_payload_signature_is_deterministic(test_db_path):
    service = ToolControlService()

    sig1 = service.make_payload_signature({"a": 1, "b": 2})
    sig2 = service.make_payload_signature({"b": 2, "a": 1})

    assert sig1 == sig2
