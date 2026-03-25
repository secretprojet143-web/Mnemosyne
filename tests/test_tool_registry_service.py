from app.services.tool_registry_service import ToolRegistryService


def test_list_tools_returns_registered_tools():
    service = ToolRegistryService()

    tools = service.list_tools()
    names = [tool["name"] for tool in tools]

    assert "calculator" in names
    assert "file_read" in names
    assert "file_write" in names
    assert "memory_lookup" in names


def test_get_tool_returns_correct_definition():
    service = ToolRegistryService()

    tool = service.get_tool("calculator")

    assert tool is not None
    assert tool["name"] == "calculator"
    assert tool["risk_level"] == "low"
    assert tool["requires_confirmation"] is False
    assert "input_schema" in tool
    assert "output_schema" in tool


def test_get_tool_returns_none_for_missing_tool():
    service = ToolRegistryService()

    tool = service.get_tool("nonexistent_tool")
    assert tool is None


def test_tool_exists():
    service = ToolRegistryService()

    assert service.tool_exists("calculator") is True
    assert service.tool_exists("nonexistent_tool") is False


def test_list_enabled_tools_filters_disabled_tools():
    service = ToolRegistryService()

    service._tools["calculator"]["enabled"] = False

    enabled = service.list_enabled_tools()
    names = [tool["name"] for tool in enabled]

    assert "calculator" not in names
    assert "file_read" in names


def test_list_tools_sorted_alphabetically():
    service = ToolRegistryService()

    tools = service.list_tools()
    names = [tool["name"] for tool in tools]

    assert names == sorted(names)


def test_tool_definitions_have_required_fields():
    service = ToolRegistryService()

    for tool in service.list_tools():
        assert "name" in tool
        assert "description" in tool
        assert "category" in tool
        assert "risk_level" in tool
        assert "requires_confirmation" in tool
        assert "enabled" in tool
        assert "input_schema" in tool
        assert "output_schema" in tool
        assert tool["input_schema"].get("type") == "object"
        assert "properties" in tool["input_schema"]
        assert "required" in tool["input_schema"]
