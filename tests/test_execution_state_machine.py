import pytest

from app.services.execution_service import ExecutionService
from app.services.planning_service import PlanningService


def test_valid_execution_status_transitions(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Transition Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step A")

    execution_id = execution.create_step_execution(plan_id, step_id)

    started = execution.start_execution(execution_id)
    assert started["status"] == "running"
    assert started["started_at"] is not None

    succeeded = execution.mark_execution_succeeded(execution_id, result_summary="Done")
    assert succeeded["status"] == "succeeded"
    assert succeeded["finished_at"] is not None


def test_invalid_execution_transition_raises(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Invalid Transition Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step B")

    execution_id = execution.create_step_execution(plan_id, step_id)

    with pytest.raises(ValueError):
        execution.mark_execution_succeeded(execution_id)


def test_verification_requires_succeeded_status(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Verification Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step C")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)

    with pytest.raises(ValueError):
        execution.mark_execution_verified(execution_id)


def test_verification_allowed_after_success(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Verified Success Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step D")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_succeeded(execution_id, result_summary="Success")

    verified = execution.mark_execution_verified(execution_id)
    assert verified["verification_status"] == "verified"


def test_terminal_execution_status_cannot_transition_again(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Terminal Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step E")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Oops")

    with pytest.raises(ValueError):
        execution.start_execution(execution_id)


def test_cancel_from_pending(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Cancel Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step F")

    execution_id = execution.create_step_execution(plan_id, step_id)

    cancelled = execution.mark_execution_cancelled(execution_id)
    assert cancelled["status"] == "cancelled"
    assert cancelled["finished_at"] is not None


def test_verification_failed_on_failed_execution(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Verify Fail Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step G")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Error")

    vf = execution.mark_execution_verification_failed(execution_id, error_message="Output was wrong")
    assert vf["verification_status"] == "verification_failed"
    assert vf["error_message"] == "Output was wrong"


def test_same_status_transition_is_allowed(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Same Status Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step H")

    execution_id = execution.create_step_execution(plan_id, step_id)

    result = execution.update_step_execution(execution_id, status="pending")
    assert result["status"] == "pending"
