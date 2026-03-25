from app.services.autonomy_service import AutonomyService
from app.services.execution_service import ExecutionService
from app.services.planning_service import PlanningService


def test_environment_snapshot_contains_plan_and_execution_context(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Snapshot Plan")
    planning.create_plan_step(plan_id, 1, "Step 1", status="pending")

    run_id = autonomy.create_autonomy_run(plan_id=plan_id)

    snapshot = autonomy.get_environment_snapshot(run_id)

    assert snapshot is not None
    assert snapshot["run"]["id"] == run_id
    assert snapshot["plan_summary"] is not None
    assert snapshot["plan_health"] is not None
    assert snapshot["execution_health"] is not None
    assert isinstance(snapshot["ready_steps"], list)
    assert isinstance(snapshot["blocked_steps"], list)


def test_readiness_allows_run_with_ready_step_and_budget(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Ready Plan")
    planning.create_plan_step(plan_id, 1, "Step 1", status="pending")

    run_id = autonomy.create_autonomy_run(
        plan_id=plan_id,
        status="draft",
        max_steps=5,
        max_tool_calls=10
    )

    readiness = autonomy.evaluate_run_readiness(run_id)

    assert readiness is not None
    assert readiness["can_proceed"] is True
    assert readiness["next_ready_step"] is not None


def test_readiness_blocks_when_no_ready_steps(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Blocked Readiness Plan")
    planning.create_plan_step(plan_id, 1, "Step 1", status="blocked")

    run_id = autonomy.create_autonomy_run(plan_id=plan_id)

    readiness = autonomy.evaluate_run_readiness(run_id)

    assert readiness is not None
    assert readiness["can_proceed"] is False
    assert any("No ready steps available." in r for r in readiness["reasons"])


def test_readiness_blocks_when_step_budget_exhausted(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Budget Exhausted Plan")
    planning.create_plan_step(plan_id, 1, "Step 1", status="pending")

    run_id = autonomy.create_autonomy_run(
        plan_id=plan_id,
        max_steps=1,
        steps_executed=1
    )

    readiness = autonomy.evaluate_run_readiness(run_id)

    assert readiness is not None
    assert readiness["can_proceed"] is False
    assert any("Step budget exhausted." in r for r in readiness["reasons"])


def test_readiness_reports_retryable_failures(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Retryable Failure Readiness Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Retry step", status="failed")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Temporary network timeout")

    run_id = autonomy.create_autonomy_run(plan_id=plan_id)

    readiness = autonomy.evaluate_run_readiness(run_id)

    assert readiness is not None
    assert readiness["execution_health_status"] == "retryable_failures"
    assert readiness["recovery_hint"] is not None


def test_snapshot_returns_none_for_missing_run(test_db_path):
    autonomy = AutonomyService()
    result = autonomy.get_environment_snapshot(999999)
    assert result is None


def test_readiness_returns_none_for_missing_run(test_db_path):
    autonomy = AutonomyService()
    result = autonomy.evaluate_run_readiness(999999)
    assert result is None
