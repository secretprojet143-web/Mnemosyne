from app.services.autonomy_service import AutonomyService
from app.services.execution_service import ExecutionService
from app.services.planning_service import PlanningService


def test_run_next_step_starts_ready_step_execution(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Autonomy Runtime Plan")
    step_id = planning.create_plan_step(plan_id, 1, "First step", status="pending")

    run_id = autonomy.create_autonomy_run(
        plan_id=plan_id,
        status="draft",
        max_steps=5,
        max_tool_calls=10
    )

    result = autonomy.run_next_step(run_id)

    assert result is not None
    assert result["executed"] is True
    assert result["step"]["id"] == step_id
    assert result["execution"]["status"] == "running"

    updated_run = autonomy.get_autonomy_run_by_id(run_id)
    assert updated_run["steps_executed"] == 1
    assert updated_run["status"] == "running"


def test_run_next_step_stops_when_not_ready(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Blocked Runtime Plan")
    planning.create_plan_step(plan_id, 1, "Blocked step", status="blocked")

    run_id = autonomy.create_autonomy_run(plan_id=plan_id, status="draft")

    result = autonomy.run_next_step(run_id)

    assert result is not None
    assert result["executed"] is False
    assert result["decision"]["action_type"] == "stop"

    updated_run = autonomy.get_autonomy_run_by_id(run_id)
    assert updated_run["status"] == "stopped"
    assert updated_run["stop_reason"] != ""


def test_run_next_step_stops_when_budget_exhausted(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Budget Runtime Plan")
    planning.create_plan_step(plan_id, 1, "Step 1", status="pending")

    run_id = autonomy.create_autonomy_run(
        plan_id=plan_id,
        status="draft",
        max_steps=1,
        steps_executed=1
    )

    result = autonomy.run_next_step(run_id)

    assert result is not None
    assert result["executed"] is False

    updated_run = autonomy.get_autonomy_run_by_id(run_id)
    assert updated_run["status"] == "stopped"
    assert "budget" in updated_run["stop_reason"].lower()


def test_run_next_step_returns_none_for_missing_run(test_db_path):
    autonomy = AutonomyService()

    result = autonomy.run_next_step(999999)
    assert result is None
