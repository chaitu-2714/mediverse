"""MediVerse AI — Annotation Repository."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from database.models.audit_log_model import AnnotationModel
from database.repositories.base_repository import BaseRepository


class AnnotationRepository(BaseRepository[AnnotationModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AnnotationModel)

    def get_by_document(self, document_id: UUID) -> list[AnnotationModel]:
        """Fetch all annotations/highlights for a specific document."""
        return (
            self._session.query(AnnotationModel)
            .filter(AnnotationModel.document_id == document_id)
            .order_by(AnnotationModel.page_number, AnnotationModel.created_at)
            .all()
        )

    def get_by_document_and_page(self, document_id: UUID, page_number: int) -> list[AnnotationModel]:
        """Fetch annotations/highlights for a specific page of a document."""
        return (
            self._session.query(AnnotationModel)
            .filter(
                AnnotationModel.document_id == document_id,
                AnnotationModel.page_number == page_number
            )
            .order_by(AnnotationModel.created_at)
            .all()
        )

    def add_annotation(
        self,
        user_id: UUID,
        document_id: UUID,
        page_number: int,
        text_content: Optional[str] = None,
        note: Optional[str] = None
    ) -> AnnotationModel:
        """Create and persist a new annotation or highlight."""
        annotation = AnnotationModel(
            user_id=user_id,
            document_id=document_id,
            page_number=page_number,
            text_content=text_content,
            note=note
        )
        self.add(annotation)
        self._session.flush()
        return annotation
