from app.services.reasoning_service import ReasoningService
from app.services.retrieval_orchestrator import RetrievalOrchestrator


def test_continuity_query_includes_relevant_reasoning_states(test_db_path):
    reasoning_service = ReasoningService()
    orchestrator = RetrievalOrchestrator()

    reasoning_service.create_reasoning_state(
        task="Improve retrieval quality",
        goal="Increase relevance of search results",
        constraints=["Keep latency under 200ms"],
        assumptions=["Current reranking is heuristic-based"],
        candidate_actions=["Tune weighting coefficients", "Add cross-encoder reranker"],
        confidence=0.75,
        self_check={"goal_alignment": True, "constraint_risk": "low", "missing_information": []},
        status="active"
    )

    reasoning_service.create_reasoning_state(
        task="Refactor memory consolidation",
        goal="Reduce duplicate facts",
        candidate_actions=["Merge similar entries"],
        confidence=0.5,
        status="draft"
    )

    context = orchestrator.build_context_package(
        query="Where did we leave off on our project?",
        retrieval_mode="balanced"
    )

    assert context["query_type"] == "project_continuity"
    assert context["reasoning"]["used"] is True
    assert len(context["reasoning"]["states"]) >= 1
    assert context["context_counts"]["reasoning_states"] >= 1
    assert context["retrieval_plan"]["used_reasoning_context"] is True

    top_state = context["reasoning"]["states"][0]
    assert "task" in top_state
    assert "confidence" in top_state


def test_personal_memory_query_skips_reasoning_context(test_db_path):
    reasoning_service = ReasoningService()
    orchestrator = RetrievalOrchestrator()

    reasoning_service.create_reasoning_state(
        task="Some reasoning task",
        goal="Some goal",
        status="active"
    )

    context = orchestrator.build_context_package(
        query="What do you remember about me?",
        retrieval_mode="balanced"
    )

    assert context["query_type"] == "personal_memory"
    assert context["reasoning"]["used"] is False
    assert context["reasoning"]["states"] == []
    assert context["retrieval_plan"]["used_reasoning_context"] is False
