"""
MediVerse AI — Domain Models (Core Entities).
Pure Python dataclasses — no ORM or UI dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from config.constants import UserRole


@dataclass
class User:
    """Domain entity representing an authenticated user."""
    id: UUID
    email: str
    username: str
    full_name: str
    role: UserRole
    is_active: bool = True
    is_verified: bool = False
    avatar_url: Optional[str] = None
    auth_provider: Optional[str] = None
    is_onboarded: bool = False
    login_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    @property
    def display_name(self) -> str:
        return self.full_name or self.username

    @property
    def role_display(self) -> str:
        from config.constants import ROLE_DISPLAY_NAMES
        return ROLE_DISPLAY_NAMES.get(self.role, self.role)

    def has_permission(self, action: str) -> bool:
        from config.constants import ROLE_PERMISSIONS
        return action in ROLE_PERMISSIONS.get(self.role, [])

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email}, role={self.role})"
