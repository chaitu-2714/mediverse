"""
MediVerse AI — Query Pipeline.
Handles full AI queries and logs them to the database.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from ai_core.engines.rag_engine import RAGEngine
from ai_core.engines.evidence_engine import EvidenceEngine
from core.models.search_result import AIResponse
from database.connection import get_db_session
from database.repositories.chunk_repository import SearchRepository

logger = logging.getLogger("mediverse.ai.pipeline.query")


class QueryPipeline:
    """
    Coordinates the user query process:
    RAG Search -> LLM Generation -> Evidence Verification -> DB Logging
    """

    def __init__(
        self,
        rag_engine: RAGEngine,
        evidence_engine: EvidenceEngine,
    ) -> None:
        self._rag = rag_engine
        self._evidence = evidence_engine

    def execute_query(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        category_filter: Optional[str] = None,
        provider: Optional[str] = None,
        online_search: Optional[bool] = None,
    ) -> AIResponse:
        """Execute a query and log the results."""
        logger.info(f"Executing query: '{query}' for user: {user_id} (provider={provider}, online={online_search})")
        
        # 1. RAG Engine builds context and queries LLM
        response = self._rag.query(
            query,
            category_filter=category_filter,
            provider=provider,
            online_search=online_search,
        )
        
        # 2. Verify and format evidence
        verified_response = self._evidence.verify_response(response)
        
        # 3. Log search asynchronously (or synchronously here for simplicity)
        self._log_search(query, verified_response, user_id)
        
        return verified_response

    def _log_search(
        self, 
        query: str, 
        response: AIResponse, 
        user_id: Optional[UUID]
    ) -> None:
        """Log the search query to the database."""
        try:
            with get_db_session() as session:
                repo = SearchRepository(session)
                
                # Get the top document ID if there are sources
                top_doc_id = None
                if response.sources:
                    try:
                        top_doc_id = UUID(response.sources[0].document_id)
                    except ValueError:
                        pass
                
                repo.log_search(
                    query=query,
                    user_id=user_id,
                    result_count=len(response.sources),
                    response_time_ms=response.processing_time_ms,
                    top_document_id=top_doc_id
                )
        except Exception as e:
            # Don't fail the query if logging fails
            logger.error(f"Failed to log search query: {e}")
