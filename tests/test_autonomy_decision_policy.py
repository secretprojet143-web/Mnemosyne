from app.services.autonomy_service import AutonomyService
from app.services.execution_service import ExecutionService
from app.services.planning_service import PlanningService


def test_select_next_action_chooses_ready_step_when_no_failures(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Ready Step Action Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Ready step", status="pending")

    run_id = autonomy.create_autonomy_run(plan_id=plan_id)

    decision = autonomy.select_next_autonomy_action(run_id)

    assert decision is not None
    assert decision["action_type"] == "start_ready_step"
    assert decision["target"]["id"] == step_id


def test_select_next_action_prefers_retryable_failure(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Retry First Plan")
    step1 = planning.create_plan_step(plan_id, 1, "Failed step", status="failed")
    step2 = planning.create_plan_step(plan_id, 2, "Ready step", status="pending")

    execution_id = execution.create_step_execution(plan_id, step1)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Temporary network timeout")

    run_id = autonomy.create_autonomy_run(plan_id=plan_id)

    decision = autonomy.select_next_autonomy_action(run_id)

    assert decision is not None
    assert decision["action_type"] == "retry_execution"
    assert decision["target"]["step_id"] == step1


def test_select_next_action_stops_on_manual_intervention_needed(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Manual Intervention Plan")
    step1 = planning.create_plan_step(plan_id, 1, "Broken step", status="failed")

    execution_id = execution.create_step_execution(plan_id, step1)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Unauthorized: invalid API key")

    run_id = autonomy.create_autonomy_run(plan_id=plan_id)

    decision = autonomy.select_next_autonomy_action(run_id)

    assert decision is not None
    assert decision["action_type"] == "handoff"
    assert "manual intervention" in decision["reason"].lower() or "require manual intervention" in decision["reason"].lower()


def test_run_next_step_retries_failed_step_before_advancing(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Retry Runtime Plan")
    failed_step = planning.create_plan_step(plan_id, 1, "Retry me", status="failed")
    ready_step = planning.create_plan_step(plan_id, 2, "Ready later", status="pending")

    old_execution_id = execution.create_step_execution(plan_id, failed_step)
    execution.start_execution(old_execution_id)
    execution.mark_execution_failed(old_execution_id, error_message="Temporary network timeout")

    run_id = autonomy.create_autonomy_run(plan_id=plan_id)

    result = autonomy.run_next_step(run_id)

    assert result is not None
    assert result["executed"] is True
    assert result["decision"]["action_type"] == "retry_execution"
    assert result["step"]["id"] == failed_step
    assert result["execution"]["attempt_number"] == 2
