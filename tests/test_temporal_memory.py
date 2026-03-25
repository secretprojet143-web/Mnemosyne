from app.services.memory_service import MemoryService


def test_fact_history_returns_location_versions(test_db_path):
    memory_service = MemoryService()

    conversation_id = memory_service.create_conversation("Timeline Test")

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

    history = memory_service.get_fact_history("User lives in Toronto")

    texts = [item["fact_text"] for item in history]
    assert "User lives in Berlin" in texts
    assert "User lives in Toronto" in texts
    assert len(history) >= 2


def test_fact_timeline_by_kind_returns_temporal_entries(test_db_path):
    memory_service = MemoryService()

    conversation_id = memory_service.create_conversation("Timeline Kind Test")

    msg1 = memory_service.save_message(conversation_id, "user", "My name is Alex")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="My name is Alex",
        source_message_id=msg1
    )

    msg2 = memory_service.save_message(conversation_id, "user", "My name is Alexander")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="My name is Alexander",
        source_message_id=msg2
    )

    timeline = memory_service.get_fact_timeline_by_kind("name")

    assert len(timeline) >= 2
    assert all(item["parsed_kind"] == "name" for item in timeline)


def test_temporal_fact_groups_only_include_temporal_kinds(test_db_path):
    memory_service = MemoryService()

    conversation_id = memory_service.create_conversation("Temporal Groups Test")

    msg1 = memory_service.save_message(conversation_id, "user", "I live in Berlin")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I live in Berlin",
        source_message_id=msg1
    )

    msg2 = memory_service.save_message(conversation_id, "user", "I like coffee")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I like coffee",
        source_message_id=msg2
    )

    groups = memory_service.get_temporal_fact_groups()

    assert "location_live" in groups
    assert "preference" not in groups
