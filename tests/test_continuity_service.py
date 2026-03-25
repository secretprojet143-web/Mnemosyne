from app.services.continuity_service import ContinuityService


def test_create_and_list_project(test_db_path):
    continuity_service = ContinuityService()

    project_id = continuity_service.create_project(
        title="Build Mnemosyne",
        description="Memory-first AI assistant",
        priority="critical"
    )

    project = continuity_service.get_project_by_id(project_id)
    assert project is not None
    assert project["title"] == "Build Mnemosyne"
    assert project["priority"] == "critical"

    projects = continuity_service.list_projects()
    assert len(projects) == 1


def test_auto_store_extracted_items_creates_project_goal_and_open_loop(test_db_path):
    continuity_service = ContinuityService()

    extracted = {
        "projects": [{"title": "mnemosyne", "description": "I am building Mnemosyne"}],
        "goals": [{"goal_text": "improve retrieval quality"}],
        "open_loops": [{"description": "add a memory dashboard"}]
    }

    result = continuity_service.auto_store_extracted_items(
        extracted=extracted,
        conversation_id=1
    )

    assert len(result["projects"]) == 1
    assert len(result["goals"]) == 1
    assert len(result["open_loops"]) == 1
    assert result["effective_project_id"] is not None


def test_find_project_by_title_match(test_db_path):
    continuity_service = ContinuityService()

    continuity_service.create_project(
        title="Build Mnemosyne",
        description="Main AI project",
        priority="high"
    )

    matched = continuity_service.find_project_by_title_match(
        "I want to continue working on Build Mnemosyne this week"
    )

    assert matched is not None
    assert matched["title"] == "Build Mnemosyne"
