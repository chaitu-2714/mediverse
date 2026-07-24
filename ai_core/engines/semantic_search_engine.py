"""
MediVerse AI — Semantic Search Engine.
Performs vector similarity search over ChromaDB with metadata enrichment from PostgreSQL.
"""
from __future__ import annotations

import logging
import time
from typing import Optional
from uuid import UUID

from ai_core.engines.embedding_engine import EmbeddingEngine
from core.exceptions import SearchError
from core.models.search_result import SearchResult
from config.settings import get_settings

logger = logging.getLogger("mediverse.ai.search")


class SemanticSearchEngine:
    """
    Google-like semantic search engine for medical documents.
    Embeds queries, searches ChromaDB, enriches results from PostgreSQL.
    """

    def __init__(self, embedding_engine: EmbeddingEngine) -> None:
        self._embedding = embedding_engine
        self._settings = get_settings()
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            from vector_db.collections import MedicalDocumentCollection
            self._collection = MedicalDocumentCollection()
        return self._collection

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        category_filter: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> tuple[list[SearchResult], int]:
        """
        Execute semantic search.
        Returns (results, processing_time_ms).
        """
        if not query.strip():
            raise SearchError("Query cannot be empty")

        start_time = time.monotonic()
        top_k = top_k or self._settings.search_top_k
        min_score = min_score or self._settings.search_min_score

        try:
            # 1. Embed the query
            query_embedding = self._embedding.embed_query(query)
            if not query_embedding:
                raise SearchError("Failed to generate query embedding")

            # 2. Query ChromaDB
            where_filter = None
            if category_filter:
                where_filter = {"category": category_filter}

            collection = self._get_collection()
            raw_results = collection.query(
                query_embedding=query_embedding,
                n_results=top_k,
                where=where_filter,
            )

            # 3. Parse and enrich results
            results = self._parse_results(raw_results, min_score)

            # 4. Log search
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.info(
                f"Semantic search: '{query[:50]}' → {len(results)} results in {elapsed_ms}ms"
            )
            return results, elapsed_ms

        except SearchError:
            raise
        except Exception as e:
            raise SearchError(str(e)) from e

    def _parse_results(self, raw: dict, min_score: float) -> list[SearchResult]:
        """Convert ChromaDB raw results to SearchResult objects."""
        results: list[SearchResult] = []

        ids_list = raw.get("ids", [[]])[0]
        docs_list = raw.get("documents", [[]])[0]
        metas_list = raw.get("metadatas", [[]])[0]
        dists_list = raw.get("distances", [[]])[0]

        for chunk_id, doc_text, meta, distance in zip(
            ids_list, docs_list, metas_list, dists_list
        ):
            # ChromaDB returns cosine distance (0=identical, 2=opposite)
            # Convert to similarity score [0, 1]
            similarity = max(0.0, 1.0 - (distance / 2.0))

            if similarity < min_score:
                continue

            result = SearchResult(
                chunk_id=chunk_id,
                document_id=meta.get("document_id", ""),
                document_title=meta.get("title", "Unknown"),
                category=meta.get("category", ""),
                page_number=int(meta.get("page_number", 0)),
                chunk_index=int(meta.get("chunk_index", 0)),
                content=doc_text or "",
                similarity_score=round(similarity, 4),
                keywords=meta.get("keywords", "").split(",") if meta.get("keywords") else [],
            )
            results.append(result)

        # Sort by similarity descending
        results.sort(key=lambda r: r.similarity_score, reverse=True)
        return results

    def search_by_document(self, query: str, document_id: str, top_k: int = 5) -> list[SearchResult]:
        """Search within a specific document only."""
        start_time = time.monotonic()
        query_embedding = self._embedding.embed_query(query)
        collection = self._get_collection()
        raw = collection.query(
            query_embedding=query_embedding,
            n_results=top_k,
            where={"document_id": document_id},
        )
        return self._parse_results(raw, min_score=0.0)
