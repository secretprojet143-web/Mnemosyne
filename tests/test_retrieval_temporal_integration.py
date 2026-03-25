from app.services.memory_service import MemoryService
from app.services.retrieval_orchestrator import RetrievalOrchestrator


def test_temporal_query_is_detected_and_context_is_used(test_db_path):
    memory_service = MemoryService()
    orchestrator = RetrievalOrchestrator()

    conversation_id = memory_service.create_conversation("Temporal Retrieval Test")

    msg1 = memory_service.save_message(conversation_id, "user", "I live in Berlin")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I live in Berlin",
        source_message_id=msg1
    )

    msg2 = memory_service.save_message(conversation_id, "user", "I live in Toronto")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="I live in Toronto",
        source_message_id=msg2
    )

    context = orchestrator.build_context_package(
        query="What changed about where I live?",
        conversation_id=conversation_id,
        retrieval_mode="balanced"
    )

    assert context["is_temporal_query"] is True
    assert context["temporal"]["used"] is True
    assert len(context["temporal"]["summaries"]) >= 1
    assert any("changed from berlin to toronto" in item["summary"].lower() for item in context["temporal"]["summaries"])


def test_non_temporal_document_query_does_not_use_temporal_context(test_db_path):
    orchestrator = RetrievalOrchestrator()

    context = orchestrator.build_context_package(
        query="What does the document say about embeddings?",
        retrieval_mode="document_first"
    )

    assert context["query_type"] == "document_qa"
    assert context["temporal"]["used"] is False
