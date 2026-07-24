"""MediVerse AI — Chunk, Audit, and Search Repositories."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.models.chunk_model import DocumentChunkModel
from database.models.audit_log_model import AuditLogModel, SearchLogModel, ProcessingQueueModel
from database.repositories.base_repository import BaseRepository

logger = logging.getLogger("mediverse.repository")


class ChunkRepository(BaseRepository[DocumentChunkModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DocumentChunkModel)

    def get_by_document(self, document_id: UUID) -> list[DocumentChunkModel]:
        return (
            self._session.query(DocumentChunkModel)
            .filter(DocumentChunkModel.document_id == document_id)
            .order_by(DocumentChunkModel.chunk_index)
            .all()
        )

    def delete_by_document(self, document_id: UUID) -> int:
        deleted = (
            self._session.query(DocumentChunkModel)
            .filter(DocumentChunkModel.document_id == document_id)
            .delete()
        )
        self._session.flush()
        return deleted

    def get_by_chroma_id(self, chroma_id: str) -> Optional[DocumentChunkModel]:
        return (
            self._session.query(DocumentChunkModel)
            .filter(DocumentChunkModel.chroma_id == chroma_id)
            .first()
        )

    def bulk_add(self, chunks: list[DocumentChunkModel]) -> None:
        self._session.bulk_save_objects(chunks)
        self._session.flush()


class AuditRepository(BaseRepository[AuditLogModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditLogModel)

    def log_action(
        self,
        action: str,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLogModel:
        entry = AuditLogModel(
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
        )
        return self.add(entry)

    def get_by_user(self, user_id: UUID, limit: int = 50) -> list[AuditLogModel]:
        return (
            self._session.query(AuditLogModel)
            .filter(AuditLogModel.user_id == user_id)
            .order_by(desc(AuditLogModel.created_at))
            .limit(limit)
            .all()
        )

    def get_recent(self, limit: int = 20) -> list[AuditLogModel]:
        return (
            self._session.query(AuditLogModel)
            .order_by(desc(AuditLogModel.created_at))
            .limit(limit)
            .all()
        )


class SearchRepository(BaseRepository[SearchLogModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, SearchLogModel)

    def log_search(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        result_count: int = 0,
        response_time_ms: int = 0,
        top_document_id: Optional[UUID] = None,
    ) -> SearchLogModel:
        entry = SearchLogModel(
            query=query,
            user_id=user_id,
            result_count=result_count,
            response_time_ms=response_time_ms,
            top_document_id=top_document_id,
        )
        return self.add(entry)

    def get_recent_searches(self, user_id: UUID, limit: int = 10) -> list[SearchLogModel]:
        return (
            self._session.query(SearchLogModel)
            .filter(SearchLogModel.user_id == user_id)
            .order_by(desc(SearchLogModel.created_at))
            .limit(limit)
            .all()
        )

    def get_popular_queries(self, limit: int = 10) -> list[tuple[str, int]]:
        from sqlalchemy import func
        results = (
            self._session.query(
                SearchLogModel.query,
                func.count(SearchLogModel.id).label("count"),
            )
            .group_by(SearchLogModel.query)
            .order_by(desc("count"))
            .limit(limit)
            .all()
        )
        return [(r.query, r.count) for r in results]


class ProcessingQueueRepository(BaseRepository[ProcessingQueueModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ProcessingQueueModel)

    def get_by_document(self, document_id: UUID) -> Optional[ProcessingQueueModel]:
        return (
            self._session.query(ProcessingQueueModel)
            .filter(ProcessingQueueModel.document_id == document_id)
            .first()
        )

    def update_progress(
        self,
        queue_id: UUID,
        progress: int,
        current_step: str,
        status: str = "processing",
    ) -> None:
        record = self.get_by_id(queue_id)
        record.progress = progress
        record.current_step = current_step
        record.status = status
        self._session.flush()
