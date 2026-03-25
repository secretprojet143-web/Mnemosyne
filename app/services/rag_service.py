import hashlib
from pathlib import Path
from typing import List, Dict

from app.config import settings, DOCS_DIR
from app.services.document_loader import DocumentLoader
from app.services.vector_service import VectorService


class RAGService:
    def __init__(self):
        self.vector_service = VectorService()
        self.document_loader = DocumentLoader()

    def chunk_text(self, text: str) -> List[str]:
        text = text.strip()
        if not text:
            return []

        chunk_size = settings.RAG_MAX_CHUNK_CHARS
        overlap = settings.RAG_CHUNK_OVERLAP

        chunks = []
        start = 0
        length = len(text)

        while start < length:
            end = min(start + chunk_size, length)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= length:
                break

            start = max(end - overlap, start + 1)

        return chunks

    def add_document_from_path(self, file_path: str) -> Dict:
        text = self.document_loader.load_file(file_path)

        if not text:
            return {
                "success": False,
                "message": "Could not read document."
            }

        chunks = self.chunk_text(text)
        if not chunks:
            return {
                "success": False,
                "message": "No chunks extracted from document."
            }

        file_name = Path(file_path).name
        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:12]

        ids = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            ids.append(f"doc_{file_hash}_{i}")
            metadatas.append({
                "source": file_name,
                "chunk_index": i,
                "type": "document"
            })

        self.vector_service.add_document_chunks(
            ids=ids,
            documents=chunks,
            metadatas=metadatas
        )

        return {
            "success": True,
            "message": f"Indexed {len(chunks)} chunks from {file_name}",
            "file_name": file_name,
            "chunks_indexed": len(chunks)
        }

    def add_raw_text(self, text: str, source_name: str = "manual_input") -> Dict:
        chunks = self.chunk_text(text)
        if not chunks:
            return {
                "success": False,
                "message": "No valid text to index."
            }

        base_hash = hashlib.md5(text.encode()).hexdigest()[:12]

        ids = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            ids.append(f"raw_{base_hash}_{i}")
            metadatas.append({
                "source": source_name,
                "chunk_index": i,
                "type": "raw_text"
            })

        self.vector_service.add_document_chunks(
            ids=ids,
            documents=chunks,
            metadatas=metadatas
        )

        return {
            "success": True,
            "message": f"Indexed {len(chunks)} text chunks",
            "chunks_indexed": len(chunks)
        }

    def retrieve_context(self, query: str, top_k: int | None = None) -> List[Dict]:
        return self.vector_service.search_documents(
            query=query,
            top_k=top_k or settings.RAG_TOP_K
        )
