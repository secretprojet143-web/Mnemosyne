from app.services.reasoning_service import ReasoningService


def test_create_and_get_reasoning_state(test_db_path):
    service = ReasoningService()

    reasoning_id = service.create_reasoning_state(
        task="Improve retrieval quality",
        goal="Increase relevance",
        constraints=["Keep latency low", "Do not break memory safety"],
        assumptions=["Current reranking is heuristic"],
        candidate_actions=["Tune weighting", "Add better reranker"],
        confidence=0.72,
        self_check={"goal_alignment": True},
        status="draft"
    )

    state = service.get_reasoning_state_by_id(reasoning_id)

    assert state is not None
    assert state["task"] == "Improve retrieval quality"
    assert state["goal"] == "Increase relevance"
    assert len(state["constraints"]) == 2
    assert len(state["assumptions"]) == 1
    assert len(state["candidate_actions"]) == 2
    assert state["confidence"] == 0.72
    assert state["self_check"]["goal_alignment"] is True


def test_update_reasoning_state(test_db_path):
    service = ReasoningService()

    reasoning_id = service.create_reasoning_state(
        task="Initial task",
        status="draft"
    )

    updated = service.update_reasoning_state(
        reasoning_id=reasoning_id,
        task="Updated task",
        selected_action="Tune weighting",
        confidence=0.81,
        status="active"
    )

    assert updated is not None
    assert updated["task"] == "Updated task"
    assert updated["selected_action"] == "Tune weighting"
    assert updated["confidence"] == 0.81
    assert updated["status"] == "active"


def test_list_reasoning_states_filters_by_status(test_db_path):
    service = ReasoningService()

    service.create_reasoning_state(task="Task A", status="draft")
    service.create_reasoning_state(task="Task B", status="active")

    active_states = service.list_reasoning_states(status="active")
    draft_states = service.list_reasoning_states(status="draft")

    assert len(active_states) == 1
    assert active_states[0]["task"] == "Task B"
    assert len(draft_states) == 1
    assert draft_states[0]["task"] == "Task A"
