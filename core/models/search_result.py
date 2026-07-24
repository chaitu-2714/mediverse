"""MediVerse AI — SearchResult value object."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID


@dataclass
class SourceReference:
    """Evidence reference for an AI response."""
    document_id: str
    document_title: str
    category: str
    page_number: int
    chunk_index: int
    chunk_text: str
    similarity_score: float
    chunk_id: Optional[str] = None

    @property
    def score_pct(self) -> int:
        return int(self.similarity_score * 100)


@dataclass
class SearchResult:
    """A single semantic search result."""
    chunk_id: str
    document_id: str
    document_title: str
    category: str
    page_number: int
    chunk_index: int
    content: str
    similarity_score: float
    keywords: list[str] = field(default_factory=list)
    medical_entities: list[str] = field(default_factory=list)

    @property
    def preview(self) -> str:
        return self.content[:300] + "..." if len(self.content) > 300 else self.content

    @property
    def score_pct(self) -> int:
        return int(self.similarity_score * 100)

    @property
    def score_label(self) -> str:
        if self.similarity_score >= 0.80:
            return "High"
        elif self.similarity_score >= 0.60:
            return "Medium"
        else:
            return "Low"


@dataclass
class AIResponse:
    """Complete AI response from RAG pipeline."""
    query: str
    answer: str
    sources: list[SourceReference]
    confidence: float
    processing_time_ms: int
    model_used: str = "llama3.2"
    has_evidence: bool = True

    NO_EVIDENCE_MESSAGE = (
        "No supporting evidence found in the indexed knowledge repository. "
        "Please upload relevant medical documents and ensure they are indexed before querying."
    )

    @property
    def confidence_label(self) -> str:
        if self.confidence >= 0.80:
            return "High Confidence"
        elif self.confidence >= 0.60:
            return "Medium Confidence"
        elif self.confidence >= 0.40:
            return "Low Confidence"
        else:
            return "Very Low Confidence"

    @property
    def confidence_pct(self) -> int:
        return int(self.confidence * 100)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "confidence": self.confidence,
            "confidence_label": self.confidence_label,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
            "has_evidence": self.has_evidence,
            "sources": [
                {
                    "document_title": s.document_title,
                    "page_number": s.page_number,
                    "similarity_score": s.similarity_score,
                    "chunk_text": s.chunk_text[:200],
                }
                for s in self.sources
            ],
        }
