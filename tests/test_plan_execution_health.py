from app.services.execution_service import ExecutionService
from app.services.planning_service import PlanningService


def test_plan_execution_health_healthy_with_no_failures(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Healthy Execution Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step A")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_succeeded(execution_id, result_summary="Done")
    execution.mark_execution_verified(execution_id)

    summary = planning.get_plan_execution_health_summary(plan_id)

    assert summary is not None
    assert summary["execution_health_status"] == "healthy"
    assert summary["failed_execution_count"] == 0
    assert summary["retryable_failed_step_count"] == 0
    assert summary["next_execution_action"] is None


def test_plan_execution_health_detects_retryable_failures(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Retryable Failure Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step B")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Temporary network timeout")

    summary = planning.get_plan_execution_health_summary(plan_id)

    assert summary is not None
    assert summary["execution_health_status"] == "retryable_failures"
    assert summary["retryable_failed_step_count"] >= 1
    assert summary["next_execution_action"] is not None
    assert summary["next_execution_action"]["type"] == "retry_step"
    assert summary["next_execution_action"]["step_id"] == step_id


def test_plan_execution_health_detects_manual_intervention_needed(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Manual Intervention Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step C")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Unauthorized: invalid API key")

    summary = planning.get_plan_execution_health_summary(plan_id)

    assert summary is not None
    assert summary["execution_health_status"] == "requires_intervention"
    assert summary["retryable_failed_step_count"] == 0
    assert summary["next_execution_action"] is None
    assert summary["recovery_items"][0]["recommended_action"] == "revise_input_or_permissions"


def test_plan_execution_health_with_no_executions(test_db_path):
    planning = PlanningService()

    plan_id = planning.create_plan(title="No Executions Plan")
    planning.create_plan_step(plan_id, 1, "Step D")

    summary = planning.get_plan_execution_health_summary(plan_id)

    assert summary is not None
    assert summary["execution_health_status"] == "healthy"
    assert summary["failed_execution_count"] == 0


def test_plan_execution_health_returns_none_for_missing_plan(test_db_path):
    planning = PlanningService()

    result = planning.get_plan_execution_health_summary(99999)
    assert result is None
