from app.services.memory_service import MemoryService
from app.services.retrieval_orchestrator import RetrievalOrchestrator


def test_query_classification():
    orchestrator = RetrievalOrchestrator()

    assert orchestrator.classify_query("What do you remember about me?") == "personal_memory"
    assert orchestrator.classify_query("What does the document say about embeddings?") == "document_qa"
    assert orchestrator.classify_query("What should I do next?") == "project_continuity"
    assert orchestrator.classify_query("Hello there") == "general_chat"


def test_privacy_safe_mode_reduces_prompt_safe_facts(test_db_path):
    memory_service = MemoryService()
    orchestrator = RetrievalOrchestrator()

    conversation_id = memory_service.create_conversation("Privacy Test")
    msg1 = memory_service.save_message(conversation_id, "user", "My name is Alex")
    memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message="My name is Alex",
        source_message_id=msg1
    )

    balanced = orchestrator.build_context_package(
        query="What do you remember about me?",
        retrieval_mode="balanced"
    )

    privacy_safe = orchestrator.build_context_package(
        query="What do you remember about me?",
        retrieval_mode="privacy_safe"
    )

    assert len(privacy_safe["facts"]) <= len(balanced["facts"])


def test_document_first_mode_increases_document_budget():
    orchestrator = RetrievalOrchestrator()

    balanced = orchestrator.build_context_package(
        query="What does the document say?",
        retrieval_mode="balanced"
    )

    document_first = orchestrator.build_context_package(
        query="What does the document say?",
        retrieval_mode="document_first"
    )

    assert document_first["budget_profile"]["documents"] >= balanced["budget_profile"]["documents"]
