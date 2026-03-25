from app.services.planning_service import PlanningService


def test_plan_progress_summary_counts_steps_correctly(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Progress Plan")
    service.create_plan_step(plan_id, 1, "Step 1", status="completed")
    service.create_plan_step(plan_id, 2, "Step 2", status="in_progress")
    service.create_plan_step(plan_id, 3, "Step 3", status="pending")

    summary = service.get_plan_progress_summary(plan_id)

    assert summary is not None
    assert summary["counts"]["total_steps"] == 3
    assert summary["counts"]["completed"] == 1
    assert summary["counts"]["in_progress"] == 1
    assert summary["counts"]["pending"] == 1
    assert summary["percent_complete"] == round((1 / 3) * 100, 2)


def test_plan_progress_summary_empty_plan(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Empty Plan")

    summary = service.get_plan_progress_summary(plan_id)

    assert summary is not None
    assert summary["counts"]["total_steps"] == 0
    assert summary["percent_complete"] == 0.0


def test_plan_health_detects_blocked_plan(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Blocked Plan")
    step1 = service.create_plan_step(plan_id, 1, "Step 1", status="pending")
    step2 = service.create_plan_step(plan_id, 2, "Step 2", status="pending")

    service.add_step_dependency(plan_id, step2, step1)

    service.update_plan_step(step1, status="blocked")

    health = service.get_plan_health_summary(plan_id)

    assert health is not None
    assert health["health_status"] in {"blocked", "active_with_blockers"}


def test_plan_health_detects_completed_plan(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Completed Plan")
    service.create_plan_step(plan_id, 1, "Step 1", status="completed")
    service.create_plan_step(plan_id, 2, "Step 2", status="completed")

    health = service.get_plan_health_summary(plan_id)

    assert health is not None
    assert health["health_status"] == "completed"
    assert health["percent_complete"] == 100.0


def test_plan_health_returns_next_recommended_ready_step(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Ready Step Plan")
    service.create_plan_step(plan_id, 1, "First Ready Step", status="pending")
    service.create_plan_step(plan_id, 2, "Later Step", status="pending")

    health = service.get_plan_health_summary(plan_id)

    assert health is not None
    assert health["next_recommended_step"] is not None
    assert health["next_recommended_step"]["title"] == "First Ready Step"


def test_plan_health_empty_plan(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="No Steps Plan")

    health = service.get_plan_health_summary(plan_id)

    assert health is not None
    assert health["health_status"] == "empty"


def test_plan_health_at_risk_with_failed_step(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Failed Plan")
    service.create_plan_step(plan_id, 1, "Step 1", status="completed")
    service.create_plan_step(plan_id, 2, "Step 2", status="failed")

    health = service.get_plan_health_summary(plan_id)

    assert health is not None
    assert health["health_status"] == "at_risk"


def test_plan_health_healthy_with_no_blockers(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Healthy Plan")
    service.create_plan_step(plan_id, 1, "Step 1", status="completed")
    service.create_plan_step(plan_id, 2, "Step 2", status="in_progress")
    service.create_plan_step(plan_id, 3, "Step 3", status="pending")

    health = service.get_plan_health_summary(plan_id)

    assert health is not None
    assert health["health_status"] == "healthy"


def test_plan_progress_summary_returns_none_for_missing_plan(test_db_path):
    service = PlanningService()
    result = service.get_plan_progress_summary(99999)
    assert result is None


def test_plan_health_returns_none_for_missing_plan(test_db_path):
    service = PlanningService()
    result = service.get_plan_health_summary(99999)
    assert result is None
