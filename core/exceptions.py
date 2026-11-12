"""
MediVerse AI — Custom Exception Hierarchy.
All domain exceptions live here for consistent error handling.
"""
from __future__ import annotations


class MediVerseError(Exception):
    """Base exception for all MediVerse AI errors."""
    def __init__(self, message: str, code: str = "MEDIVERSE_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ── Authentication Exceptions ─────────────────────────────────
class AuthenticationError(MediVerseError):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, "AUTH_ERROR")


class InvalidCredentialsError(AuthenticationError):
    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class UserNotFoundError(AuthenticationError):
    def __init__(self, identifier: str = "") -> None:
        super().__init__(f"User not found: {identifier}")


class UserAlreadyExistsError(AuthenticationError):
    def __init__(self, email: str) -> None:
        super().__init__(f"User with email '{email}' already exists")


class AccountDeactivatedError(AuthenticationError):
    def __init__(self) -> None:
        super().__init__("Account has been deactivated")


class TokenExpiredError(AuthenticationError):
    def __init__(self) -> None:
        super().__init__("Session token has expired. Please log in again.")


class TokenInvalidError(AuthenticationError):
    def __init__(self) -> None:
        super().__init__("Invalid session token")


class PermissionDeniedError(MediVerseError):
    def __init__(self, action: str = "", role: str = "") -> None:
        msg = f"Permission denied: action='{action}', role='{role}'"
        super().__init__(msg, "PERMISSION_DENIED")


# ── Database Exceptions ───────────────────────────────────────
class DatabaseError(MediVerseError):
    def __init__(self, message: str, original: Exception | None = None) -> None:
        super().__init__(message, "DB_ERROR")
        self.original = original


class DatabaseConnectionError(DatabaseError):
    def __init__(self, host: str = "", port: int = 0) -> None:
        super().__init__(f"Cannot connect to database at {host}:{port}")


class RecordNotFoundError(DatabaseError):
    def __init__(self, model: str, record_id: str) -> None:
        super().__init__(f"{model} with id='{record_id}' not found")


# ── Document Exceptions ───────────────────────────────────────
class DocumentError(MediVerseError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "DOC_ERROR")


class InvalidFileTypeError(DocumentError):
    def __init__(self, extension: str) -> None:
        super().__init__(f"File type '{extension}' is not supported")


class FileTooLargeError(DocumentError):
    def __init__(self, size_mb: float, limit_mb: int) -> None:
        super().__init__(f"File size {size_mb:.1f}MB exceeds limit of {limit_mb}MB")


class DocumentProcessingError(DocumentError):
    def __init__(self, step: str, reason: str) -> None:
        super().__init__(f"Processing failed at step '{step}': {reason}")


class OCRError(DocumentError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"OCR processing failed: {reason}")


# ── AI / Search Exceptions ────────────────────────────────────
class AIEngineError(MediVerseError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "AI_ERROR")


class EmbeddingError(AIEngineError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Embedding generation failed: {reason}")


class SearchError(AIEngineError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Semantic search failed: {reason}")


class LLMError(AIEngineError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"LLM query failed: {reason}")


class OllamaNotAvailableError(LLMError):
    def __init__(self) -> None:
        super().__init__(
            "Ollama service is not running. Start it with: ollama serve"
        )


class GeminiError(LLMError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Gemini LLM error: {reason}")


class GeminiAuthError(GeminiError):
    def __init__(self, message: str = "Gemini API key is invalid or not configured. Set GEMINI_API_KEY in .env") -> None:
        super().__init__(message)


class GeminiNetworkError(GeminiError):
    def __init__(self, message: str = "Network error connecting to Gemini API. Please check your internet connection.") -> None:
        super().__init__(message)


class GeminiRateLimitError(GeminiError):
    def __init__(self, message: str = "Gemini API rate limit exceeded. Please try again shortly.") -> None:
        super().__init__(message)


class OnlineSearchError(AIEngineError):
    def __init__(self, message: str = "Online medical search failed.") -> None:
        super().__init__(message)


class NoEvidenceFoundError(AIEngineError):
    def __init__(self, query: str) -> None:
        super().__init__(
            f"No supporting evidence found in the indexed knowledge repository "
            f"for query: '{query}'"
        )


# ── Vector DB Exceptions ──────────────────────────────────────
class VectorDBError(MediVerseError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "VECTOR_DB_ERROR")


class ChromaDBConnectionError(VectorDBError):
    def __init__(self) -> None:
        super().__init__("Cannot connect to ChromaDB. Is it running?")


# ── Configuration Exceptions ──────────────────────────────────
class ConfigurationError(MediVerseError):
    def __init__(self, key: str, reason: str) -> None:
        super().__init__(f"Configuration error for '{key}': {reason}", "CONFIG_ERROR")


# ── Storage Exceptions ────────────────────────────────────────
class StorageError(MediVerseError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "STORAGE_ERROR")
