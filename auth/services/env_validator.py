"""
MediVerse AI — Environment Configuration Validator & Writer.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

REQUIRED_VARS = [
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "JWT_SECRET"
]

# Values that indicate the user hasn't replaced the placeholder
_PLACEHOLDER_VALUES = {
    "change-this-in-production",
    "your-supabase-anon-key-here",
    "your-supabase-service-role-key-here",
    "use-a-securely-generated-sha256-string-here",
    "your-google-client-id",
    "your-google-client-secret"
}



def check_env_status() -> Dict[str, bool]:
    """
    Check the configuration status of each required environment variable.
    Returns a dict mapping the variable name to its configuration status (True = configured, False = missing).
    """
    # Force reloading environment from .env file (if it was created/updated)
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    status = {}
    for var in REQUIRED_VARS:
        val = os.environ.get(var) or ""
        val = val.strip()
        
        # Validation rules
        if not val:
            status[var] = False
        elif val in _PLACEHOLDER_VALUES or "your-supabase" in val:
            status[var] = False
        else:
            status[var] = True
            
    return status


def get_missing_vars() -> List[str]:
    """Return a list of all missing required environment variables."""
    status = check_env_status()
    return [var for var, configured in status.items() if not configured]


def get_oauth_diagnostic() -> Optional[str]:
    """
    Pre-flight check for Supabase configuration.
    Returns None if everything looks good, or a human-readable diagnostic string
    describing what needs to be fixed.
    """
    from dotenv import load_dotenv
    load_dotenv(override=True)

    problems: List[str] = []

    supabase_url = (os.environ.get("SUPABASE_URL") or "").strip()
    supabase_key = (os.environ.get("SUPABASE_ANON_KEY") or "").strip()

    if not supabase_url or "your-supabase" in supabase_url:
        problems.append("SUPABASE_URL is not set in .env")
    if not supabase_key or "your-supabase" in supabase_key:
        problems.append("SUPABASE_ANON_KEY is not set in .env")

    if problems:
        header = "SSO / Supabase pre-flight check FAILED:"
        detail = "\n".join(f"  • {p}" for p in problems)
        return f"{header}\n{detail}"

    return None


def save_env_config(updates: Dict[str, str]) -> None:
    """
    Write / update variables in the .env file.
    Preserves other unrelated environment configuration values.
    """
    env_path = Path(".env")
    existing = {}
    
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    parts = line.strip().split("=", 1)
                    existing[parts[0].strip()] = parts[1].strip()
                    
    # Merge updates
    for k, v in updates.items():
        existing[k] = v
        # Also update os.environ immediately so it's loaded in the current run
        os.environ[k] = v
        
    # Write back
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("# ── MediVerse AI Environment Configuration ──\n\n")
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
            
    # Force reload settings cache
    try:
        from config.settings import get_settings
        get_settings.cache_clear()
    except Exception:
        pass
