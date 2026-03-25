from app.db.database import get_connection
from app.services.memory_service import MemoryService
from app.services.recommendation_service import RecommendationService
from app.services.continuity_service import ContinuityService


def test_create_and_list_recommendations(test_db_path):
    service = RecommendationService()

    rec_id = service.create_recommendation(
        source_type="reflection",
        source_ref_id=1,
        recommendation_text="User values continuity in AI systems.",
        category="user_insight",
        confidence=0.88
    )

    assert rec_id is not None

    rec = service.get_recommendation_by_id(rec_id)
    assert rec is not None
    assert rec["category"] == "user_insight"

    all_recs = service.list_recommendations()
    assert len(all_recs) == 1


def test_duplicate_recommendation_from_same_source_is_not_duplicated(test_db_path):
    service = RecommendationService()

    rec1 = service.create_recommendation(
        source_type="reflection",
        source_ref_id=10,
        recommendation_text="User prioritizes trust and continuity.",
        category="memory_candidate",
        confidence=0.85
    )

    rec2 = service.create_recommendation(
        source_type="reflection",
        source_ref_id=10,
        recommendation_text="User prioritizes trust and continuity.",
        category="memory_candidate",
        confidence=0.85
    )

    assert rec1 is not None
    assert rec2 is None

    all_recs = service.list_recommendations()
    assert len(all_recs) == 1


def test_aggregate_recommendations_scores_recurrence(test_db_path):
    service = RecommendationService()

    service.create_recommendation(
        source_type="reflection",
        source_ref_id=1,
        recommendation_text="User values continuity in AI systems.",
        category="user_insight",
        confidence=0.80
    )

    service.create_recommendation(
        source_type="reflection",
        source_ref_id=2,
        recommendation_text="User values continuity in AI systems.",
        category="user_insight",
        confidence=0.90
    )

    service.create_recommendation(
        source_type="weekly_learning",
        source_ref_id=1,
        recommendation_text="User values continuity in AI systems.",
        category="user_insight",
        confidence=0.88
    )

    candidates = service.get_top_candidates(limit=10)
    assert candidates["candidate_count"] >= 1

    top = candidates["candidates"][0]
    assert top["recommendation_text"] == "User values continuity in AI systems."
    assert top["occurrence_count"] == 3
    assert top["distinct_source_types"] == 2
    assert top["score"] > 0.9


def test_accept_recommendation_updates_status_and_note(test_db_path):
    service = RecommendationService()

    rec_id = service.create_recommendation(
        source_type="reflection",
        source_ref_id=1,
        recommendation_text="User values continuity in AI systems.",
        category="user_insight",
        confidence=0.88
    )

    updated = service.accept_recommendation(
        recommendation_id=rec_id,
        decision_note="Repeated across reflections."
    )

    assert updated is not None
    assert updated["status"] == "accepted"
    assert updated["decision_note"] == "Repeated across reflections."


def test_reject_recommendation_updates_status(test_db_path):
    service = RecommendationService()

    rec_id = service.create_recommendation(
        source_type="reflection",
        source_ref_id=2,
        recommendation_text="User likes this.",
        category="preference",
        confidence=0.50
    )

    updated = service.reject_recommendation(
        recommendation_id=rec_id,
        decision_note="Too vague to store durably."
    )

    assert updated is not None
    assert updated["status"] == "rejected"
    assert updated["decision_note"] == "Too vague to store durably."


import pytest


def test_invalid_status_transition_raises_error(test_db_path):
    service = RecommendationService()

    rec_id = service.create_recommendation(
        source_type="reflection",
        source_ref_id=3,
        recommendation_text="User prioritizes trust in AI.",
        category="user_insight",
        confidence=0.9
    )

    service.reject_recommendation(rec_id, "Rejected for testing")

    with pytest.raises(ValueError):
        service.accept_recommendation(rec_id, "Should not reopen rejected item")


def test_promote_accepted_recommendation_creates_fact(test_db_path):
    rec_service = RecommendationService()

    rec_id = rec_service.create_recommendation(
        source_type="reflection",
        source_ref_id=1,
        recommendation_text="User highly values continuity in AI systems.",
        category="user_insight",
        confidence=0.9
    )

    rec_service.accept_recommendation(rec_id, "Strong recurring theme.")

    result = rec_service.promote_recommendation_to_fact(rec_id, pin=True)

    assert result is not None
    assert result["action"] == "created_fact"
    assert result["recommendation"]["status"] == "promoted"
    assert result["fact"]["fact_text"] == "User highly values continuity in AI systems."
    assert result["fact"]["is_pinned"] == 1


