from typing import List, Dict, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import VECTOR_DIR


class VectorService:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=str(VECTOR_DIR),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        self.memory_collection = self.client.get_or_create_collection(name="memory_chunks")
        self.document_collection = self.client.get_or_create_collection(name="document_chunks")

    def add_memory_chunks(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None
    ):
        self.memory_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def search_memory(self, query: str, top_k: int = 5) -> List[Dict]:
        results = self.memory_collection.query(
            query_texts=[query],
            n_results=top_k
        )
        return self._normalize_results(results)

    def add_document_chunks(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None
    ):
        self.document_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def search_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        results = self.document_collection.query(
            query_texts=[query],
            n_results=top_k
        )
        return self._normalize_results(results)

    def memory_exists(self, chunk_id: str) -> bool:
        result = self.memory_collection.get(ids=[chunk_id])
        return bool(result and result.get("ids"))

    def _normalize_results(self, results: Dict) -> List[Dict]:
        normalized = []

        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
        distances = results.get("distances", [[]])[0] if results.get("distances") else []

        for i, doc_id in enumerate(ids):
            normalized.append({
                "id": doc_id,
                "content": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "distance": distances[i] if i < len(distances) else None,
            })

        return normalized
