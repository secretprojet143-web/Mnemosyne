import json
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

# Import real AI services from app/
from app.services.memory_service import MemoryService
from app.services.fact_extractor import FactExtractor
from app.services.llm_service import LLMService
from app.services.consolidation_service import ConsolidationService

router = APIRouter(prefix="/memory", tags=["memory"])

memory_service = MemoryService()
fact_extractor = FactExtractor()
llm_service = LLMService()
consolidation_service = ConsolidationService()


@router.get("/facts")
def get_facts(
    category: Optional[str] = None,
    status: str = "active",
    limit: int = Query(50, le=200)
):
    """Get all facts from the real memory system."""
    facts = memory_service.get_active_facts(category=category)
    return {"facts": facts[:limit], "total": len(facts)}


@router.get("/facts/{fact_id}")
def get_fact(fact_id: int):
    """Get a specific fact by ID."""
    fact = memory_service.get_fact_by_id(fact_id)
    if not fact:
        raise HTTPException(404, "Fact not found")
    return fact


@router.post("/extract")
def extract_facts(text: str):
    """Extract facts from text using the real fact extractor."""
    facts = fact_extractor.extract(text)
    return {"extracted": facts, "count": len(facts)}


@router.post("/store")
def store_facts(text: str, conversation_id: int = 0):
    """Extract and store facts from text."""
    if not conversation_id:
        conversation_id = memory_service.create_conversation("API")
    msg_id = memory_service.save_message(conversation_id, "user", text)
    stored = memory_service.extract_and_store_facts(conversation_id, text, msg_id)
    return {"stored": stored, "count": len(stored)}


@router.post("/consolidate")
def consolidate():
    """Run fact consolidation (merge duplicates, supersede old facts)."""
    removed = consolidation_service.consolidate_facts()
    return {"facts_removed": removed}


@router.get("/stats")
def memory_stats():
    """Get real memory statistics."""
    return consolidation_service.get_memory_stats()


@router.post("/chat")
def chat_with_memory(message: str):
    """Chat with the LLM using the full memory context."""
    facts = memory_service.get_active_facts()
    fact_texts = [f["fact_text"] for f in facts[:10]]
    memory_context = "\n".join(f"- {f}" for f in fact_texts) if fact_texts else "No memories yet."

    system = (
        "You are Mnemosyne AI. Use these memories about the user when relevant:\n"
        f"{memory_context}\n\n"
        "Be helpful, personal, and reference memories naturally."
    )

    result = llm_service.simple_chat(message, system_prompt=system)

    # Store the conversation and extract new facts
    conv_id = memory_service.create_conversation("API Chat")
    memory_service.save_message(conv_id, "user", message)
    memory_service.save_message(conv_id, "assistant", result["content"])
    memory_service.extract_and_store_facts(conv_id, message, 0)

    return {
        "response": result["content"],
        "model": result["model"],
        "memories_used": len(facts),
        "usage": result.get("usage", {})
    }
