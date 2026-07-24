"""
Session Manager to handle user devices, session lists, and revocation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from database.models.refresh_token import RefreshTokenModel

class SessionManagerBackend:
    """Session management helpers for device lists and logouts."""

    @staticmethod
    def get_active_sessions(db: Session, user_id: uuid.UUID) -> list[RefreshTokenModel]:
        """Fetch all active refresh token sessions for a user."""
        return db.query(RefreshTokenModel).filter(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.is_revoked == False,
            RefreshTokenModel.expires_at > datetime.now(timezone.utc)
        ).all()

    @staticmethod
    def revoke_all_sessions(db: Session, user_id: uuid.UUID) -> None:
        """Revoke all sessions for a user (Logout from every device)."""
        sessions = db.query(RefreshTokenModel).filter(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.is_revoked == False
        ).all()
        for session in sessions:
            session.is_revoked = True
        db.commit()
