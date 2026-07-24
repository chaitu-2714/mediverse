"""
MediVerse AI — Application Settings
Uses pydantic-settings for environment-based configuration with .env support.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Central application configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = Field(default="MediVerse AI")
    app_version: str = Field(default="1.0.0")
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)
    secret_key: str = Field(default="change-this-in-production")

    # ── PostgreSQL ────────────────────────────────────────────
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str = Field(default="mediverse_db")
    db_user: str = Field(default="postgres")
    db_password: str = Field(default="")
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)

    # ── JWT ───────────────────────────────────────────────────
    jwt_secret_key: str = Field(default="change-this-jwt-secret", validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiry_hours: int = Field(default=24)

    # ── ChromaDB ─────────────────────────────────────────────
    chroma_host: str = Field(default="localhost")
    chroma_port: int = Field(default=8000)
    chroma_persist_dir: str = Field(default="./data/chromadb")

    # ── Ollama / LLM ──────────────────────────────────────────
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.2")
    ollama_timeout: int = Field(default=120)
    ollama_enabled: bool = Field(default=True)

    # ── Embeddings ────────────────────────────────────────────
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_batch_size: int = Field(default=32)
    embedding_device: str = Field(default="cpu")

    # ── Document Processing ───────────────────────────────────
    max_file_size_mb: int = Field(default=500)
    chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=64)
    max_chunks_per_doc: int = Field(default=2000)
    ocr_confidence_threshold: float = Field(default=0.5)
    min_text_length_for_ocr: int = Field(default=50)

    # ── Search ────────────────────────────────────────────────
    search_top_k: int = Field(default=10)
    search_min_score: float = Field(default=0.3)
    rag_top_k: int = Field(default=5)

    # ── Storage ───────────────────────────────────────────────
    upload_dir: str = Field(default="./knowledge_base/uploads")
    temp_dir: str = Field(default="./data/temp")
    log_dir: str = Field(default="./data/logs")

    # ── Logging ───────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="./data/logs/mediverse.log")
    audit_log_file: str = Field(default="./data/logs/audit.log")

    # ── Supabase & OAuth ──────────────────────────────────────────────
    supabase_url: Optional[str] = Field(default=None, validation_alias="SUPABASE_URL")
    supabase_anon_key: Optional[str] = Field(default=None, validation_alias="SUPABASE_ANON_KEY")
    supabase_service_key: Optional[str] = Field(default=None, validation_alias="SUPABASE_SERVICE_ROLE_KEY")
    google_client_id: Optional[str] = Field(default=None, validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(default=None, validation_alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(default="http://127.0.0.1:8000/auth/google/callback", validation_alias="GOOGLE_REDIRECT_URI")
    apple_client_id: Optional[str] = Field(default=None, validation_alias="APPLE_CLIENT_ID")
    # ── Computed Properties ───────────────────────────────────
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_async(self) -> str:
        return (
            f"postgresql+asyncpg://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        dirs = [
            self.upload_dir,
            self.temp_dir,
            self.log_dir,
            self.chroma_persist_dir,
            "./knowledge_base/uploads/who_guidelines",
            "./knowledge_base/uploads/cdc_guidelines",
            "./knowledge_base/uploads/icmr_guidelines",
            "./knowledge_base/uploads/research_papers",
            "./knowledge_base/uploads/medical_books",
            "./knowledge_base/uploads/hospital_sops",
            "./knowledge_base/uploads/medical_reports",
            "./knowledge_base/uploads/x_rays",
            "./knowledge_base/uploads/scan_reports",
        ]
        for d in dirs:
            Path(d).mkdir(parents=True, exist_ok=True)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return v.upper()


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return singleton settings instance."""
    settings = AppSettings()
    settings.ensure_directories()
    return settings
