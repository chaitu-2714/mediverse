"""MediVerse AI — JWT Token Service."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

import jwt

from config.settings import get_settings
from core.exceptions import TokenExpiredError, TokenInvalidError

logger = logging.getLogger("mediverse.auth.jwt")


class JWTService:
    """
    Handles JWT token creation, validation, and decoding.
    Tokens carry user identity and role claims.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    def create_token(
        self,
        user_id: UUID,
        email: str,
        role: str,
        extra_claims: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create a signed JWT access token."""
        now = datetime.now(timezone.utc)
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "iat": now,
            "exp": now + timedelta(hours=self._settings.jwt_expiry_hours),
            "iss": "mediverse-ai",
            "type": "access",
        }
        if extra_claims:
            payload.update(extra_claims)

        token = jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )
        logger.debug(f"JWT created for user_id={user_id}")
        return token

    def decode_token(self, token: str) -> dict[str, Any]:
        """
        Decode and validate a JWT. Raises TokenExpiredError or TokenInvalidError
        on failure.
        """
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=[self._settings.jwt_algorithm],
                options={"verify_exp": True},
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT: {e}")
            raise TokenInvalidError()

    def get_user_id(self, token: str) -> UUID:
        payload = self.decode_token(token)
        return UUID(payload["sub"])

    def get_role(self, token: str) -> str:
        payload = self.decode_token(token)
        return payload["role"]

    def is_token_valid(self, token: str) -> bool:
        try:
            self.decode_token(token)
            return True
        except Exception:
            return False

    def create_password_reset_token(self, email: str) -> str:
        """Create a short-lived token for password reset."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": email,
            "iat": now,
            "exp": now + timedelta(hours=1),
            "iss": "mediverse-ai",
            "type": "password_reset",
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

    def decode_password_reset_token(self, token: str) -> str:
        """Decode and validate a password reset token. Returns email."""
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=[self._settings.jwt_algorithm],
            )
            if payload.get("type") != "password_reset":
                raise TokenInvalidError()
            return payload["sub"]
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError:
            raise TokenInvalidError()
