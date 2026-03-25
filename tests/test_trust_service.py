from app.services.trust_service import TrustService


def test_system_source_is_trusted():
    service = TrustService()

    result = service.classify_source("system")

    assert result["trust_level"] == "trusted"
    assert result["can_issue_instructions"] is True
    assert result["can_trigger_actions"] is True


def test_user_source_is_semi_trusted():
    service = TrustService()

    result = service.classify_source("user")

    assert result["trust_level"] == "semi_trusted"
    assert result["can_issue_instructions"] is True
    assert result["can_trigger_actions"] is False


def test_document_source_is_untrusted():
    service = TrustService()

    result = service.classify_source("document")

    assert result["trust_level"] == "untrusted"
    assert result["can_issue_instructions"] is False
    assert result["can_trigger_actions"] is False


def test_unknown_source_defaults_to_untrusted():
    service = TrustService()

    result = service.classify_source("unknown_source")

    assert result["trust_level"] == "untrusted"
    assert result["can_issue_instructions"] is False
    assert result["can_trigger_actions"] is False


def test_tool_output_source_is_untrusted():
    service = TrustService()

    result = service.classify_source("tool_output")

    assert result["trust_level"] == "untrusted"
    assert result["can_issue_instructions"] is False
    assert result["can_trigger_actions"] is False


def test_memory_source_is_semi_trusted():
    service = TrustService()

    result = service.classify_source("memory")

    assert result["trust_level"] == "semi_trusted"
    assert result["can_issue_instructions"] is False
    assert result["can_trigger_actions"] is False
