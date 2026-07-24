"""
MediVerse AI — Encrypted Session Persistence Manager.
Secures local desktop operator session tokens using dynamic machine-hash derived Fernet encryption keys.
"""
from __future__ import annotations

import base64
import getpass
import hashlib
import json
import logging
import os
import socket
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet

logger = logging.getLogger("mediverse.auth.session")


class SessionManager:
    """
    Encrypts and persists the local operator session JWT.
    Prevents cleartext token storage on client disk.
    """

    def __init__(self) -> None:
        # Determine the App Data Directory
        # App Data Directory: C:\\Users\\chait\\.gemini\\antigravity-ide
        # We can store the session dat in user home folder or app folder
        self.session_dir = Path(os.path.expanduser("~")) / ".mediverse"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_path = self.session_dir / ".session.dat"
        
        # Derive machine key
        self.key = self._derive_key()
        self.fernet = Fernet(self.key)

    def _derive_key(self) -> bytes:
        """Derive a URL-safe 32-byte key dynamically from system properties."""
        try:
            username = getpass.getuser()
            hostname = socket.gethostname()
            # Combine username & hostname to create a consistent, machine-locked seed
            seed = f"{username}::{hostname}::mediverse_secure_session_token_key"
            
            hasher = hashlib.sha256(seed.encode("utf-8"))
            return base64.urlsafe_b64encode(hasher.digest())
        except Exception as e:
            logger.error(f"Failed to derive machine key: {e}")
            # Fallback to a static derived seed if system functions fail
            hasher = hashlib.sha256(b"mediverse_default_session_salt")
            return base64.urlsafe_b64encode(hasher.digest())

    def save_session(self, token: str, refresh_token: str, user_id: str, email: str) -> bool:
        """Encrypt and save the session details locally."""
        try:
            session_data = {
                "token": token,
                "refresh_token": refresh_token,
                "user_id": user_id,
                "email": email
            }
            raw_json = json.dumps(session_data).encode("utf-8")
            encrypted = self.fernet.encrypt(raw_json)
            
            with open(self.session_path, "wb") as f:
                f.write(encrypted)
                
            logger.info("Session encrypted and saved locally.")
            return True
        except Exception as e:
            logger.error(f"Failed to save local session: {e}")
            return False

    def load_session(self) -> Optional[Dict[str, Any]]:
        """Load and decrypt the local session details if present."""
        if not self.session_path.exists():
            return None
            
        try:
            with open(self.session_path, "rb") as f:
                encrypted_data = f.read()
                
            decrypted = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted.decode("utf-8"))
        except Exception as e:
            logger.warning(f"Failed to load or decrypt local session: {e}. Session may be corrupt or expired.")
            self.clear_session()
            return None

    def clear_session(self) -> None:
        """Delete local session file."""
        try:
            if self.session_path.exists():
                self.session_path.unlink()
                logger.info("Local session cleared.")
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
