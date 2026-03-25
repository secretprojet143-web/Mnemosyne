from app.services.initiative_service import InitiativeService


def test_quiet_mode_only_allows_top_priority(test_db_path):
    service = InitiativeService()

    result = service.get_suggestions_for_chat(initiative_mode="quiet")

    assert result["initiative_mode"] == "quiet"
    assert "top_priority" in result["policy"]["allowed_types"]
    assert result["policy"]["max_items"] == 1


def test_coach_mode_allows_more_items_than_quiet(test_db_path):
    service = InitiativeService()

    quiet = service.get_suggestions_for_chat(initiative_mode="quiet")
    coach = service.get_suggestions_for_chat(initiative_mode="coach")

    assert quiet["policy"]["max_items"] < coach["policy"]["max_items"]
    assert quiet["policy"]["cooldown_limit"] > coach["policy"]["cooldown_limit"]


def test_balanced_mode_is_default_policy(test_db_path):
    service = InitiativeService()

    result = service.get_suggestions_for_chat()

    assert result["initiative_mode"] == "balanced"
    assert result["policy"]["cooldown_limit"] == 3
