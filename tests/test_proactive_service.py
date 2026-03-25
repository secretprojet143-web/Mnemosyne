from app.db.database import get_connection
from app.services.continuity_service import ContinuityService
from app.services.proactive_service import ProactiveService
from app.services.recommendation_service import RecommendationService


def test_generate_proactive_briefing_returns_expected_sections(test_db_path):
    service = ProactiveService()

    briefing = service.generate_proactive_briefing()

    assert "summary_counts" in briefing
    assert "top_priorities" in briefing
    assert "reconfirmation_needs" in briefing
    assert "stalled_items" in briefing
    assert "memory_review_queue" in briefing
    assert "briefing_lines" in briefing


def test_proactive_briefing_surfaces_pending_memory_recommendations(test_db_path):
    rec_service = RecommendationService()
    service = ProactiveService()

    rec_service.create_recommendation(
        source_type="reflection",
        source_ref_id=1,
        recommendation_text="User strongly values continuity in AI systems.",
        category="user_insight",
        confidence=0.95
    )
    rec_service.create_recommendation(
        source_type="weekly_learning",
        source_ref_id=1,
        recommendation_text="User strongly values continuity in AI systems.",
        category="user_insight",
        confidence=0.92
    )

    briefing = service.generate_proactive_briefing()

    assert briefing["summary_counts"]["pending_memory_recommendations"] >= 1
    assert len(briefing["memory_review_queue"]) >= 1


def test_proactive_briefing_surfaces_aging_items(test_db_path):
    continuity_service = ContinuityService()
    service = ProactiveService()

    goal_id = continuity_service.create_goal(
        goal_text="Improve retrieval quality",
        status="active",
        priority="high"
    )

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE goals
        SET updated_at = '2020-01-01 00:00:00'
        WHERE id = ?
    """, (goal_id,))
    conn.commit()
    conn.close()

    briefing = service.generate_proactive_briefing()

    assert briefing["summary_counts"]["aging_goals"] >= 1
    assert len(briefing["stalled_items"]) >= 1
