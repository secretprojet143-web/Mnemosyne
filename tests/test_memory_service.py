from app.services.memory_service import MemoryService


def test_fact_extraction_and_storage(test_db_path):
    memory_service = MemoryService()

    conversation_id = memory_service.create_conversation("Test Conversation")
    message_id = memory_service.save_message(
        conversation_id=conversation_id,
        role="user",
        content="My name is Alex and I live in Berlin"
    )

    stored = memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="My name is Alex and I live in Berlin",
        source_message_id=message_id
    )

    assert len(stored) >= 2

    facts = memory_service.get_all_facts()
    fact_texts = [f["fact_text"] for f in facts]

    # The fact extractor may combine or split facts differently
    # The important thing is that facts were extracted
    assert len(facts) >= 2
    # Check that at least some relevant content was extracted
    all_fact_text = " ".join(fact_texts)
    assert "Alex" in all_fact_text
    assert "Berlin" in all_fact_text


def test_duplicate_fact_reconfirms_instead_of_creating_new_row(test_db_path):
    memory_service = MemoryService()

    conversation_id = memory_service.create_conversation("Duplicate Test")
    message_id_1 = memory_service.save_message(conversation_id, "user", "I live in Toronto")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I live in Toronto",
        source_message_id=message_id_1
    )

    message_id_2 = memory_service.save_message(conversation_id, "user", "I live in Toronto")
    stored_again = memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I live in Toronto",
        source_message_id=message_id_2
    )

    active_facts = memory_service.get_active_facts()
    toronto_facts = [f for f in active_facts if f["fact_text"] == "User lives in Toronto"]

    assert len(toronto_facts) == 1
    assert stored_again[0]["action"] == "reconfirmed"


def test_conflicting_location_supersedes_old_fact(test_db_path):
    memory_service = MemoryService()

    conversation_id = memory_service.create_conversation("Contradiction Test")

    msg1 = memory_service.save_message(conversation_id, "user", "I live in Berlin")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I live in Berlin",
        source_message_id=msg1
    )

    msg2 = memory_service.save_message(conversation_id, "user", "I live in Toronto")
    stored = memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I live in Toronto",
        source_message_id=msg2
    )

    all_facts = memory_service.get_all_facts()
    active_facts = [f for f in all_facts if f["status"] == "active"]
    superseded_facts = [f for f in all_facts if f["status"] == "superseded"]

    assert any(f["fact_text"] == "User lives in Toronto" for f in active_facts)
    assert any(f["fact_text"] == "User lives in Berlin" for f in superseded_facts)
    assert stored[0]["action"] == "superseded_conflict"
