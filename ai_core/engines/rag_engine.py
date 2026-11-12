"""
MediVerse AI — Unified RAG Engine.
Coordinates:
- Multi-turn conversation intelligence (follow-up query reformulation)
- Local semantic search (ChromaDB)
- Online medical guideline retrieval (PubMed, WHO, CDC, ICMR)
- Dual-LLM support: Gemini Online LLM & Ollama Local LLM (Llama 3.2)
- Google Search grounding integration
- Strict medical safety disclaimers
"""
from __future__ import annotations

import logging
import time
from typing import Optional, List, Dict, Any

from config.settings import get_settings
from core.exceptions import (
    NoEvidenceFoundError,
    LLMError,
    GeminiError,
    GeminiAuthError,
    GeminiNetworkError,
    OllamaNotAvailableError,
)
from core.models.search_result import SearchResult, AIResponse, SourceReference
from ai_core.engines.semantic_search_engine import SemanticSearchEngine
from ai_core.engines.llm_engine import LLMEngine
from ai_core.engines.gemini_engine import GeminiEngine
from ai_core.engines.medical_search_engine import MedicalGuidelineSearchEngine
from ai_core.conversation.conversation_manager import ConversationManager

logger = logging.getLogger("mediverse.ai.rag")

MANDATORY_SAFETY_DISCLAIMER = (
    "\n\n---\n"
    "⚠️ **MEDICAL SAFETY DISCLAIMER**: This automated clinical intelligence is intended strictly for "
    "informational and educational knowledge discovery. It does not constitute a clinical diagnosis, "
    "treatment plan, or medical prescription. Never alter prescribed therapies based solely on AI output. "
    "Consult a qualified, licensed healthcare professional for medical evaluations. In acute or life-threatening emergencies, "
    "seek immediate hospital emergency care."
)


