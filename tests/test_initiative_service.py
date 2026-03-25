from app.services.initiative_service import InitiativeService
from app.services.recommendation_service import RecommendationService


def test_initiative_service_returns_structured_suggestions(test_db_path):
    service = InitiativeService()

    result = service.get_suggestions_for_chat(max_items=2)

    assert "surfaced_count" in result
    assert "surfaced" in result
    assert "skipped" in result


def test_suggestion_cooldown_prevents_immediate_repeat(test_db_path):
    service = InitiativeService()

    service.record_surface_event(
        suggestion_type="memory_review",
        suggestion_text="Strong memory recommendation awaiting review: User values continuity"
    )

    should_surface = service.should_surface(
        suggestion_type="memory_review",
        suggestion_text="Strong memory recommendation awaiting review: User values continuity"
    )

    assert should_surface is False


def test_recent_surface_events_are_recorded(test_db_path):
    service = InitiativeService()

    service.record_surface_event(
        suggestion_type="top_priority",
        suggestion_text="Top active priority: Improve retrieval quality",
        conversation_id=1
    )

    events = service.list_recent_surface_events(limit=10)

    assert len(events) >= 1
    assert events[0]["suggestion_type"] == "top_priority"
