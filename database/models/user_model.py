"""MediVerse AI — User ORM Model."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, func, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base
from config.constants import UserRole
from database.models.document_model import DocumentModel
from database.models.audit_log_model import BookmarkModel, AuditLogModel, SearchLogModel


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default=UserRole.MEDICAL_STUDENT
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supabase_uid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    auth_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_onboarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    documents: Mapped[list[DocumentModel]] = relationship("DocumentModel", back_populates="uploader")
    bookmarks: Mapped[list[BookmarkModel]] = relationship("BookmarkModel", back_populates="user")
    audit_logs: Mapped[list[AuditLogModel]] = relationship("AuditLogModel", back_populates="user")
    search_logs: Mapped[list[SearchLogModel]] = relationship("SearchLogModel", back_populates="user")

    def __repr__(self) -> str:
        return f"<User email={self.email} role={self.role}>"
