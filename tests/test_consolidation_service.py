from app.db.database import get_connection
from app.services.consolidation_service import ConsolidationService
from app.services.memory_service import MemoryService


def test_consolidation_supersedes_duplicate_facts_instead_of_deleting(test_db_path):
    memory_service = MemoryService()
    consolidation_service = ConsolidationService()

    conversation_id = memory_service.create_conversation("Consolidation Test")

    msg1 = memory_service.save_message(conversation_id, "user", "I live in Toronto")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I live in Toronto",
        source_message_id=msg1
    )

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO facts (
            conversation_id,
            source_message_id,
            fact_text,
            category,
            confidence,
            status,
            visibility,
            is_pinned,
            provenance
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        conversation_id,
        msg1,
        "User lives in Toronto",
        "location",
        0.60,
        "active",
        "personal",
        0,
        "explicit"
    ))
    conn.commit()
    conn.close()

    consolidated_count = consolidation_service.consolidate_facts()
    assert consolidated_count >= 1

    all_facts = memory_service.get_all_facts()
    active = [f for f in all_facts if f["fact_text"] == "User lives in Toronto" and f["status"] == "active"]
    superseded = [f for f in all_facts if f["fact_text"] == "User lives in Toronto" and f["status"] == "superseded"]

    assert len(active) == 1
    assert len(superseded) >= 1


def test_consolidation_keeps_higher_confidence_fact_active(test_db_path):
    memory_service = MemoryService()
    consolidation_service = ConsolidationService()

    conversation_id = memory_service.create_conversation("Confidence Test")

    msg1 = memory_service.save_message(conversation_id, "user", "I like Python")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I like Python",
        source_message_id=msg1
    )

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO facts (
            conversation_id, source_message_id, fact_text, category,
            confidence, status, visibility, is_pinned, provenance
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (conversation_id, msg1, "User likes Python", "preference", 0.99, "active", "personal", 0, "explicit"))
    conn.commit()
    conn.close()

    consolidation_service.consolidate_facts()

    all_facts = memory_service.get_all_facts()
    active = [f for f in all_facts if f["fact_text"] == "User likes Python" and f["status"] == "active"]

    assert len(active) == 1
    assert active[0]["confidence"] >= 0.99
