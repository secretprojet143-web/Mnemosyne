import pytest

from app.services.planning_service import PlanningService


def test_add_and_list_step_dependencies(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Dependency Plan")
    step1 = service.create_plan_step(plan_id, 1, "Step 1")
    step2 = service.create_plan_step(plan_id, 2, "Step 2")

    dep_id = service.add_step_dependency(plan_id, step2, step1)
    assert dep_id is not None

    deps = service.list_step_dependencies(plan_id)
    assert len(deps) == 1
    assert deps[0]["step_id"] == step2
    assert deps[0]["depends_on_step_id"] == step1


def test_cannot_add_self_dependency(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Self Dependency Plan")
    step1 = service.create_plan_step(plan_id, 1, "Step 1")

    with pytest.raises(ValueError):
        service.add_step_dependency(plan_id, step1, step1)


def test_dependency_steps_must_belong_to_same_plan(test_db_path):
    service = PlanningService()

    plan1 = service.create_plan(title="Plan 1")
    plan2 = service.create_plan(title="Plan 2")

    step1 = service.create_plan_step(plan1, 1, "Plan1 Step")
    step2 = service.create_plan_step(plan2, 1, "Plan2 Step")

    with pytest.raises(ValueError):
        service.add_step_dependency(plan1, step1, step2)


def test_duplicate_dependency_returns_existing_id(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Duplicate Dependency Plan")
    step1 = service.create_plan_step(plan_id, 1, "Step 1")
    step2 = service.create_plan_step(plan_id, 2, "Step 2")

    dep1 = service.add_step_dependency(plan_id, step2, step1)
    dep2 = service.add_step_dependency(plan_id, step2, step1)

    assert dep1 == dep2
    deps = service.list_step_dependencies(plan_id)
    assert len(deps) == 1


def test_blocked_and_ready_steps(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Blocked Ready Plan")
    step1 = service.create_plan_step(plan_id, 1, "Step 1", status="pending")
    step2 = service.create_plan_step(plan_id, 2, "Step 2", status="pending")
    step3 = service.create_plan_step(plan_id, 3, "Step 3", status="pending")

    service.add_step_dependency(plan_id, step2, step1)
    service.add_step_dependency(plan_id, step3, step2)

    blocked = service.get_blocked_steps(plan_id)
    ready = service.get_ready_steps(plan_id)

    blocked_ids = {item["step"]["id"] for item in blocked}
    ready_ids = {item["id"] for item in ready}

    assert step2 in blocked_ids
    assert step3 in blocked_ids
    assert step1 in ready_ids

    service.update_plan_step(step1, status="completed")

    ready_after = service.get_ready_steps(plan_id)
    ready_after_ids = {item["id"] for item in ready_after}

    assert step2 in ready_after_ids


def test_completed_step_not_returned_as_ready_or_blocked(test_db_path):
    service = PlanningService()

    plan_id = service.create_plan(title="Completed Step Plan")
    step1 = service.create_plan_step(plan_id, 1, "Completed Step", status="completed")

    ready = service.get_ready_steps(plan_id)
    blocked = service.get_blocked_steps(plan_id)

    ready_ids = {item["id"] for item in ready}
    blocked_ids = {item["step"]["id"] for item in blocked}

    assert step1 not in ready_ids
    assert step1 not in blocked_ids
