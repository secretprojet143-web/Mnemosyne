import hashlib
from typing import List, Dict

from app.config import settings
from app.services.vector_service import VectorService


class SemanticMemoryService:
    """
    Stores meaningful conversation snippets into vector memory
    and retrieves them later by semantic similarity.
    """

    def __init__(self):
        self.vector_service = VectorService()

    def should_store_message(self, role: str, content: str) -> bool:
        if role not in ("user", "assistant"):
            return False

        text = content.strip()
        if len(text) < 25:
            return False

        important_keywords = [
            "my name", "i am", "i'm", "i live", "i work", "i like", "i love",
            "project", "goal", "remember", "important", "preference", "learning",
            "problem", "issue", "bug", "plan", "idea"
        ]

        lowered = text.lower()

        if any(keyword in lowered for keyword in important_keywords):
            return True

        return len(text) >= 120

    def build_memory_text(self, role: str, content: str) -> str:
        if role == "user":
            return f"User said: {content}"
        return f"Assistant said: {content}"

    def store_message_memory(
        self,
        conversation_id: int,
        message_id: int,
        role: str,
        content: str
    ) -> bool:
        if not self.should_store_message(role, content):
            return False

        chunk_id = self._make_chunk_id(conversation_id, message_id, role, content)

        if self.vector_service.memory_exists(chunk_id):
            return False

        memory_text = self.build_memory_text(role, content)

        self.vector_service.add_memory_chunks(
            ids=[chunk_id],
            documents=[memory_text],
            metadatas=[{
                "conversation_id": conversation_id,
                "message_id": message_id,
                "role": role,
                "type": "conversation_memory"
            }]
        )

        return True

    def retrieve_relevant_memories(self, query: str, top_k: int | None = None) -> List[Dict]:
        return self.vector_service.search_memory(
            query=query,
            top_k=top_k or settings.RAG_TOP_K
        )

    def _make_chunk_id(self, conversation_id: int, message_id: int, role: str, content: str) -> str:
        base = f"{conversation_id}:{message_id}:{role}:{content[:80]}"
        digest = hashlib.md5(base.encode()).hexdigest()[:16]
        return f"mem_{conversation_id}_{message_id}_{digest}"
