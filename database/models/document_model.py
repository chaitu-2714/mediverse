"""MediVerse AI — Document ORM Model."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, BigInteger, String, Text, Date, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from database.base import Base
from config.constants import DocumentCategory, ProcessingStatus
from database.models.chunk_model import DocumentChunkModel
from database.models.audit_log_model import BookmarkModel, ProcessingQueueModel


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    category: Mapped[str] = mapped_column(
        String(100), nullable=False,
        default=DocumentCategory.UNCATEGORIZED, index=True
    )
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    publication_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    medical_entities: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    embedding_status: Mapped[str] = mapped_column(
        String(50), nullable=False,
        default=ProcessingStatus.PENDING, index=True
    )
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    uploader: Mapped[Optional[object]] = relationship("UserModel", back_populates="documents")
    chunks: Mapped[list[DocumentChunkModel]] = relationship(
        "DocumentChunkModel", back_populates="document",
        cascade="all, delete-orphan"
    )
    bookmarks: Mapped[list[BookmarkModel]] = relationship("BookmarkModel", back_populates="document")
    processing_queue: Mapped[list[ProcessingQueueModel]] = relationship(
        "ProcessingQueueModel", back_populates="document",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document title={self.title!r} category={self.category}>"
