from app.services.tool_execution_service import ToolExecutionService
from app.services.trust_service import TrustService
from app.services.retrieval_orchestrator import RetrievalOrchestrator


def test_trust_service_annotates_item():
    service = TrustService()

    item = {"content": "Some retrieved text"}
    annotated = service.annotate_item(item, source_type="document")

    assert annotated["_trust_source"] == "document"
    assert annotated["_trust_level"] == "untrusted"
    assert annotated["_can_issue_instructions"] is False
    assert annotated["_can_trigger_actions"] is False
    assert annotated["content"] == "Some retrieved text"


def test_trust_service_annotates_items_batch():
    service = TrustService()

    items = [
        {"content": "Item 1"},
        {"content": "Item 2"}
    ]
    annotated = service.annotate_items(items, source_type="document")

    assert len(annotated) == 2
    assert annotated[0]["_trust_source"] == "document"
    assert annotated[1]["_trust_source"] == "document"


def test_tool_execution_returns_tool_output_trust_metadata(test_db_path):
    service = ToolExecutionService()

    result = service.execute_tool(
        tool_name="calculator",
        payload={"expression": "2 + 2"},
        confirmed=False,
        initiative_mode="balanced",
        source_type="user"
    )

    assert "trust" in result
    assert result["trust"]["source_type"] == "tool_output"
    assert result["trust"]["trust_level"] == "untrusted"


def test_retrieved_document_contexts_include_trust_metadata(test_db_path):
    orchestrator = RetrievalOrchestrator()

    orchestrator.rag_service.retrieve_context = lambda query, top_k=5: [
        {"content": "This is a document.", "metadata": {"source": "doc1"}}
    ]

    context = orchestrator.build_context_package(
        query="What does the document say?",
        retrieval_mode="document_first"
    )

    assert len(context["retrieved_contexts"]) >= 1
    item = context["retrieved_contexts"][0]
    assert item["_trust_source"] == "document"
    assert item["_trust_level"] == "untrusted"
    assert item["_can_issue_instructions"] is False
    assert item["_can_trigger_actions"] is False
