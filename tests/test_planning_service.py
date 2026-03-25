from app.services.planning_service import PlanningService


def test_create_and_get_plan(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(
        title="Improve retrieval system",
        goal="Increase relevance while preserving safety",
        status="draft"
    )

    plan = service.get_plan_by_id(plan_id)

    assert plan is not None
    assert plan["title"] == "Improve retrieval system"
    assert plan["goal"] == "Increase relevance while preserving safety"
    assert plan["status"] == "draft"


def test_create_and_list_plan_steps_in_order(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(
        title="Build planning system",
        status="draft"
    )

    service.create_plan_step(
        plan_id=plan_id,
        step_order=2,
        title="Implement endpoints",
        status="pending"
    )

    service.create_plan_step(
        plan_id=plan_id,
        step_order=1,
        title="Create planning schema",
        status="completed"
    )

    steps = service.list_plan_steps(plan_id)

    assert len(steps) == 2
    assert steps[0]["step_order"] == 1
    assert steps[0]["title"] == "Create planning schema"
    assert steps[1]["step_order"] == 2
    assert steps[1]["title"] == "Implement endpoints"


def test_update_plan_and_step_status(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(
        title="Execution control plan",
        status="draft"
    )

    step_id = service.create_plan_step(
        plan_id=plan_id,
        step_order=1,
        title="Add validation",
        status="pending"
    )

    updated_plan = service.update_plan(plan_id, status="active")
    updated_step = service.update_plan_step(step_id, status="in_progress")

    assert updated_plan is not None
    assert updated_plan["status"] == "active"

    assert updated_step is not None
    assert updated_step["status"] == "in_progress"


def test_update_plan_not_found(test_db_path):
    service = PlanningService()
    result = service.update_plan(99999, title="nonexistent")
    assert result is None


def test_update_plan_step_not_found(test_db_path):
    service = PlanningService()
    result = service.update_plan_step(99999, title="nonexistent")
    assert result is None


def test_list_plans_filtered_by_status(test_db_path):
    service = PlanningService()

    service.create_plan(title="Draft plan", status="draft")
    service.create_plan(title="Active plan", status="active")

    active = service.list_plans(status="active")
    draft = service.list_plans(status="draft")

    assert len(active) == 1
    assert active[0]["title"] == "Active plan"
    assert len(draft) == 1
    assert draft[0]["title"] == "Draft plan"


def test_plan_exists(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Existence test")

    assert service.plan_exists(plan_id) is True
    assert service.plan_exists(99999) is False


def test_plan_step_exists(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Step existence test")
    step_id = service.create_plan_step(plan_id=plan_id, step_order=1, title="First step")

    assert service.plan_step_exists(step_id) is True
    assert service.plan_step_exists(99999) is False
