"""MediVerse AI — Role-Based Access Control Service."""
from __future__ import annotations

import logging
from functools import wraps
from typing import Callable

from config.constants import ROLE_PERMISSIONS
from core.exceptions import PermissionDeniedError
from core.models.user import User

logger = logging.getLogger("mediverse.auth.rbac")


class RBACService:
    """
    Role-Based Access Control service.
    Enforces permission checks for all protected operations.
    """

    @staticmethod
    def check_permission(user: User, action: str) -> bool:
        """Return True if the user has the given permission."""
        permissions = ROLE_PERMISSIONS.get(user.role, [])
        return action in permissions

    @staticmethod
    def require_permission(user: User, action: str) -> None:
        """
        Assert the user has the given permission.
        Raises PermissionDeniedError if not.
        """
        if not RBACService.check_permission(user, action):
            logger.warning(
                f"Permission denied: user={user.email} role={user.role} action={action}"
            )
            raise PermissionDeniedError(action=action, role=user.role)

    @staticmethod
    def get_user_permissions(user: User) -> list[str]:
        """Return all permissions for a user's role."""
        return ROLE_PERMISSIONS.get(user.role, [])

    @staticmethod
    def can_upload(user: User) -> bool:
        return RBACService.check_permission(user, "upload_document")

    @staticmethod
    def can_delete(user: User) -> bool:
        return RBACService.check_permission(user, "delete_document")

    @staticmethod
    def can_search(user: User) -> bool:
        return RBACService.check_permission(user, "search")

    @staticmethod
    def can_use_ai(user: User) -> bool:
        return RBACService.check_permission(user, "ai_assistant")

    @staticmethod
    def can_manage_users(user: User) -> bool:
        return RBACService.check_permission(user, "manage_users")

    @staticmethod
    def can_view_analytics(user: User) -> bool:
        return RBACService.check_permission(user, "view_analytics")

    @staticmethod
    def can_export(user: User) -> bool:
        return RBACService.check_permission(user, "export_reports")
