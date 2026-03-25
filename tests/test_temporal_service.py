from app.services.memory_service import MemoryService
from app.services.temporal_service import TemporalService


def test_detect_location_change_summary(test_db_path):
    memory_service = MemoryService()
    temporal_service = TemporalService()

    conversation_id = memory_service.create_conversation("Temporal Change Test")

    msg1 = memory_service.save_message(conversation_id, "user", "I live in Berlin")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I live in Berlin",
        source_message_id=msg1
    )

    msg2 = memory_service.save_message(conversation_id, "user", "I live in Toronto")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I live in Toronto",
        source_message_id=msg2
    )

    result = temporal_service.detect_changes_for_kind("location_live")

    assert result["has_change"] is True
    assert result["previous_value"] == "berlin"
    assert result["current_value"] == "toronto"
    assert "changed from berlin to toronto" in result["summary"].lower()


def test_detect_current_state_when_no_change(test_db_path):
    memory_service = MemoryService()
    temporal_service = TemporalService()

    conversation_id = memory_service.create_conversation("No Change Test")

    msg1 = memory_service.save_message(conversation_id, "user", "My name is Alex")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="My name is Alex",
        source_message_id=msg1
    )

    result = temporal_service.detect_changes_for_kind("name")

    assert result["has_change"] is False
    assert result["current_value"] == "alex"
    assert result["previous_value"] is None
    assert "current known name is alex" in result["summary"].lower()


def test_detect_all_changes_returns_supported_kinds(test_db_path):
    temporal_service = TemporalService()

    results = temporal_service.detect_all_changes()

    assert "name" in results
    assert "location_live" in results
    assert "work_role" in results
    assert "work_company" in results
