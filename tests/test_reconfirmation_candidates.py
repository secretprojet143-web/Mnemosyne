from app.db.database import get_connection
from app.services.memory_service import MemoryService
from app.services.temporal_service import TemporalService
from app.services.retrieval_orchestrator import RetrievalOrchestrator


def test_reconfirmation_candidates_prioritize_stale_important_facts(test_db_path):
    memory_service = MemoryService()
    temporal_service = TemporalService()

    conversation_id = memory_service.create_conversation("Reconfirmation Test")
    msg_id = memory_service.save_message(conversation_id, "user", "I live in Berlin")
    stored = memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I live in Berlin",
        source_message_id=msg_id
    )

    fact_id = stored[0]["id"]

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE facts
        SET last_confirmed_at = '2020-01-01 00:00:00', is_pinned = 1
        WHERE id = ?
    """, (fact_id,))
    conn.commit()
    conn.close()

    candidates = temporal_service.get_reconfirmation_candidates(stale_after_days=30)

    assert len(candidates) >= 1
    assert candidates[0]["fact_id"] == fact_id
    assert candidates[0]["priority_score"] >= 4


def test_temporal_context_includes_reconfirmation_candidates(test_db_path):
    memory_service = MemoryService()

    conversation_id = memory_service.create_conversation("Temporal Prompt Test")
    msg_id = memory_service.save_message(conversation_id, "user", "My name is Alex")
    stored = memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="My name is Alex",
        source_message_id=msg_id
    )

    fact_id = stored[0]["id"]

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE facts
        SET last_confirmed_at = '2020-01-01 00:00:00'
        WHERE id = ?
    """, (fact_id,))
    conn.commit()
    conn.close()

    orchestrator = RetrievalOrchestrator()

    context = orchestrator.build_context_package(
        query="What do you remember about me?",
        conversation_id=conversation_id,
        retrieval_mode="balanced"
    )

    assert context["temporal"]["used"] is True
    assert "reconfirmation_candidates" in context["temporal"]
    assert len(context["temporal"]["reconfirmation_candidates"]) >= 1
