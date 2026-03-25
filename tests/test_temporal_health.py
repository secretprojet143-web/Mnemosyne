from app.db.database import get_connection
from app.services.continuity_service import ContinuityService
from app.services.memory_service import MemoryService
from app.services.temporal_service import TemporalService


def test_detect_stale_facts(test_db_path):
    memory_service = MemoryService()
    temporal_service = TemporalService()

    conversation_id = memory_service.create_conversation("Stale Fact Test")
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
        SET last_confirmed_at = '2020-01-01 00:00:00'
        WHERE id = ?
    """, (fact_id,))
    conn.commit()
    conn.close()

    stale = temporal_service.detect_stale_facts(stale_after_days=30)

    assert any(item["fact_id"] == fact_id for item in stale)


def test_detect_aging_open_loops(test_db_path):
    continuity_service = ContinuityService()
    temporal_service = TemporalService()

    loop_id = continuity_service.create_open_loop(
        description="Need to improve retrieval scoring",
        status="open",
        priority="high"
    )

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE open_loops
        SET updated_at = '2020-01-01 00:00:00'
        WHERE id = ?
    """, (loop_id,))
    conn.commit()
    conn.close()

    aging = temporal_service.detect_aging_open_loops(stale_after_days=14)

    assert any(item["open_loop_id"] == loop_id for item in aging)


def test_detect_recurring_open_loop_patterns(test_db_path):
    continuity_service = ContinuityService()
    temporal_service = TemporalService()

    continuity_service.create_open_loop(
        description="Need to improve fuzzy matching",
        status="open",
        priority="medium"
    )
    continuity_service.create_open_loop(
        description="Need to improve fuzzy matching",
        status="resolved",
        priority="medium"
    )

    recurring = temporal_service.detect_recurring_open_loop_patterns()

    assert len(recurring) >= 1
    assert recurring[0]["occurrence_count"] >= 2