class RAGEngine:
    """
    Retrieval-Augmented Generation engine coordinating local knowledge,
    online guidelines, and configurable LLM providers (Gemini / Ollama).
    """

    def __init__(
        self,
        search_engine: SemanticSearchEngine,
        llm_engine: LLMEngine,
        gemini_engine: Optional[GeminiEngine] = None,
        medical_search_engine: Optional[MedicalGuidelineSearchEngine] = None,
        conversation_manager: Optional[ConversationManager] = None,
    ) -> None:
        self._search = search_engine
        self._llm = llm_engine
        self._gemini = gemini_engine or GeminiEngine()
        self._medical_search = medical_search_engine or MedicalGuidelineSearchEngine()
        self._conversation = conversation_manager or ConversationManager()
        self._settings = get_settings()

        # Default provider from settings or active configuration
        self._active_provider = self._settings.llm_provider

    def set_provider(self, provider: str) -> None:
        """Set active LLM provider ('gemini' or 'ollama')."""
        if provider not in ("gemini", "ollama"):
            raise ValueError(f"Unknown LLM provider: {provider}. Expected 'gemini' or 'ollama'")
        self._active_provider = provider
        logger.info("Active LLM Provider switched to: %s", provider)

    @property
    def active_provider(self) -> str:
        return self._active_provider

    @property
    def conversation_manager(self) -> ConversationManager:
        return self._conversation

    def query(
        self,
        user_query: str,
        category_filter: Optional[str] = None,
        top_k: Optional[int] = None,
        require_evidence: bool = True,
        provider: Optional[str] = None,
        online_search: Optional[bool] = None,
    ) -> AIResponse:
        """
        Execute full RAG retrieval & generation pipeline:
        1. Contextualize query with conversation memory (follow-up intelligence)
        2. Retrieve local knowledge base chunks from ChromaDB
        3. Retrieve online medical guidelines (PubMed/WHO/CDC) if enabled
        4. Query selected LLM (Gemini or Ollama) with grounded context
        5. Enforce non-diagnostic medical disclaimer & citation traceability
        6. Record turn in conversation history
        """
        start_time = time.monotonic()
        top_k = top_k or self._settings.rag_top_k
        chosen_provider = provider or self._active_provider
        use_online = online_search if online_search is not None else self._settings.online_search_enabled

        # Step 1: Follow-Up Question Intelligence & Contextualization
        contextualized = self._conversation.contextualize_query(user_query)
        effective_query = contextualized.standalone_query
        medical_topic = contextualized.medical_topic

        logger.info(
            "Executing RAG Query: Raw='%s' | Effective='%s' | Provider='%s' | OnlineSearch=%s",
            user_query,
            effective_query,
            chosen_provider,
            use_online,
        )

        # Step 2: Local Semantic Search (ChromaDB)
        local_results: List[SearchResult] = []
        try:
            local_results, search_time_ms = self._search.search(
                query=effective_query,
                top_k=top_k,
                category_filter=category_filter,
            )
            logger.info("Local Semantic Search retrieved %d chunks in %dms", len(local_results), search_time_ms)
        except Exception as e:
            logger.warning("Local semantic search encountered an issue: %s", e)

        # Step 3: Online Medical Guideline Search (PubMed/WHO/CDC/ICMR)
        online_sources: List[SourceReference] = []
        if use_online:
            try:
                online_guidelines = self._medical_search.search_guidelines(effective_query, max_results=3)
                online_sources = [g.to_source_reference() for g in online_guidelines]
                logger.info("Online Guideline Search retrieved %d verified references", len(online_sources))
            except Exception as e:
                logger.warning("Online guideline search failed: %s", e)

        local_sources = self._build_sources(local_results)

        # Step 4: Assemble Context
        local_context = self._build_local_context(local_results)
        online_context = self._build_online_context(online_sources)

        context_blocks = []
        if local_context:
            context_blocks.append(f"### [LOCAL REPOSITORY DOCUMENTS]\n{local_context}")
        if online_context:
            context_blocks.append(f"### [OFFICIAL MEDICAL GUIDELINES & PEER-REVIEWED LITERATURE]\n{online_context}")

        combined_context = "\n\n".join(context_blocks).strip()

        # Step 5: Check evidence threshold if local-only and require_evidence
        all_candidate_sources = local_sources + online_sources
        if not all_candidate_sources and require_evidence and chosen_provider == "ollama":
            elapsed = int((time.monotonic() - start_time) * 1000)
            logger.warning("No evidence found in local or online search. RAG pipeline aborted.")
            return AIResponse(
                query=user_query,
                answer=AIResponse.NO_EVIDENCE_MESSAGE + MANDATORY_SAFETY_DISCLAIMER,
                sources=[],
                confidence=0.0,
                processing_time_ms=elapsed,
                has_evidence=False,
                provider=chosen_provider,
                online_search_used=use_online,
                follow_up_topic=medical_topic,
            )

        # Calculate confidence
        confidence = 0.85 if online_sources else 0.50
        if local_results:
            local_conf = sum(r.similarity_score for r in local_results) / len(local_results)
            confidence = max(confidence, local_conf)

        # Step 6: Query Chosen LLM
        answer = ""
        model_used = "retrieval-only"
        grounding_sources: List[SourceReference] = []
        search_queries_used: List[str] = []

        if chosen_provider == "gemini":
            try:
                gemini_res = self._gemini.generate(
                    prompt=effective_query,
                    context=combined_context,
                    conversation_history=contextualized.history_turns,
                    enable_search_grounding=use_online,
                )
                answer = gemini_res["answer"]
                grounding_sources = gemini_res.get("groundings", [])
                search_queries_used = gemini_res.get("search_queries", [])
                model_used = gemini_res.get("model_used", self._settings.gemini_model)
                logger.info("Gemini Online response generated successfully via %s", model_used)
            except (GeminiAuthError, GeminiNetworkError, GeminiError) as e:
                logger.error("Gemini Online generation failed: %s", e)
                # If Gemini fails, do not silently swallow the error — report clear message or fallback
                raise
        else:
            # Ollama Local LLM
            if self._llm.is_available:
                try:
                    answer = self._llm.generate(
                        prompt=effective_query,
                        context=combined_context,
                        temperature=0.1,
                    )
                    model_used = self._settings.ollama_model
                    logger.info("Ollama response generated successfully via %s", model_used)
                except Exception as e:
                    logger.warning("Ollama generation failed: %s", e)
                    answer = self._fallback_answer(local_results, online_sources)
            else:
                logger.warning("Ollama LLM offline. Falling back to retrieved passages.")
                answer = self._fallback_answer(local_results, online_sources)

        # Step 7: Enforce Medical Safety Disclaimer
        if "SAFETY DISCLAIMER" not in answer.upper():
            answer += MANDATORY_SAFETY_DISCLAIMER

        # Step 8: Consolidate & Deduplicate Sources
        final_sources: List[SourceReference] = []
        seen_keys = set()

        for src in local_sources + online_sources + grounding_sources:
            key = src.url or src.document_title.lower()
            if key not in seen_keys:
                seen_keys.add(key)
                final_sources.append(src)

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        # Step 9: Record Dialogue Turn in Conversation Memory
        self._conversation.record_turn(
            user_query=user_query,
            assistant_answer=answer,
            standalone_query=effective_query,
            medical_topic=medical_topic,
            sources_count=len(final_sources),
        )

        return AIResponse(
            query=user_query,
            answer=answer,
            sources=final_sources,
            confidence=round(confidence, 4),
            processing_time_ms=elapsed_ms,
            model_used=model_used,
            has_evidence=len(final_sources) > 0,
            provider=chosen_provider,
            online_search_used=use_online and (len(online_sources) > 0 or len(grounding_sources) > 0),
            search_queries=search_queries_used,
            follow_up_topic=medical_topic,
        )

    def _build_local_context(self, results: list[SearchResult]) -> str:
        """Format local ChromaDB search results."""
        if not results:
            return ""
        parts = []
        for i, r in enumerate(results, 1):
            header = f"[Context {i}] Source: {r.document_title} (Page {r.page_number}, Relevance: {r.score_pct}%)"
            parts.append(f"{header}\n{r.content}")
        return "\n\n".join(parts)

    def _build_online_context(self, sources: list[SourceReference]) -> str:
        """Format retrieved online guidelines."""
        if not sources:
            return ""
        parts = []
        for i, s in enumerate(sources, 1):
            header = f"[Online Guideline {i}] Title: {s.document_title} | Organization: {s.organization} | Date: {s.publication_date} | URL: {s.url}"
            parts.append(f"{header}\nClinical Evidence: {s.chunk_text}")
        return "\n\n".join(parts)

    def _build_sources(self, results: list[SearchResult]) -> list[SourceReference]:
        """Convert local SearchResults to SourceReferences."""
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
                source_type="local",
                organization="Local Knowledge Base",
            )
            for r in results
        ]

    def _fallback_answer(self, local_results: list[SearchResult], online_sources: list[SourceReference]) -> str:
        """Fallback synthesis when LLM is unavailable."""
        parts = ["### 📄 Retrieved Clinical Evidence & Guideline Passages\n"]
        if online_sources:
            parts.append("**Verified Online Guidelines:**\n")
            for i, s in enumerate(online_sources[:3], 1):
                parts.append(f"**{i}. [{s.organization}] {s.document_title}** ({s.publication_date})\n{s.chunk_text}\nURL: {s.url}\n")
        if local_results:
            parts.append("\n**Local Repository Matches:**\n")
            for i, r in enumerate(local_results[:2], 1):
                parts.append(f"**{i}. {r.document_title}** (Page {r.page_number})\n{r.preview}\n")

        parts.append(
            "\n*Note: Direct conversational LLM generation is currently offline. "
            "Displaying retrieved authoritative passages above.*"
        )
        return "\n".join(parts)
