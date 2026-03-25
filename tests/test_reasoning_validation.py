from app.services.reasoning_service import ReasoningService


def test_validate_reasoning_state_ready_for_action(test_db_path):
    service = ReasoningService()

    reasoning_id = service.create_reasoning_state(
        task="Improve retrieval quality",
        goal="Increase relevance safely",
        constraints=["Do not break memory safety", "Keep latency manageable"],
        assumptions=["Current retrieval is heuristic"],
        candidate_actions=["Tune weights", "Add eval benchmark"],
        confidence=0.72,
        self_check={
            "goal_alignment": True,
            "constraint_risk": "medium",
            "missing_information": ["No benchmark set yet"]
        },
        status="draft"
    )

    validation = service.validate_reasoning_state(reasoning_id)

    assert validation is not None
    assert validation["valid"] is True
    assert validation["ready_for_action"] is True
    assert validation["summary"]["constraint_count"] == 2


def test_validate_reasoning_state_warns_on_missing_constraints(test_db_path):
    service = ReasoningService()

    reasoning_id = service.create_reasoning_state(
        task="Do something important",
        goal="Complete important task",
        constraints=[],
        assumptions=[],
        candidate_actions=[],
        confidence=0.95,
        self_check={
            "goal_alignment": True,
            "constraint_risk": "medium",
            "missing_information": []
        },
        status="draft"
    )

    validation = service.validate_reasoning_state(reasoning_id)

    assert validation is not None
    assert validation["valid"] is True
    assert validation["ready_for_action"] is False
    assert "No constraints defined." in validation["warnings"]
    assert "No candidate actions proposed." in validation["warnings"]


def test_validate_reasoning_payload_detects_overconfidence(test_db_path):
    service = ReasoningService()

    payload = {
        "task": "Optimize cost",
        "goal": "Reduce spending",
        "constraints": [],
        "assumptions": [],
        "candidate_actions": ["Switch providers"],
        "confidence": 0.98,
        "self_check": {
            "goal_alignment": True,
            "constraint_risk": "medium",
            "missing_information": []
        }
    }

    validation = service.validate_reasoning_payload(payload)

    assert validation["valid"] is True
    assert "overconfident" in validation["quality_flags"]
