"""MediVerse AI — Password Service using bcrypt."""
from __future__ import annotations

import bcrypt


class PasswordService:
    """
    Handles password hashing and verification using bcrypt.
    Passwords are NEVER stored or logged in plain text.
    """
    _ROUNDS = 12

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Hash a plain-text password and return the bcrypt hash string."""
        if not plain_password or len(plain_password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        salt = bcrypt.gensalt(rounds=PasswordService._ROUNDS)
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Return True if the plain password matches the stored hash."""
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except Exception:
            return False

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """
        Validate password strength.
        Returns (is_valid, error_message).
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
        special_chars = "!@#$%^&*(),.?\":{}|<>"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"
        return True, ""
