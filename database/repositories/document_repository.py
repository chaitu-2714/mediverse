"""MediVerse AI — Document Repository."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from database.models.document_model import DocumentModel
from database.repositories.base_repository import BaseRepository
from config.constants import ProcessingStatus

logger = logging.getLogger("mediverse.repository.document")


class DocumentRepository(BaseRepository[DocumentModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DocumentModel)

    def get_by_category(self, category: str, limit: int = 100) -> list[DocumentModel]:
        return (
            self._session.query(DocumentModel)
            .filter(DocumentModel.category == category)
            .order_by(desc(DocumentModel.created_at))
            .limit(limit)
            .all()
        )

    def get_indexed(self) -> list[DocumentModel]:
        return (
            self._session.query(DocumentModel)
            .filter(DocumentModel.is_indexed == True)
            .all()
        )

    def get_pending_processing(self) -> list[DocumentModel]:
        return (
            self._session.query(DocumentModel)
            .filter(DocumentModel.embedding_status == ProcessingStatus.PENDING)
            .all()
        )

    def search_by_title(self, query: str, limit: int = 20) -> list[DocumentModel]:
        return (
            self._session.query(DocumentModel)
            .filter(DocumentModel.title.ilike(f"%{query}%"))
            .order_by(desc(DocumentModel.created_at))
            .limit(limit)
            .all()
        )

    def get_recent(self, limit: int = 10) -> list[DocumentModel]:
        return (
            self._session.query(DocumentModel)
            .order_by(desc(DocumentModel.created_at))
            .limit(limit)
            .all()
        )

    def get_by_uploader(self, user_id: UUID) -> list[DocumentModel]:
        return (
            self._session.query(DocumentModel)
            .filter(DocumentModel.uploaded_by == user_id)
            .order_by(desc(DocumentModel.created_at))
            .all()
        )

    def update_embedding_status(
        self, doc_id: UUID, status: ProcessingStatus, is_indexed: bool = False
    ) -> None:
        doc = self.get_by_id(doc_id)
        doc.embedding_status = status
        doc.is_indexed = is_indexed
        self._session.flush()

    def get_stats(self) -> dict:
        """Return aggregate stats for the dashboard."""
        total = self._session.query(func.count(DocumentModel.id)).scalar() or 0
        indexed = (
            self._session.query(func.count(DocumentModel.id))
            .filter(DocumentModel.is_indexed == True)
            .scalar() or 0
        )
        total_size = (
            self._session.query(func.sum(DocumentModel.file_size))
            .scalar() or 0
        )
        by_category = (
            self._session.query(
                DocumentModel.category,
                func.count(DocumentModel.id).label("count"),
            )
            .group_by(DocumentModel.category)
            .all()
        )
        return {
            "total": total,
            "indexed": indexed,
            "pending": total - indexed,
            "total_size_bytes": total_size,
            "by_category": {row.category: row.count for row in by_category},
        }

    def add_document(
        self,
        title: str,
        file_path: str,
        file_type: str,
        file_size_bytes: int,
        uploader_id: Optional[UUID],
        category: str,
    ) -> DocumentModel:
        doc = DocumentModel(
            title=title,
            original_filename=title + "." + file_type if not title.endswith("." + file_type) else title,
            file_path=file_path,
            file_size=file_size_bytes,
            file_type=file_type,
            category=category,
            uploaded_by=uploader_id,
            embedding_status=ProcessingStatus.PENDING,
            is_indexed=False,
        )
        self.add(doc)
        # Also add to processing queue
        from database.models.audit_log_model import ProcessingQueueModel
        queue_item = ProcessingQueueModel(
            document_id=doc.id,
            status="queued",
            progress=0,
            current_step="Queued for processing"
        )
        self._session.add(queue_item)
        self._session.flush()
        return doc

    def delete_document(self, doc_id: UUID) -> None:
        self.delete_by_id(doc_id)
