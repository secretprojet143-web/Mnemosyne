from app.services.reasoning_service import ReasoningService


def test_normalize_reasoning_state_payload():
    service = ReasoningService()

    raw = {
        "task": "Improve retrieval quality",
        "goal": "Increase relevance",
        "constraints": ["Keep latency low"],
        "assumptions": "Current scoring is heuristic",
        "candidate_actions": ["Tune weights", "Add reranker"],
        "selected_action": "",
        "confidence": 1.2,
        "self_check": {
            "goal_alignment": True,
            "constraint_risk": "medium",
            "missing_information": ["No benchmark set"]
        },
        "status": "draft"
    }

    normalized = service._normalize_reasoning_state_payload(raw)

    assert normalized["task"] == "Improve retrieval quality"
    assert normalized["constraints"] == ["Keep latency low"]
    assert normalized["assumptions"] == ["Current scoring is heuristic"]
    assert normalized["confidence"] == 1.0
    assert normalized["self_check"]["constraint_risk"] == "medium"


def test_generate_reasoning_state_from_input_with_mocked_llm(monkeypatch, test_db_path):
    service = ReasoningService()

    mock_response = {
        "content": """
        {
          "task": "Improve retrieval quality",
          "goal": "Increase relevance while preserving safety",
          "constraints": ["Do not break memory safety", "Keep latency manageable"],
          "assumptions": ["Current scoring is heuristic"],
          "candidate_actions": ["Tune weighting", "Add benchmark eval"],
          "selected_action": "",
          "confidence": 0.74,
          "self_check": {
            "goal_alignment": true,
            "constraint_risk": "medium",
            "missing_information": ["No formal benchmark suite yet"]
          },
          "status": "draft"
        }
        """
    }

    class MockLLM:
        def chat(self, *args, **kwargs):
            return mock_response

    service.llm_service = MockLLM()

    state = service.generate_reasoning_state_from_input(
        user_input="Help me improve Mnemosyne retrieval quality."
    )

    assert state["task"] == "Improve retrieval quality"
    assert state["goal"] == "Increase relevance while preserving safety"
    assert len(state["constraints"]) == 2
    assert state["confidence"] == 0.74
    assert state["status"] == "draft"
