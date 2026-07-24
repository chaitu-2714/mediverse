"""
MediVerse AI — Generic Base Repository.
Implements common CRUD operations using the Repository Pattern.
"""
from __future__ import annotations

import logging
from typing import Generic, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from core.exceptions import RecordNotFoundError

T = TypeVar("T")
logger = logging.getLogger("mediverse.repository")


class BaseRepository(Generic[T]):
    """Generic CRUD repository for SQLAlchemy models."""

    def __init__(self, session: Session, model_class: Type[T]) -> None:
        self._session = session
        self._model_class = model_class

    def get_by_id(self, record_id: UUID) -> T:
        record = self._session.get(self._model_class, record_id)
        if record is None:
            raise RecordNotFoundError(self._model_class.__name__, str(record_id))
        return record

    def get_by_id_or_none(self, record_id: UUID) -> Optional[T]:
        return self._session.get(self._model_class, record_id)

    def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        return (
            self._session.query(self._model_class)
            .limit(limit)
            .offset(offset)
            .all()
        )

    def add(self, record: T) -> T:
        self._session.add(record)
        self._session.flush()
        logger.debug(f"Added {self._model_class.__name__} record")
        return record

    def update(self, record: T) -> T:
        self._session.merge(record)
        self._session.flush()
        return record

    def delete(self, record: T) -> None:
        self._session.delete(record)
        self._session.flush()

    def delete_by_id(self, record_id: UUID) -> None:
        record = self.get_by_id(record_id)
        self.delete(record)

    def count(self) -> int:
        return self._session.query(self._model_class).count()

    def exists(self, record_id: UUID) -> bool:
        return self._session.get(self._model_class, record_id) is not None
