"""MediVerse AI — Document and Chunk domain entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from config.constants import DocumentCategory, ProcessingStatus


@dataclass
class MedicalEntity:
    """A recognized medical entity from NLP processing."""
    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class Document:
    """Domain entity representing an uploaded medical document."""
    id: UUID
    title: str
    original_filename: str
    file_path: str
    category: DocumentCategory
    uploaded_by: UUID

    file_size: int = 0
    file_type: str = "pdf"
    page_count: int = 0
    language: str = "en"

    author: Optional[str] = None
    publication_date: Optional[datetime] = None
    summary: Optional[str] = None

    keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    medical_entities: list[MedicalEntity] = field(default_factory=list)

    embedding_status: ProcessingStatus = ProcessingStatus.PENDING
    is_indexed: bool = False
    is_bookmarked: bool = False
    version: int = 1

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def file_size_mb(self) -> float:
        return self.file_size / (1024 * 1024)

    @property
    def category_display(self) -> str:
        from config.constants import CATEGORY_DISPLAY_NAMES
        return CATEGORY_DISPLAY_NAMES.get(self.category, self.category)

    @property
    def is_ready(self) -> bool:
        return self.embedding_status == ProcessingStatus.COMPLETE and self.is_indexed

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "title": self.title,
            "category": self.category,
            "file_size_mb": round(self.file_size_mb, 2),
            "page_count": self.page_count,
            "language": self.language,
            "keywords": self.keywords,
            "tags": self.tags,
            "embedding_status": self.embedding_status,
            "is_indexed": self.is_indexed,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class DocumentChunk:
    """A text chunk from a document used for embedding and RAG."""
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    page_number: int = 0
    char_start: int = 0
    char_end: int = 0
    token_count: int = 0
    chroma_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def preview(self) -> str:
        """Return first 200 characters as a preview."""
        return self.content[:200] + "..." if len(self.content) > 200 else self.content
