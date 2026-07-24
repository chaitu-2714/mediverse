"""
MediVerse AI — ChromaDB Collection Manager.
Manages the medical_documents collection for storing and querying embeddings.
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

import chromadb
from chromadb import Collection

from config.constants import CHROMA_COLLECTION_NAME, CHROMA_DISTANCE_FUNCTION
from vector_db.chroma_client import get_chroma_client

logger = logging.getLogger("mediverse.vector_db.collections")


class MedicalDocumentCollection:
    """
    Manages the 'medical_documents' ChromaDB collection.
    Handles add, query, delete, and stats operations.
    """

    def __init__(self) -> None:
        self._client = get_chroma_client()
        self._collection = self._get_or_create_collection()

    def _get_or_create_collection(self) -> Collection:
        """Get or create the medical_documents collection."""
        collection = self._client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": CHROMA_DISTANCE_FUNCTION},
        )
        logger.info(
            f"ChromaDB collection '{CHROMA_COLLECTION_NAME}' ready "
            f"({collection.count()} vectors)"
        )
        return collection

    def add_chunks(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Add document chunks with their embeddings to ChromaDB."""
        if not ids:
            return
        # ChromaDB requires all metadata values to be str/int/float/bool
        sanitized_meta = [self._sanitize_metadata(m) for m in metadatas]
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=sanitized_meta,
        )
        logger.debug(f"Added {len(ids)} vectors to ChromaDB")

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: Optional[dict] = None,
        min_score: float = 0.0,
    ) -> dict[str, Any]:
        """
        Query the collection for similar chunks.
        Returns ChromaDB results dict with ids, documents, metadatas, distances.
        """
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)
        return results

    def delete_by_document_id(self, document_id: str) -> int:
        """Delete all chunks belonging to a document."""
        results = self._collection.get(
            where={"document_id": document_id},
            include=[],
        )
        ids_to_delete = results.get("ids", [])
        if ids_to_delete:
            self._collection.delete(ids=ids_to_delete)
            logger.info(f"Deleted {len(ids_to_delete)} vectors for doc={document_id}")
        return len(ids_to_delete)

    def get_document_chunk_ids(self, document_id: str) -> list[str]:
        """Return all ChromaDB IDs for a given document."""
        results = self._collection.get(
            where={"document_id": document_id},
            include=[],
        )
        return results.get("ids", [])

    def count(self) -> int:
        """Return total number of vectors in collection."""
        return self._collection.count()

    def reset(self) -> None:
        """Delete and recreate the collection (use with caution)."""
        self._client.delete_collection(CHROMA_COLLECTION_NAME)
        self._collection = self._get_or_create_collection()
        logger.warning("ChromaDB collection reset")

    @staticmethod
    def _sanitize_metadata(meta: dict[str, Any]) -> dict[str, Any]:
        """Ensure all metadata values are ChromaDB-compatible types."""
        sanitized = {}
        for k, v in meta.items():
            if isinstance(v, (str, int, float, bool)):
                sanitized[k] = v
            elif isinstance(v, UUID):
                sanitized[k] = str(v)
            elif v is None:
                sanitized[k] = ""
            else:
                sanitized[k] = str(v)
        return sanitized
