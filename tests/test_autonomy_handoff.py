import pytest

from app.services.autonomy_service import AutonomyService
from app.services.execution_service import ExecutionService
from app.services.planning_service import PlanningService


def test_pause_and_resume_run(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Pause Resume Plan")
    run_id = autonomy.create_autonomy_run(plan_id=plan_id, status="draft")

    paused = autonomy.pause_run(run_id, reason="Manual pause")
    assert paused is not None
    assert paused["status"] == "paused"
    assert paused["stop_reason"] == "Manual pause"

    resumed = autonomy.resume_run(run_id)
    assert resumed is not None
    assert resumed["status"] == "running"
    assert resumed["stop_reason"] == ""


def test_resume_non_paused_run_raises(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Invalid Resume Plan")
    run_id = autonomy.create_autonomy_run(plan_id=plan_id, status="draft")

    with pytest.raises(ValueError):
        autonomy.resume_run(run_id)


def test_handoff_run_sets_paused_and_summary(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Handoff Plan")
    planning.create_plan_step(plan_id, 1, "Blocked step", status="blocked")
    run_id = autonomy.create_autonomy_run(plan_id=plan_id, status="running")

    handed_off = autonomy.handoff_run(run_id, reason="Needs human review")
    assert handed_off is not None
    assert handed_off["status"] == "paused"

    summary = autonomy.build_handoff_summary(run_id)
    assert summary is not None
    assert summary["recommended_human_action"] is not None


def test_run_next_step_returns_handoff_for_non_retryable_failure(test_db_path):
    planning = PlanningService()
    execution = ExecutionService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Non Retryable Runtime Plan")
    step_id = planning.create_plan_step(plan_id, 1, "Broken step", status="failed")

    execution_id = execution.create_step_execution(plan_id, step_id)
    execution.start_execution(execution_id)
    execution.mark_execution_failed(execution_id, error_message="Unauthorized: invalid API key")

    run_id = autonomy.create_autonomy_run(plan_id=plan_id, status="draft")

    result = autonomy.run_next_step(run_id)

    assert result is not None
    assert result["executed"] is False
    assert result["decision"]["action_type"] == "handoff"
    assert result["handoff_summary"] is not None


def test_complete_run_sets_completed_status(test_db_path):
    planning = PlanningService()
    autonomy = AutonomyService()

    plan_id = planning.create_plan(title="Complete Plan")
    run_id = autonomy.create_autonomy_run(plan_id=plan_id, status="running")

    completed = autonomy.complete_run(run_id, reason="Done")
    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["stop_reason"] == "Done"
