from app.services.tool_registry_service import ToolRegistryService


def test_validate_tool_input_accepts_valid_calculator_payload():
    service = ToolRegistryService()

    result = service.validate_tool_input(
        "calculator",
        {"expression": "2 + 2 * 5"}
    )

    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_tool_input_rejects_missing_required_field():
    service = ToolRegistryService()

    result = service.validate_tool_input(
        "calculator",
        {}
    )

    assert result["valid"] is False
    assert "Missing required field: expression" in result["errors"]


def test_validate_tool_input_rejects_wrong_type():
    service = ToolRegistryService()

    result = service.validate_tool_input(
        "file_write",
        {"path": "/tmp/a.txt", "content": 123}
    )

    assert result["valid"] is False
    assert any("Field 'content' has invalid type" in err for err in result["errors"])


def test_validate_tool_input_warns_on_unexpected_field():
    service = ToolRegistryService()

    result = service.validate_tool_input(
        "memory_lookup",
        {"query": "user preferences", "extra": "unexpected"}
    )

    assert result["valid"] is True
    assert "Unexpected field provided: extra" in result["warnings"]


def test_validate_tool_input_unknown_tool():
    service = ToolRegistryService()

    result = service.validate_tool_input(
        "does_not_exist",
        {"x": 1}
    )

    assert result["valid"] is False
    assert "not found" in result["errors"][0].lower()


def test_validate_tool_input_rejects_non_object_payload():
    service = ToolRegistryService()

    result = service.validate_tool_input(
        "calculator",
        ["not", "an", "object"]
    )

    assert result["valid"] is False
    assert "Payload must be an object." in result["errors"]


def test_validate_file_read_accepts_valid_payload():
    service = ToolRegistryService()

    result = service.validate_tool_input(
        "file_read",
        {"path": "/some/file.txt"}
    )

    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_file_write_requires_both_fields():
    service = ToolRegistryService()

    result = service.validate_tool_input(
        "file_write",
        {"path": "/tmp/test.txt"}
    )

    assert result["valid"] is False
    assert "Missing required field: content" in result["errors"]


def test_validate_memory_lookup_accepts_string_query():
    service = ToolRegistryService()

    result = service.validate_tool_input(
        "memory_lookup",
        {"query": "user's name"}
    )

    assert result["valid"] is True
