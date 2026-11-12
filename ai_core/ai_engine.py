"""
MediVerse AI — Central AI Engine (Singleton Facade).
Every module must use this engine for AI operations, never duplicating logic.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional
from uuid import UUID

from ai_core.engines.ocr_engine import OCREngine
from ai_core.engines.nlp_engine import NLPEngine
from ai_core.engines.embedding_engine import EmbeddingEngine
from ai_core.engines.semantic_search_engine import SemanticSearchEngine
from ai_core.engines.llm_engine import LLMEngine
from ai_core.engines.gemini_engine import GeminiEngine
from ai_core.engines.medical_search_engine import MedicalGuidelineSearchEngine
from ai_core.conversation.conversation_manager import ConversationManager
from ai_core.engines.rag_engine import RAGEngine
from ai_core.engines.evidence_engine import EvidenceEngine

from ai_core.pipelines.document_pipeline import DocumentPipeline
from ai_core.pipelines.query_pipeline import QueryPipeline

from core.models.search_result import AIResponse

logger = logging.getLogger("mediverse.ai")

_instance: Optional["AIEngine"] = None


class AIEngine:
    """
    Singleton facade providing unified access to all AI subsystems.
    """
    
    def __init__(self) -> None:
        if _instance is not None:
            raise RuntimeError("AIEngine is a singleton. Use AIEngine.get_instance()")
            
        logger.info("Initializing Central AI Engine...")
        
        # 1. Initialize core engines
        self.ocr = OCREngine()
        self.nlp = NLPEngine()
        self.embedding = EmbeddingEngine()
        self.llm = LLMEngine()
        self.gemini = GeminiEngine()
        self.medical_search = MedicalGuidelineSearchEngine()
        self.conversation = ConversationManager()
        self.search = SemanticSearchEngine(self.embedding)
        self.rag = RAGEngine(
            search_engine=self.search,
            llm_engine=self.llm,
            gemini_engine=self.gemini,
            medical_search_engine=self.medical_search,
            conversation_manager=self.conversation,
        )
        self.evidence = EvidenceEngine()
        
        # 2. Initialize pipelines
        self.document_pipeline = DocumentPipeline(
            ocr_engine=self.ocr,
            nlp_engine=self.nlp,
            embedding_engine=self.embedding,
        )
        self.query_pipeline = QueryPipeline(
            rag_engine=self.rag,
            evidence_engine=self.evidence,
        )
        
        # 3. Pre-load models (can be slow, handled via Splash Screen worker)
        # We don't call .initialize() here to prevent blocking the main thread

    @classmethod
    def get_instance(cls) -> "AIEngine":
        global _instance
        if _instance is None:
            _instance = cls()
        return _instance

    def initialize_models(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """Load heavy AI models into memory."""
        try:
            if progress_callback: progress_callback(10, "Loading NLP models (spaCy/NLTK)")
            self.nlp.initialize()
            
            if progress_callback: progress_callback(50, "Loading Embedding model (SentenceTransformers)")
            self.embedding.initialize()
            
            if progress_callback: progress_callback(80, "Connecting to LLM (Ollama)")
            self.llm.initialize()
            
            if progress_callback: progress_callback(100, "AI Engine Ready")
            logger.info("Central AI Engine fully initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AI Engine models: {e}")
            raise

    # ── Facade Methods for Modules ───────────────────────────────────────

    def process_document(self, document_id: UUID, on_progress: Optional[Callable] = None) -> None:
        """Run a document through the complete intelligence pipeline."""
        self.document_pipeline.process_document(document_id, on_progress)

    def query(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        category: Optional[str] = None,
        provider: Optional[str] = None,
        online_search: Optional[bool] = None,
    ) -> AIResponse:
        """Execute a natural language query against the knowledge repository and guidelines."""
        return self.query_pipeline.execute_query(
            query=query,
            user_id=user_id,
            category_filter=category,
            provider=provider,
            online_search=online_search,
        )

    def set_llm_provider(self, provider: str) -> None:
        """Switch between 'gemini' and 'ollama'."""
        self.rag.set_provider(provider)

    def get_llm_provider(self) -> str:
        """Get currently active LLM provider."""
        return self.rag.active_provider

    def reset_conversation(self) -> None:
        """Reset multi-turn conversation memory."""
        self.conversation.reset()

    @property
    def is_gemini_available(self) -> bool:
        return self.gemini.is_available

    @property
    def is_ollama_available(self) -> bool:
        return self.llm.is_available

    def search_only(self, query: str, category: Optional[str] = None, top_k: int = 10) -> list:
        """Perform semantic search without LLM generation."""
        results, _ = self.search.search(query, top_k=top_k, category_filter=category)
        return results

    def summarize_text(self, text: str, title: str = "") -> str:
        """Generate a summary of a medical text snippet."""
        return self.llm.summarize_document(text, title)
        
    def extract_keywords(self, text: str, max_keywords: int = 10) -> list[str]:
        """Extract medical keywords from text."""
        result = self.nlp.process(text, max_keywords=max_keywords)
        return result.keywords

def get_ai_engine() -> AIEngine:
    """Helper to get the singleton instance."""
    return AIEngine.get_instance()
