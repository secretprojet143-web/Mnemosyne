from app.services.memory_service import MemoryService
from app.services.tool_execution_service import ToolExecutionService


def test_execute_calculator_success(test_db_path):
    service = ToolExecutionService()

    result = service.execute_tool("calculator", {"expression": "2 + 3 * 4"})

    assert result["execution_success"] is True
    assert result["result"]["result"] == 14
    assert result["output_validation"]["valid"] is True


def test_execute_calculator_invalid_input_fails_validation(test_db_path):
    service = ToolExecutionService()

    result = service.execute_tool("calculator", {})

    assert result["execution_success"] is False
    assert result["error"] == "Input validation failed."
    assert result["input_validation"]["valid"] is False


def test_execute_calculator_unsafe_expression_fails(test_db_path):
    service = ToolExecutionService()

    result = service.execute_tool("calculator", {"expression": "__import__('os').system('rm -rf /')"})

    assert result["execution_success"] is False
    assert result["error"] is not None


def test_execute_memory_lookup_returns_matching_facts(test_db_path):
    memory_service = MemoryService()
    service = ToolExecutionService()

    conversation_id = memory_service.create_conversation("Memory Lookup Test")
    msg_id = memory_service.save_message(conversation_id, "user", "I like chess")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I like chess",
        source_message_id=msg_id
    )

    result = service.execute_tool("memory_lookup", {"query": "chess"})

    assert result["execution_success"] is True
    assert result["output_validation"]["valid"] is True
    assert len(result["result"]["results"]) >= 1
    assert any("chess" in item["fact_text"].lower() for item in result["result"]["results"])


def test_execute_unimplemented_tool_returns_error(test_db_path):
    service = ToolExecutionService()

    result = service.execute_tool("file_read", {"path": "/tmp/test.txt"})

    assert result["execution_success"] is False
    assert result["error"] is not None
