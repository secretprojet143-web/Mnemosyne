from app.services.reasoning_service import ReasoningService


def test_summarize_reasoning_quality_low_confidence(test_db_path):
    service = ReasoningService()

    state = {
        "task": "Optimize cost",
        "goal": "Reduce spending",
        "constraints": ["Stay within budget"],
        "assumptions": ["Current provider is expensive"],
        "candidate_actions": ["Switch provider"],
        "confidence": 0.2,
        "self_check": {
            "goal_alignment": True,
            "constraint_risk": "medium",
            "missing_information": ["No pricing comparison yet"]
        }
    }

    quality = service.summarize_reasoning_quality(state)

    assert quality["confidence_label"] == "low"
    assert quality["missing_information_count"] == 1
    assert any("low" in line.lower() for line in quality["caution_lines"])


def test_summarize_reasoning_quality_high_constraint_risk(test_db_path):
    service = ReasoningService()

    state = {
        "task": "Migrate database",
        "goal": "Zero downtime migration",
        "constraints": ["No data loss", "Maintain availability"],
        "assumptions": ["New DB is compatible"],
        "candidate_actions": ["Blue-green deploy", "Shadow writes"],
        "confidence": 0.6,
        "self_check": {
            "goal_alignment": True,
            "constraint_risk": "high",
            "missing_information": []
        }
    }

    quality = service.summarize_reasoning_quality(state)

    assert quality["confidence_label"] == "medium"
    assert quality["constraint_risk"] == "high"
    assert any("constraint risk is high" in line.lower() for line in quality["caution_lines"])


def test_summarize_reasoning_quality_ready_for_action(test_db_path):
    service = ReasoningService()

    state = {
        "task": "Improve retrieval quality",
        "goal": "Increase relevance safely",
        "constraints": ["Do not break memory safety"],
        "assumptions": ["Current scoring is heuristic"],
        "candidate_actions": ["Tune weighting"],
        "confidence": 0.82,
        "self_check": {
            "goal_alignment": True,
            "constraint_risk": "low",
            "missing_information": []
        }
    }

    quality = service.summarize_reasoning_quality(state)

    assert quality["confidence_label"] == "high"
    assert quality["ready_for_action"] is True
    assert quality["constraint_risk"] == "low"


def test_get_reasoning_quality_report(test_db_path):
    service = ReasoningService()

    reasoning_id = service.create_reasoning_state(
        task="Test reasoning quality",
        goal="Validate quality reporting",
        constraints=["Keep system safe"],
        assumptions=["This is a test"],
        candidate_actions=["Run quality check"],
        confidence=0.7,
        self_check={
            "goal_alignment": True,
            "constraint_risk": "medium",
            "missing_information": []
        },
        status="draft"
    )

    report = service.get_reasoning_quality_report(reasoning_id)

    assert report is not None
    assert report["reasoning_state_id"] == reasoning_id
    assert report["task"] == "Test reasoning quality"
    assert "quality" in report


def test_get_reasoning_quality_report_not_found(test_db_path):
    service = ReasoningService()
    report = service.get_reasoning_quality_report(99999)
    assert report is None
