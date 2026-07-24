"""MediVerse AI — User Repository."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database.models.user_model import UserModel
from database.repositories.base_repository import BaseRepository

logger = logging.getLogger("mediverse.repository.user")


class UserRepository(BaseRepository[UserModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, UserModel)

    def get_by_email(self, email: str) -> Optional[UserModel]:
        return (
            self._session.query(UserModel)
            .filter(UserModel.email == email.lower().strip())
            .first()
        )

    def get_by_username(self, username: str) -> Optional[UserModel]:
        return (
            self._session.query(UserModel)
            .filter(UserModel.username == username.strip())
            .first()
        )

    def get_by_supabase_uid(self, uid: str) -> Optional[UserModel]:
        return (
            self._session.query(UserModel)
            .filter(UserModel.supabase_uid == uid)
            .first()
        )

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def username_exists(self, username: str) -> bool:
        return self.get_by_username(username) is not None

    def get_active_users(self) -> list[UserModel]:
        return self._session.query(UserModel).filter(UserModel.is_active == True).all()

    def get_by_role(self, role: str) -> list[UserModel]:
        return self._session.query(UserModel).filter(UserModel.role == role).all()

    def update_last_login(self, user_id: UUID) -> None:
        from datetime import datetime
        user = self.get_by_id(user_id)
        user.last_login = datetime.utcnow()
        self._session.flush()
