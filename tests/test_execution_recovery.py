from app.services.execution_service import ExecutionService
from app.services.planning_service import PlanningService


def test_classify_retryable_failure(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Retryable Failure Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Network timeout while calling service")

    item = execution.get_step_execution_by_id(execution_id)
    classification = execution.classify_execution_failure(item)

    assert classification["failure_type"] == "retryable"
    assert classification["retryable"] is True


def test_classify_non_retryable_failure(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Non Retryable Failure Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Unauthorized: invalid API key")

    item = execution.get_step_execution_by_id(execution_id)
    classification = execution.classify_execution_failure(item)

    assert classification["failure_type"] == "non_retryable"
    assert classification["retryable"] is False


def test_classify_unknown_failure_with_no_error_message(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Unknown Failure Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id)

    item = execution.get_step_execution_by_id(execution_id)
    classification = execution.classify_execution_failure(item)

    assert classification["failure_type"] == "unknown"
    assert classification["retryable"] is False


def test_recovery_recommends_retry_for_retryable_failure_under_limit(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Recovery Retry Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Temporary network timeout")

    recovery = execution.get_execution_recovery_recommendation(execution_id)

    assert recovery["can_retry"] is True
    assert recovery["recommended_action"] == "retry"


def test_recovery_blocks_retry_after_too_many_attempts(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Retry Limit Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step")

    for _ in range(3):
        execution_id = execution.create_step_execution(plan_id, step_id)
        execution.start_execution(execution_id)
        execution.mark_execution_failed(execution_id, error_message="Temporary network timeout")

    latest = execution.list_step_executions(step_id=step_id, limit=1)[0]
    recovery = execution.get_execution_recovery_recommendation(latest["id"])

    assert recovery["can_retry"] is False
    assert recovery["recommended_action"] == "escalate"


def test_recovery_for_non_failed_execution_needs_no_recovery(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="No Recovery Needed Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)

    recovery = execution.get_execution_recovery_recommendation(execution_id)

    assert recovery["recommended_action"] == "no_recovery_needed"


def test_recovery_recommends_revise_for_non_retryable(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Non Retryable Recovery Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Step")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Forbidden: permission denied")

    recovery = execution.get_execution_recovery_recommendation(execution_id)

    assert recovery["can_retry"] is False
    assert recovery["recommended_action"] == "revise_input_or_permissions"
