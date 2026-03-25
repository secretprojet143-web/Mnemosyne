from app.services.execution_service import ExecutionService
from app.services.planning_service import PlanningService


def test_running_execution_sets_step_in_progress(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Sync Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Run step", status="pending")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)

    step = planning.get_plan_step_by_id(step_id)
    assert step["status"] == "in_progress"


def test_verified_success_sets_step_completed(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Verified Completion Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Finish step", status="pending")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_succeeded(execution_id, result_summary="Done")

    step_mid = planning.get_plan_step_by_id(step_id)
    assert step_mid["status"] == "in_progress"

    execution.mark_execution_verified(execution_id)

    step_final = planning.get_plan_step_by_id(step_id)
    assert step_final["status"] == "completed"


def test_failed_execution_sets_step_failed(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Failed Step Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Failing step", status="pending")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Tool failed")

    step = planning.get_plan_step_by_id(step_id)
    assert step["status"] == "failed"


def test_cancelled_execution_resets_in_progress_step_to_pending(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Cancelled Step Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Cancelable step", status="pending")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_cancelled(execution_id, result_summary="User stopped it")

    step = planning.get_plan_step_by_id(step_id)
    assert step["status"] == "pending"


def test_sync_step_returns_synced_true_on_change(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Sync Detail Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Detail step", status="pending")

    execution_id = execution.create_step_execution(plan_id, step_id)

    result = execution.sync_step_status_from_execution(execution_id)
    assert result["synced"] is False
    assert result["new_step_status"] == "pending"

    execution.start_execution(execution_id)

    result2 = execution.sync_step_status_from_execution(execution_id)
    assert result2["synced"] is False
    assert result2["new_step_status"] == "in_progress"


def test_succeeded_unverified_does_not_complete_step(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()

    plan_id = planning.create_plan(title="Unverified Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Needs verification", status="pending")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_succeeded(execution_id, result_summary="Looks done")

    step = planning.get_plan_step_by_id(step_id)
    assert step["status"] == "in_progress"
