from app.services.security_scan_service import SecurityScanService
from app.services.tool_execution_service import ToolExecutionService


def test_scan_text_detects_env_secret():
    service = SecurityScanService()

    result = service.scan_text("API_KEY=supersecretvalue123")

    assert result["has_sensitive_data"] is True
    assert result["finding_count"] >= 1
    assert any(f["category"] == "env_secret" for f in result["findings"])


def test_scan_text_detects_bearer_token():
    service = SecurityScanService()

    result = service.scan_text("Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456")

    assert result["has_sensitive_data"] is True
    assert any(f["category"] == "bearer_token" for f in result["findings"])


def test_scan_text_safe_text_not_flagged():
    service = SecurityScanService()

    result = service.scan_text("This is a normal document about retrieval systems.")

    assert result["has_sensitive_data"] is False
    assert result["finding_count"] == 0


def test_redact_text_replaces_sensitive_values():
    service = SecurityScanService()

    result = service.redact_text("API_KEY=supersecretvalue123")

    assert result["original_has_sensitive_data"] is True
    assert "[REDACTED]" in result["redacted_text"]
    assert "supersecretvalue123" not in result["redacted_text"]


def test_scan_structured_output_detects_nested_sensitive_data():
    service = SecurityScanService()

    data = {
        "message": "safe",
        "meta": {
            "token": "Bearer abcdefghijklmnopqrstuvwxyz123456"
        }
    }

    result = service.scan_structured_output(data)

    assert result["has_sensitive_data"] is True
    assert result["finding_count"] >= 1
    assert any("meta.token" in f["path"] for f in result["findings"])


def test_scan_structured_output_with_list():
    service = SecurityScanService()

    data = ["safe", "PASSWORD=secret123", {"key": "value"}]

    result = service.scan_structured_output(data)

    assert result["has_sensitive_data"] is True
    assert any("[1]" in f["path"] for f in result["findings"])


def test_scan_text_empty_string():
    service = SecurityScanService()

    result = service.scan_text("")

    assert result["has_sensitive_data"] is False
    assert result["finding_count"] == 0


def test_tool_execution_redacts_sensitive_structured_output(test_db_path):
    service = ToolExecutionService()

    service._dispatch_tool = lambda tool_name, payload: {
        "result": "API_KEY=supersecretvalue123"
    }
    service.tool_registry._tools["calculator"]["output_schema"] = {
        "type": "object",
        "properties": {"result": {"type": "string"}},
        "required": ["result"]
    }

    result = service.execute_tool("calculator", {"expression": "2+2"})

    assert result["security_scan"]["has_sensitive_data"] is True
    assert "[REDACTED]" in result["result"]["result"]
