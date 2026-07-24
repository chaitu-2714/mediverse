"""
MediVerse AI — RAG Engine.
Retrieval-Augmented Generation: retrieves context, builds prompts, queries LLM.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from ai_core.engines.semantic_search_engine import SemanticSearchEngine
from ai_core.engines.llm_engine import LLMEngine
from core.models.search_result import SearchResult, AIResponse, SourceReference
from core.exceptions import NoEvidenceFoundError, LLMError
from config.settings import get_settings

logger = logging.getLogger("mediverse.ai.rag")


class RAGEngine:
    """
    Retrieval-Augmented Generation engine.
    Enforces the rule: LLM never answers without retrieved context.
    """

    def __init__(
        self,
        search_engine: SemanticSearchEngine,
        llm_engine: LLMEngine,
    ) -> None:
        self._search = search_engine
        self._llm = llm_engine
        self._settings = get_settings()

    def query(
        self,
        user_query: str,
        category_filter: Optional[str] = None,
        top_k: Optional[int] = None,
        require_evidence: bool = True,
    ) -> AIResponse:
        """
        Execute a full RAG pipeline:
        1. Semantic search for relevant chunks
        2. Build context from top results
        3. Generate LLM response grounded in context
        4. Package with evidence references
        """
        start_time = time.monotonic()
        top_k = top_k or self._settings.rag_top_k

        # Step 1: Semantic search
        results, search_time_ms = self._search.search(
            query=user_query,
            top_k=top_k,
            category_filter=category_filter,
        )
        logger.info(f"Semantic Search Completed: retrieved {len(results)} chunks in {search_time_ms}ms")

        # Step 2: Check for evidence
        if not results:
            if require_evidence:
                elapsed = int((time.monotonic() - start_time) * 1000)
                logger.warning("No evidence found in semantic search. RAG pipeline aborted.")
                return AIResponse(
                    query=user_query,
                    answer=AIResponse.NO_EVIDENCE_MESSAGE,
                    sources=[],
                    confidence=0.0,
                    processing_time_ms=elapsed,
                    has_evidence=False,
                )

        # Step 3: Build context
        context = self._build_context(results)
        sources = self._build_sources(results)
        logger.info(f"RAG Context Built: size={len(context)} chars")

        # Step 4: Calculate confidence (avg similarity score)
        confidence = (
            sum(r.similarity_score for r in results) / len(results)
            if results else 0.0
        )

        # Step 5: Query LLM
        answer = ""
        if self._llm.is_available:
            try:
                answer = self._llm.generate(
                    prompt=user_query,
                    context=context,
                    temperature=0.1,
                )
                logger.info("Ollama Response Generated successfully via Llama 3.2")
            except (LLMError, Exception) as e:
                logger.warning(f"LLM generation failed: {e}")
                answer = self._fallback_answer(results)
        else:
            # LLM not available — return best matching chunks
            logger.warning("Ollama LLM node offline. Falling back to semantic search retrieval.")
            answer = self._fallback_answer(results)

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            f"RAG query complete: '{user_query[:40]}' "
            f"sources={len(sources)} confidence={confidence:.2f} "
            f"time={elapsed_ms}ms"
        )

        return AIResponse(
            query=user_query,
            answer=answer,
            sources=sources,
            confidence=round(confidence, 4),
            processing_time_ms=elapsed_ms,
            model_used=self._settings.ollama_model if self._llm.is_available else "retrieval-only",
            has_evidence=len(results) > 0,
        )

    def _build_context(self, results: list[SearchResult]) -> str:
        """
        Build a structured context string from search results.
        Each chunk is prefixed with its source metadata.
        """
        parts = []
        for i, result in enumerate(results, 1):
            header = (
                f"[Context {i}] Source: {result.document_title}, "
                f"Page {result.page_number}, "
                f"Relevance: {result.score_pct}%"
            )
            parts.append(f"{header}\n{result.content}")

        context = "\n\n---\n\n".join(parts)
        logger.debug(f"Built context from {len(results)} chunks ({len(context)} chars)")
        return context

    def _build_sources(self, results: list[SearchResult]) -> list[SourceReference]:
        """Convert search results to SourceReference objects for evidence display."""
        return [
            SourceReference(
                document_id=r.document_id,
                document_title=r.document_title,
                category=r.category,
                page_number=r.page_number,
                chunk_index=r.chunk_index,
                chunk_text=r.preview,
                similarity_score=r.similarity_score,
                chunk_id=r.chunk_id,
            )
            for r in results
        ]

    def _fallback_answer(self, results: list[SearchResult]) -> str:
        """
        When LLM is unavailable, return the top matching chunks as the answer.
        """
        if not results:
            return AIResponse.NO_EVIDENCE_MESSAGE

        parts = [
            f"**Most relevant passages from the knowledge repository:**\n"
        ]
        for i, r in enumerate(results[:3], 1):
            parts.append(
                f"\n**{i}. {r.document_title}** (Page {r.page_number}, "
                f"Score: {r.score_pct}%)\n{r.preview}"
            )

        parts.append(
            "\n\n*Note: AI response generation is currently unavailable (Ollama offline). "
            "Showing retrieved document passages instead.*"
        )
        return "\n".join(parts)
