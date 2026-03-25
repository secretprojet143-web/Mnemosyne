from app.services.execution_service import ExecutionService
from app.services.planning_service import PlanningService


def test_create_and_get_step_execution(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Execution Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Run validation step")

    execution_id = execution.create_step_execution(
        plan_id=plan_id,
        step_id=step_id,
        action_type="manual",
        action_payload={"note": "initial attempt"},
        status="pending",
        verification_status="unverified"
    )

    item = execution.get_step_execution_by_id(execution_id)

    assert item is not None
    assert item["plan_id"] == plan_id
    assert item["step_id"] == step_id
    assert item["attempt_number"] == 1
    assert item["action_payload"]["note"] == "initial attempt"


def test_attempt_number_increments_per_step(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Retry Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Retryable step")

    e1 = execution.create_step_execution(plan_id, step_id)
    e2 = execution.create_step_execution(plan_id, step_id)

    item1 = execution.get_step_execution_by_id(e1)
    item2 = execution.get_step_execution_by_id(e2)

    assert item1["attempt_number"] == 1
    assert item2["attempt_number"] == 2


def test_update_step_execution_status_and_verification(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Execution Update Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Check result")

    execution_id = execution.create_step_execution(plan_id, step_id)

    execution.start_execution(execution_id)

    updated = execution.update_step_execution(
        execution_id=execution_id,
        status="succeeded",
        verification_status="verified",
        result_summary="Step completed successfully.",
        started_at="2026-01-01T10:00:00",
        finished_at="2026-01-01T10:01:00"
    )

    assert updated is not None
    assert updated["status"] == "succeeded"
    assert updated["verification_status"] == "verified"
    assert updated["result_summary"] == "Step completed successfully."
    assert updated["started_at"] == "2026-01-01T10:00:00"
    assert updated["finished_at"] == "2026-01-01T10:01:00"


def test_list_step_executions_filters(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Filter Plan")
    step1 = planning.create_plan_step(plan_id, 1, "Step 1")
    step2 = planning.create_plan_step(plan_id, 2, "Step 2")

    execution.create_step_execution(plan_id, step1, status="pending")
    execution.create_step_execution(plan_id, step2, status="failed", verification_status="verification_failed")

    failed = execution.list_step_executions(status="failed")
    assert len(failed) == 1
    assert failed[0]["status"] == "failed"

    verification_failed = execution.list_step_executions(verification_status="verification_failed")
    assert len(verification_failed) == 1
    assert verification_failed[0]["verification_status"] == "verification_failed"


def test_create_execution_for_wrong_plan_returns_none(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Plan A")
    other_plan = planning.create_plan(title="Plan B")
    step_in_other = planning.create_plan_step(other_plan, 1, "Other step")

    result = execution.create_step_execution(plan_id, step_in_other)
    assert result is None


def test_execution_exists(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Existence Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step")

    execution_id = execution.create_step_execution(plan_id, step_id)

    assert execution.execution_exists(execution_id) is True
    assert execution.execution_exists(99999) is False
