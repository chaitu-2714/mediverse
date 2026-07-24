"""
Authentication Service on the backend.
"""
from __future__ import annotations

import logging
from sqlalchemy.orm import Session
from database.models.user_model import UserModel
from database.repositories.user_repository import UserRepository

logger = logging.getLogger("mediverse.backend.services.auth_service")


class AuthBackendService:
    """Backend business logic for authentication."""
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[UserModel]:
        return db.query(UserModel).filter(UserModel.email == email.lower().strip()).first()

    @staticmethod
    def get_user_by_supabase_uid(db: Session, supabase_uid: str) -> Optional[UserModel]:
        return db.query(UserModel).filter(UserModel.supabase_uid == supabase_uid).first()

