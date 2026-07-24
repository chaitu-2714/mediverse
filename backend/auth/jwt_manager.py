"""
JWT Session Manager for generating and verifying application tokens.
"""
from __future__ import annotations

import jwt
import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from config.settings import get_settings

logger = logging.getLogger("mediverse.backend.jwt_manager")


def hash_refresh_token(token: str) -> str:
    """Hash the refresh token for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user_id: uuid.UUID, email: str, role: str) -> str:
    """Generate a signed access token for app authentication."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=60),
        "iss": "mediverse-ai",
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    logger.info(f"Local JWT created successfully for user: {email} (UID: {user_id})")
    return token
