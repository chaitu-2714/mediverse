"""
MediVerse AI — Authentication Service.
Communicates with the FastAPI backend auth server to handle registration, login,
SSO handshakes, onboarding, and session refreshes.
"""
from __future__ import annotations

import logging
import requests
from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from datetime import datetime

from config.settings import get_settings
from auth.services.session_manager import SessionManager
from core.exceptions import (
    InvalidCredentialsError, UserAlreadyExistsError,
    UserNotFoundError, AccountDeactivatedError,
    PermissionDeniedError,
)
from core.models.user import User
from config.constants import UserRole

logger = logging.getLogger("mediverse.auth.service")


@dataclass
class LoginResult:
    user: User
    token: str
    is_new_session: bool = True


@dataclass
class RegisterResult:
    user: User
    token: str


class AuthService:
    """
    Central authentication client service.
    Orchestrates login, registration, and session lifecycle using the FastAPI backend.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.backend_url = "http://127.0.0.1:8000"
        self._session = SessionManager()
    def register(
        self,
        email: str,
        username: str,
        password: str,
        full_name: str,
        role: str = UserRole.MEDICAL_STUDENT,
    ) -> RegisterResult:
        """Register a new user via FastAPI auth backend."""
        url = f"{self.backend_url}/auth/register"
        payload = {
            "email": email,
            "username": username,
            "password": password,
            "full_name": full_name,
            "role": role
        }
        try:
            res = requests.post(url, json=payload, timeout=12)
            if res.status_code == 400:
                detail = res.json().get("detail", "")
                if "already exists" in detail:
                    raise UserAlreadyExistsError(email)
                raise ValueError(detail)
            elif res.status_code != 200:
                raise ValueError(res.json().get("detail", "Registration failed."))
                
            data = res.json()
            user = self._dict_to_domain(data["user"])
            token = data["token"]
            
            # Save refresh token in session storage
            self._session.save_session(token, data["refresh_token"], str(user.id), user.email)
            return RegisterResult(user=user, token=token)
        except requests.RequestException as e:
            logger.error(f"Registration network failure: {e}")
            raise ConnectionError("Authentication backend server is unreachable.")

    def login(self, email: str, password: str) -> LoginResult:
        """Authenticate a user via FastAPI auth backend, returning access token & session."""
        url = f"{self.backend_url}/auth/login"
        payload = {
            "email": email,
            "password": password
        }
        try:
            res = requests.post(url, json=payload, timeout=12)
            if res.status_code == 401:
                raise InvalidCredentialsError()
            elif res.status_code == 403:
                raise AccountDeactivatedError()
            elif res.status_code != 200:
                raise ValueError(res.json().get("detail", "Login failed."))
                
            data = res.json()
            user = self._dict_to_domain(data["user"])
            token = data["token"]
            
            # Save refresh token
            self._session.save_session(token, data["refresh_token"], str(user.id), user.email)
            return LoginResult(user=user, token=token)
        except requests.RequestException as e:
            logger.error(f"Login network failure: {e}")
            raise ConnectionError("Authentication backend server is unreachable.")

    def login_sso(
        self,
        provider: str,
        uid: str,
        email: str,
        full_name: str,
        avatar_url: str = "",
        firebase_id_token: str = ""
    ) -> LoginResult:
        """Link dynamic OAuth SSO payload to local backend session."""
        url = f"{self.backend_url}/auth/sso"
        payload = {
            "provider": provider,
            "uid": uid,
            "email": email,
            "full_name": full_name,
            "avatar_url": avatar_url or None,
            "firebase_id_token": firebase_id_token or None
        }
        try:
            res = requests.post(url, json=payload, timeout=12)
            if res.status_code != 200:
                raise ValueError(res.json().get("detail", f"{provider} validation rejected by backend."))
                
            data = res.json()
            user = self._dict_to_domain(data["user"])
            token = data["token"]
            
            self._session.save_session(token, data["refresh_token"], str(user.id), user.email)
            return LoginResult(user=user, token=token)
        except requests.RequestException as e:
            logger.error(f"SSO exchange network failure: {e}")
            raise ConnectionError("Authentication backend server is unreachable.")

    def get_user_from_token(self, token: str) -> User:
        """Fetch active user details using access token."""
        url = f"{self.backend_url}/auth/me"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                raise InvalidCredentialsError("Session token has expired or is invalid.")
            return self._dict_to_domain(res.json())
        except requests.RequestException as e:
            logger.error(f"Get User from token network failure: {e}")
            raise ConnectionError("Authentication backend server is unreachable.")

    def complete_onboarding(self, user_id: UUID, role: str) -> User:
        """Complete system operator onboarding selection."""
        # Retrieve current access token from session manager
        session_info = self._session.load_session()
        if not session_info or not session_info.get("token"):
            raise PermissionDeniedError("No active session found to complete onboarding.")
            
        url = f"{self.backend_url}/auth/onboarding"
        payload = {"role": role}
        headers = {"Authorization": f"Bearer {session_info['token']}"}
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            if res.status_code != 200:
                raise ValueError(res.json().get("detail", "Failed to confirm role onboarding."))
            return self._dict_to_domain(res.json())
        except requests.RequestException as e:
            logger.error(f"Onboarding network failure: {e}")
            raise ConnectionError("Authentication backend server is unreachable.")

    def refresh_session_token(self) -> Optional[str]:
        """Exchanges long-lived refresh token for a new access token on backend."""
        session_info = self._session.load_session()
        if not session_info or not session_info.get("refresh_token"):
            return None
            
        url = f"{self.backend_url}/auth/refresh"
        payload = {"refresh_token": session_info["refresh_token"]}
        try:
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code != 200:
                logger.warning("Refresh token rejected or expired on backend. Clearing session.")
                self.clear_session()
                return None
                
            data = res.json()
            new_token = data["token"]
            self._session.save_session(
                new_token, data["refresh_token"], data["user"]["id"], data["user"]["email"]
            )
            return new_token
        except Exception as e:
            logger.error(f"Auto token refresh failed: {e}")
            return None

    def send_password_reset(self, email: str) -> bool:
        """Triggers password reset flow in backend."""
        url = f"{self.backend_url}/auth/forgot-password"
        try:
            res = requests.post(url, json={"email": email}, timeout=10)
            if res.status_code != 200:
                raise ValueError(res.json().get("detail", "Reset dispatch failed."))
            return True
        except requests.RequestException as e:
            logger.error(f"Password reset network failure: {e}")
            raise ConnectionError("Authentication backend server is unreachable.")

    def change_password(self, user_id: UUID, old_password: str, new_password: str) -> None:
        """Mock/Wrapper for change password in FastAPI."""
        pass

    def get_user_by_id(self, user_id: UUID) -> User:
        """Resolves user details by ID."""
        session_info = self._session.load_session()
        if session_info and session_info.get("token"):
            try:
                return self.get_user_from_token(session_info["token"])
            except Exception:
                pass
        raise UserNotFoundError(str(user_id))

    def verify_backend_config(self) -> dict:
        """Call FastAPI auth verify endpoint to retrieve configuration checks."""
        url = f"{self.backend_url}/auth/verify"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                return res.json()
            else:
                return {
                    "error": {
                        "problem": "FastAPI Verify Endpoint Failed",
                        "reason": f"Backend returned status code {res.status_code}",
                        "fix": "Check backend logs for errors.",
                        "current": str(res.status_code),
                        "expected": "200 OK"
                    }
                }
        except requests.RequestException as e:
            return {
                "error": {
                    "problem": "FastAPI Server Unreachable",
                    "reason": "The PySide6 application cannot reach the backend server on port 8000.",
                    "fix": "Ensure the FastAPI server is running (started in main.py boot sequence).",
                    "current": "Offline/Unreachable",
                    "expected": "Online"
                }
            }

    # ── Session Manager wrappers ──────────────────────────────────
    def save_session(self, token: str, refresh_token: str = "", user_id: str = "", email: str = "") -> bool:
        if refresh_token and not email:
            # Handle 3 arguments passed: save_session(token, user_id, email)
            email = user_id
            user_id = refresh_token
            refresh_token = "dummy-refresh-token"
        return self._session.save_session(token, refresh_token, user_id, email)


    def load_session(self) -> Optional[dict]:
        """Bypassed Authentication: Returns mock developer session dict."""
        return {
            "token": "dummy-jwt-developer-token",
            "refresh_token": "dummy-refresh-token",
            "user_id": "d3b07384-d113-4e4e-9c29-0d1b918fcf10",
            "email": "developer@mediverse.ai"
        }


    def clear_session(self) -> None:
        """Call logout on backend, then wipe local session."""
        session_info = self._session.load_session()
        if session_info and session_info.get("token") and session_info.get("refresh_token"):
            url = f"{self.backend_url}/auth/logout"
            headers = {"Authorization": f"Bearer {session_info['token']}"}
            payload = {"refresh_token": session_info["refresh_token"]}
            try:
                requests.post(url, json=payload, headers=headers, timeout=5)
            except Exception:
                pass
        self._session.clear_session()

    @staticmethod
    def _dict_to_domain(data: dict) -> User:
        """Map dict to User Domain object."""
        return User(
            id=UUID(data["id"]),
            email=data["email"],
            username=data["username"],
            full_name=data.get("full_name") or "",
            role=UserRole(data["role"]),
            is_active=data.get("is_active", True),
            is_verified=data.get("is_verified", False),
            avatar_url=data.get("avatar_url"),
            auth_provider=data.get("auth_provider"),
            is_onboarded=data.get("is_onboarded", False),
            login_count=data.get("login_count", 0),
            created_at=None,
            last_login=None
        )
