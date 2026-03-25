from app.services.retrieval_orchestrator import RetrievalOrchestrator


def test_proactive_query_detection():
    orchestrator = RetrievalOrchestrator()

    assert orchestrator.is_proactive_query("What should I focus on?") is True
    assert orchestrator.is_proactive_query("Give me a check-in") is True
    assert orchestrator.is_proactive_query("What are my priorities?") is True
    assert orchestrator.is_proactive_query("Hello there") is False


def test_proactive_context_used_for_check_in_query(test_db_path):
    orchestrator = RetrievalOrchestrator()

    context = orchestrator.build_context_package(
        query="Give me a check-in on what needs my attention",
        retrieval_mode="balanced"
    )

    assert context["is_proactive_query"] is True
    assert context["proactive"]["used"] is True
    assert context["proactive"]["briefing"] is not None


def test_non_proactive_document_query_skips_proactive_context(test_db_path):
    orchestrator = RetrievalOrchestrator()

    context = orchestrator.build_context_package(
        query="What does the PDF say about embeddings?",
        retrieval_mode="document_first"
    )

    assert context["is_proactive_query"] is False
    assert context["proactive"]["used"] is False
