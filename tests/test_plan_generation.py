from app.services.planning_service import PlanningService
from app.services.reasoning_service import ReasoningService


def test_normalize_generated_plan():
    service = PlanningService()

    raw = {
        "title": "Improve retrieval quality",
        "goal": "Increase relevance safely",
        "steps": [
            {"step_order": 2, "title": "Tune weights", "description": "Adjust weighting", "status": "pending", "notes": ""},
            {"step_order": 1, "title": "Review scoring", "description": "Inspect current scoring", "status": "pending", "notes": ""}
        ]
    }

    normalized = service._normalize_generated_plan(raw)

    assert normalized["title"] == "Improve retrieval quality"
    assert normalized["goal"] == "Increase relevance safely"
    assert len(normalized["steps"]) == 2
    assert normalized["steps"][0]["step_order"] == 1
    assert normalized["steps"][0]["title"] == "Review scoring"
    assert normalized["steps"][1]["step_order"] == 2
    assert normalized["steps"][1]["title"] == "Tune weights"


def test_normalize_generated_plan_handles_empty_steps():
    service = PlanningService()

    raw = {
        "title": "Empty plan",
        "goal": "Test empty",
        "steps": []
    }

    normalized = service._normalize_generated_plan(raw)

    assert normalized["title"] == "Empty plan"
    assert normalized["goal"] == "Test empty"
    assert len(normalized["steps"]) == 0


def test_normalize_generated_plan_invalid_status_defaults_to_pending():
    service = PlanningService()

    raw = {
        "title": "Status test",
        "goal": "",
        "steps": [
            {"step_order": 1, "title": "Step", "description": "", "status": "invalid_status", "notes": ""}
        ]
    }

    normalized = service._normalize_generated_plan(raw)

    assert normalized["steps"][0]["status"] == "pending"


def test_normalize_generated_plan_missing_title_generates_default():
    service = PlanningService()

    raw = {
        "title": "",
        "goal": "",
        "steps": [
            {"step_order": 1, "title": "", "description": "", "status": "pending", "notes": ""}
        ]
    }

    normalized = service._normalize_generated_plan(raw)

    assert normalized["title"] == "Generated Plan"
    assert normalized["steps"][0]["title"] == "Step 1"


def test_generate_plan_from_reasoning_state_with_mocked_llm(test_db_path):
    reasoning_service = ReasoningService()
    planning_service = PlanningService()

    reasoning_id = reasoning_service.create_reasoning_state(
        task="Improve retrieval quality",
        goal="Increase relevance safely",
        constraints=["Do not break memory safety"],
        assumptions=["Current scoring is heuristic"],
        candidate_actions=["Review scoring", "Tune weighting", "Run evals"],
        confidence=0.74,
        self_check={
            "goal_alignment": True,
            "constraint_risk": "medium",
            "missing_information": []
        },
        status="draft"
    )

    mock_response = {
        "content": """
        {
          "title": "Improve retrieval quality",
          "goal": "Increase relevance safely",
          "steps": [
            {
              "step_order": 1,
              "title": "Review scoring",
              "description": "Inspect current retrieval scoring and identify weak spots",
              "status": "pending",
              "notes": ""
            },
            {
              "step_order": 2,
              "title": "Tune weighting",
              "description": "Adjust retrieval weighting to improve relevance",
              "status": "pending",
              "notes": ""
            },
            {
              "step_order": 3,
              "title": "Run evaluation checks",
              "description": "Validate quality improvements",
              "status": "pending",
              "notes": ""
            }
          ]
        }
        """
    }

    class MockLLM:
        def chat(self, *args, **kwargs):
            return mock_response

    planning_service.llm_service = MockLLM()

    result = planning_service.generate_plan_from_reasoning_state(reasoning_id)

    assert result is not None
    assert result["plan"]["title"] == "Improve retrieval quality"
    assert result["plan"]["reasoning_state_id"] == reasoning_id
    assert len(result["steps"]) == 3
    assert result["steps"][0]["title"] == "Review scoring"
    assert result["steps"][1]["title"] == "Tune weighting"
    assert result["steps"][2]["title"] == "Run evaluation checks"


def test_generate_plan_returns_none_for_missing_reasoning_state(test_db_path):
    planning_service = PlanningService()

    result = planning_service.generate_plan_from_reasoning_state(99999)
    assert result is None
