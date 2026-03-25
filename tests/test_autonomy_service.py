from app.services.autonomy_service import AutonomyService
from app.services.planning_service import PlanningService


def test_create_and_get_autonomy_run(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Autonomy Plan")

    run_id = autonomy.create_autonomy_run(
        plan_id=plan_id,
        status="draft",
        max_steps=5,
        max_tool_calls=10
    )

    run = autonomy.get_autonomy_run_by_id(run_id)

    assert run is not None
    assert run["plan_id"] == plan_id
    assert run["status"] == "draft"
    assert run["max_steps"] == 5
    assert run["max_tool_calls"] == 10
    assert run["steps_executed"] == 0
    assert run["tool_calls_used"] == 0


def test_update_autonomy_run_status_and_counters(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Counter Plan")
    run_id = autonomy.create_autonomy_run(plan_id=plan_id)

    updated = autonomy.update_autonomy_run(
        run_id=run_id,
        status="running",
        steps_executed=2,
        tool_calls_used=3,
        stop_reason="budget check in progress"
    )

    assert updated is not None
    assert updated["status"] == "running"
    assert updated["steps_executed"] == 2
    assert updated["tool_calls_used"] == 3
    assert updated["stop_reason"] == "budget check in progress"


def test_list_autonomy_runs_filters_by_status(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan1 = planning.create_plan(title="Plan A")
    plan2 = planning.create_plan(title="Plan B")

    autonomy.create_autonomy_run(plan_id=plan1, status="draft")
    autonomy.create_autonomy_run(plan_id=plan2, status="running")

    drafts = autonomy.list_autonomy_runs(status="draft")
    running = autonomy.list_autonomy_runs(status="running")

    assert len(drafts) == 1
    assert drafts[0]["status"] == "draft"
    assert len(running) == 1
    assert running[0]["status"] == "running"


def test_autonomy_run_exists(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Exists Plan")
    run_id = autonomy.create_autonomy_run(plan_id=plan_id)

    assert autonomy.autonomy_run_exists(run_id) is True
    assert autonomy.autonomy_run_exists(999999) is False


def test_update_autonomy_run_not_found(test_db_path):
    autonomy = AutonomyService()
    result = autonomy.update_autonomy_run(999999, status="running")
    assert result is None
