"""
Supabase Authentication Client Module.
"""
from __future__ import annotations

import logging
from typing import Optional
from supabase import create_client, Client
from config.settings import get_settings

logger = logging.getLogger("mediverse.backend.supabase_auth")


class SupabaseAuthHelper:
    """Helper class to interact with Supabase Auth services."""

    def __init__(self) -> None:
        self._client: Optional[Client] = None
        self._cached_url = ""
        self._cached_service_key = ""

    def get_client(self) -> Optional[Client]:
        """Dynamically load fresh settings and build/rebuild the Supabase client if changed."""
        from config.settings import get_settings
        get_settings.cache_clear()
        settings = get_settings()
        
        url = settings.supabase_url or ""
        service_key = settings.supabase_service_key or ""
        
        if url != self._cached_url or service_key != self._cached_service_key:
            self._cached_url = url
            self._cached_service_key = service_key
            if url and service_key:
                try:
                    self._client = create_client(url, service_key)
                    logger.info("Supabase client dynamically re-initialized with fresh settings.")
                except Exception as e:
                    self._client = None
                    logger.error(f"Failed to initialize Supabase client: {e}")
            else:
                self._client = None
                logger.warning("Supabase credentials not fully configured. Running in mock mode.")
        return self._client

    def verify_config(self) -> dict:
        """
        Verify all parts of the Supabase configuration and database.
        Returns a dict of status checks with details for self-healing.
        """
        from config.settings import get_settings
        get_settings.cache_clear()
        settings = get_settings()
        
        url = settings.supabase_url or ""
        anon_key = settings.supabase_anon_key or ""
        service_key = settings.supabase_service_key or ""
        
        checks = {}

        # 1. Supabase URL
        url_ok = bool(url and url.startswith("https://") and "supabase" in url)
        checks["SUPABASE_URL"] = {
            "status": url_ok,
            "current": url or "Not set",
            "expected": "https://<project-reference>.supabase.co",
            "problem": "Invalid or missing Supabase Project URL" if not url_ok else None,
            "reason": "The Supabase URL must be a valid HTTPS URL pointing to your Supabase project." if not url_ok else None,
            "fix": "Copy your Project URL from the Supabase Dashboard (Project Settings > API)." if not url_ok else None
        }

        # 2. Publishable Key (Anon Key)
        anon_ok = bool(anon_key and len(anon_key) > 50)
        checks["SUPABASE_ANON_KEY"] = {
            "status": anon_ok,
            "current": anon_key[:10] + "..." if anon_ok else "Not set",
            "expected": "Valid Supabase Anon/Public JWT key",
            "problem": "Invalid or missing Supabase Anon Key" if not anon_ok else None,
            "reason": "The Anon Key is required for client-side queries and authentication." if not anon_ok else None,
            "fix": "Copy the 'anon' public key from the Supabase Dashboard (Project Settings > API)." if not anon_ok else None
        }

        # 3. Service Role Key
        service_ok = bool(service_key and len(service_key) > 50)
        checks["SUPABASE_SERVICE_ROLE_KEY"] = {
            "status": service_ok,
            "current": service_key[:10] + "..." if service_ok else "Not set",
            "expected": "Valid Supabase Service Role JWT key",
            "problem": "Invalid or missing Service Role Key" if not service_ok else None,
            "reason": "The Service Role Key has administrative privileges and is required by the FastAPI backend to bypass RLS and verify tokens." if not service_ok else None,
            "fix": "Copy the 'service_role' secret key from the Supabase Dashboard (Project Settings > API)." if not service_ok else None
        }

        # 4. JWT Configuration / Validation
        jwt_ok = False
        jwt_problem = "JWT configuration invalid"
        jwt_reason = "JWT Secret Key is not configured."
        jwt_fix = "Configure JWT_SECRET in your .env file."
        if settings.jwt_secret_key and settings.jwt_secret_key != "change-this-jwt-secret":
            if len(settings.jwt_secret_key) >= 32:
                jwt_ok = True
                jwt_problem = None
                jwt_reason = None
                jwt_fix = None
            else:
                jwt_reason = "JWT Secret Key must be at least 32 characters for security."
                jwt_fix = "Generate a secure 256-bit JWT secret (e.g., click 'Generate' in the Setup Wizard)."
        checks["JWT_CONFIG"] = {
            "status": jwt_ok,
            "current": settings.jwt_secret_key or "Not set",
            "expected": "Secure 32+ character string",
            "problem": jwt_problem if not jwt_ok else None,
            "reason": jwt_reason,
            "fix": jwt_fix
        }

        # 5. Database Connection
        db_ok = False
        db_problem = "PostgreSQL database connection failed"
        db_reason = "Unable to connect to the database using the configured DB settings."
        db_fix = "Verify that PostgreSQL is running, the host and port are correct, and the credentials match."
        try:
            from database.connection import check_database_connection
            if check_database_connection():
                db_ok = True
                db_problem = None
                db_reason = None
                db_fix = None
        except Exception as e:
            db_reason = f"Database connection error: {str(e)}"
        
        checks["DB_CONNECTION"] = {
            "status": db_ok,
            "current": f"host={settings.db_host}, port={settings.db_port}, user={settings.db_user}",
            "expected": "Successful connection to PostgreSQL database",
            "problem": db_problem if not db_ok else None,
            "reason": db_reason,
            "fix": db_fix
        }

        # 6. Google OAuth Configuration
        google_ok = bool(settings.google_client_id and settings.google_client_secret)
        checks["GOOGLE_OAUTH"] = {
            "status": google_ok,
            "current": f"Client ID={settings.google_client_id[:10]}..." if settings.google_client_id else "Not set",
            "expected": "Configured Google Client ID & Secret",
            "problem": "Google OAuth is not configured" if not google_ok else None,
            "reason": "Google login requires an active OAuth 2.0 Client credentials set." if not google_ok else None,
            "fix": "Create a Google OAuth Client (Web application) in the Google Cloud Console, and configure the ID and Secret." if not google_ok else None
        }

        return checks

    def signup_user(self, email: str, password: str) -> dict:
        """Sign up a new user with Email + Password."""
        client = self.get_client()
        if not client:
            return {"user": {"email": email, "id": "mock-supabase-id-12345"}}
            
        try:
            response = client.auth.sign_up({
                "email": email,
                "password": password
            })
            if not response.user:
                raise ValueError("Signup failed on Supabase.")
            return response.model_dump()
        except Exception as e:
            logger.error(f"Supabase sign_up error: {e}")
            raise ValueError(f"Supabase Authentication error: {str(e)}")

    def login_user(self, email: str, password: str) -> dict:
        """Authenticate user with Email + Password."""
        client = self.get_client()
        if not client:
            return {
                "session": {
                    "access_token": "mock-access-token",
                    "refresh_token": "mock-refresh-token",
                    "expires_in": 3600
                },
                "user": {"email": email, "id": "mock-supabase-id-12345"}
            }
            
        try:
            response = client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return response.model_dump()
        except Exception as e:
            logger.error(f"Supabase sign_in error: {e}")
            raise ValueError(f"Supabase Authentication error: {str(e)}")

    def verify_token(self, token: str) -> dict:
        """Verify the integrity of a Supabase-issued access token (JWT)."""
        client = self.get_client()
        if not client:
            return {"email": "developer@mediverse.ai", "id": "d3b07384-d113-4e4e-9c29-0d1b918fcf10"}
            
        try:
            user_response = client.auth.get_user(token)
            if not user_response.user:
                raise ValueError("Invalid JWT session token.")
            return user_response.user.model_dump()
        except Exception as e:
            logger.error(f"Supabase JWT verification failed: {e}")
            raise ValueError("Authentication token is invalid or has expired.")

    def trigger_password_reset(self, email: str, redirect_url: str = "") -> bool:
        """Send password reset email to a user."""
        client = self.get_client()
        if not client:
            return True
            
        try:
            options = {}
            if redirect_url:
                options["redirect_to"] = redirect_url
            client.auth.reset_password_for_email(email, options)
            return True
        except Exception as e:
            logger.error(f"Supabase reset password failed: {e}")
            raise ValueError(f"Password reset dispatch failed: {str(e)}")

    def refresh_user_session(self, refresh_token: str) -> dict:
        """Refresh user session using a refresh token."""
        client = self.get_client()
        if not client:
            return {
                "session": {
                    "access_token": "mock-access-token-refreshed",
                    "refresh_token": "mock-refresh-token-refreshed",
                    "expires_in": 3600
                },
                "user": {"email": "developer@mediverse.ai", "id": "d3b07384-d113-4e4e-9c29-0d1b918fcf10"}
            }
        try:
            response = client.auth.refresh_session(refresh_token)
            return response.model_dump()
        except Exception as e:
            logger.error(f"Supabase refresh session failed: {e}")
            raise ValueError(f"Refresh token invalid or expired: {str(e)}")