def test_promote_requires_accepted_status(test_db_path):
    rec_service = RecommendationService()

    rec_id = rec_service.create_recommendation(
        source_type="reflection",
        source_ref_id=2,
        recommendation_text="User prefers memory-first systems.",
        category="preference",
        confidence=0.85
    )

    with pytest.raises(ValueError):
        rec_service.promote_recommendation_to_fact(rec_id)


def test_promote_matches_existing_active_fact_without_duplication(test_db_path):
    rec_service = RecommendationService()
    memory_service = MemoryService()

    conversation_id = memory_service.create_conversation("Promotion Test")
    msg_id = memory_service.save_message(conversation_id, "user", "I like structured memory systems")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I like structured memory systems",
        source_message_id=msg_id
    )

    rec_id = rec_service.create_recommendation(
        source_type="reflection",
        source_ref_id=3,
        recommendation_text="User likes structured memory systems",
        category="preference",
        confidence=0.88
    )

    rec_service.accept_recommendation(rec_id, "Already supported by direct evidence.")

    result = rec_service.promote_recommendation_to_fact(rec_id)

    assert result is not None
    assert result["action"] == "matched_existing_fact"
    assert result["recommendation"]["status"] == "promoted"


def test_promote_accepted_recommendation_to_goal(test_db_path):
    rec_service = RecommendationService()

    rec_id = rec_service.create_recommendation(
        source_type="reflection",
        source_ref_id=10,
        recommendation_text="Improve retrieval quality",
        category="goal",
        confidence=0.9
    )

    rec_service.accept_recommendation(rec_id, "Recurring strategic goal.")

    result = rec_service.promote_recommendation_to_goal(rec_id, priority="high")

    assert result is not None
    assert result["action"] == "created_goal"
    assert result["recommendation"]["status"] == "promoted"
    assert result["goal"]["goal_text"] == "Improve retrieval quality"
    assert result["goal"]["priority"] == "high"


def test_promote_accepted_recommendation_to_open_loop(test_db_path):
    rec_service = RecommendationService()

    rec_id = rec_service.create_recommendation(
        source_type="reflection",
        source_ref_id=11,
        recommendation_text="Need to improve fuzzy matching for project inference",
        category="conflict_note",
        confidence=0.88
    )

    rec_service.accept_recommendation(rec_id, "Recurring unresolved issue.")

    result = rec_service.promote_recommendation_to_open_loop(rec_id, priority="critical")

    assert result is not None
    assert result["action"] == "created_open_loop"
    assert result["recommendation"]["status"] == "promoted"
    assert result["open_loop"]["description"] == "Need to improve fuzzy matching for project inference"
    assert result["open_loop"]["priority"] == "critical"


def test_promote_to_goal_matches_existing_goal_without_duplication(test_db_path):
    rec_service = RecommendationService()
    continuity_service = ContinuityService()

    existing_goal_id = continuity_service.create_goal(
        goal_text="Improve retrieval quality",
        status="active",
        priority="high"
    )

    rec_id = rec_service.create_recommendation(
        source_type="reflection",
        source_ref_id=12,
        recommendation_text="Improve retrieval quality",
        category="goal",
        confidence=0.9
    )

    rec_service.accept_recommendation(rec_id)

    result = rec_service.promote_recommendation_to_goal(rec_id)

    assert result is not None
    assert result["action"] == "matched_existing_goal"
    assert result["goal"]["id"] == existing_goal_id
    assert result["recommendation"]["status"] == "promoted"


def test_review_queue_returns_proposed_candidates(test_db_path):
    service = RecommendationService()

    service.create_recommendation(
        source_type="reflection",
        source_ref_id=1,
        recommendation_text="User values continuity in AI systems.",
        category="user_insight",
        confidence=0.9
    )

    service.create_recommendation(
        source_type="reflection",
        source_ref_id=2,
        recommendation_text="User values continuity in AI systems.",
        category="user_insight",
        confidence=0.88
    )

    queue = service.get_review_queue(limit=10)

    assert queue["queue_size"] >= 1
    assert len(queue["items"]) >= 1
    assert queue["items"][0]["recommendation_text"] == "User values continuity in AI systems."


def test_top_pending_recommendations_filters_by_score(test_db_path):
    service = RecommendationService()

    service.create_recommendation(
        source_type="reflection",
        source_ref_id=3,
        recommendation_text="User strongly prefers memory-first systems.",
        category="preference",
        confidence=0.95
    )

    service.create_recommendation(
        source_type="weekly_learning",
        source_ref_id=1,
        recommendation_text="User strongly prefers memory-first systems.",
        category="preference",
        confidence=0.92
    )

    top = service.get_top_pending_recommendations(limit=5, min_score=0.9)

    assert top["count"] >= 1
    assert top["items"][0]["recommendation_text"] == "User strongly prefers memory-first systems."
    assert top["items"][0]["score"] >= 0.9
