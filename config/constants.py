"""MediVerse AI — Application-wide constants."""
from __future__ import annotations

from enum import Enum


# ── User Roles ────────────────────────────────────────────────
class UserRole(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    RESEARCHER = "researcher"
    MEDICAL_STUDENT = "medical_student"


# ── Role Display Names ─────────────────────────────────────────
ROLE_DISPLAY_NAMES: dict[str, str] = {
    UserRole.ADMIN: "Administrator",
    UserRole.DOCTOR: "Doctor",
    UserRole.RESEARCHER: "Researcher",
    UserRole.MEDICAL_STUDENT: "Medical Student",
}

# ── Role Permissions ──────────────────────────────────────────
ROLE_PERMISSIONS: dict[str, list[str]] = {
    UserRole.ADMIN: [
        "upload_document", "delete_document", "rename_document",
        "search", "ai_assistant", "view_analytics",
        "manage_users", "view_audit_logs", "export_reports",
        "manage_categories", "re_index",
    ],
    UserRole.DOCTOR: [
        "upload_document", "delete_document", "rename_document",
        "search", "ai_assistant", "export_reports",
    ],
    UserRole.RESEARCHER: [
        "upload_document", "delete_document", "rename_document",
        "search", "ai_assistant", "export_reports", "view_analytics",
    ],
    UserRole.MEDICAL_STUDENT: [
        "search", "ai_assistant",
    ],
}


# ── Document Categories ────────────────────────────────────────
class DocumentCategory(str, Enum):
    WHO_GUIDELINES = "who_guidelines"
    CDC_GUIDELINES = "cdc_guidelines"
    ICMR_GUIDELINES = "icmr_guidelines"
    MEDICAL_BOOKS = "medical_books"
    RESEARCH_PAPERS = "research_papers"
    HOSPITAL_SOPS = "hospital_sops"
    MEDICAL_REPORTS = "medical_reports"
    X_RAYS = "x_rays"
    SCAN_REPORTS = "scan_reports"
    UNCATEGORIZED = "uncategorized"


CATEGORY_DISPLAY_NAMES: dict[str, str] = {
    DocumentCategory.WHO_GUIDELINES: "WHO Guidelines",
    DocumentCategory.CDC_GUIDELINES: "CDC Guidelines",
    DocumentCategory.ICMR_GUIDELINES: "ICMR Guidelines",
    DocumentCategory.MEDICAL_BOOKS: "Medical Books",
    DocumentCategory.RESEARCH_PAPERS: "Research Papers",
    DocumentCategory.HOSPITAL_SOPS: "Hospital SOPs",
    DocumentCategory.MEDICAL_REPORTS: "Medical Reports",
    DocumentCategory.X_RAYS: "X-Rays",
    DocumentCategory.SCAN_REPORTS: "Scan Reports",
    DocumentCategory.UNCATEGORIZED: "Uncategorized",
}

CATEGORY_ICONS: dict[str, str] = {
    DocumentCategory.WHO_GUIDELINES: "🌐",
    DocumentCategory.CDC_GUIDELINES: "🏥",
    DocumentCategory.ICMR_GUIDELINES: "🇮🇳",
    DocumentCategory.MEDICAL_BOOKS: "📚",
    DocumentCategory.RESEARCH_PAPERS: "🔬",
    DocumentCategory.HOSPITAL_SOPS: "📋",
    DocumentCategory.MEDICAL_REPORTS: "📄",
    DocumentCategory.X_RAYS: "🩻",
    DocumentCategory.SCAN_REPORTS: "🧠",
    DocumentCategory.UNCATEGORIZED: "📁",
}


# ── Document Processing Status ────────────────────────────────
class ProcessingStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Processing Steps ──────────────────────────────────────────
PROCESSING_STEPS = [
    "Validating file",
    "Extracting text",
    "Running OCR",
    "Extracting metadata",
    "Detecting language",
    "Recognizing medical entities",
    "Extracting keywords",
    "Chunking document",
    "Generating embeddings",
    "Storing metadata",
    "Storing vectors",
    "Finalizing index",
]

# ── Supported File Types ──────────────────────────────────────
SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
}
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# ── UI Constants ──────────────────────────────────────────────
APP_WINDOW_TITLE = "MediVerse AI"
SIDEBAR_WIDTH_EXPANDED = 240
SIDEBAR_WIDTH_COLLAPSED = 60
SPLASH_DURATION_MS = 3000
TOAST_DURATION_MS = 3500
ANIMATION_DURATION_MS = 250
SEARCH_DEBOUNCE_MS = 400

# ── ChromaDB ──────────────────────────────────────────────────
CHROMA_COLLECTION_NAME = "medical_documents"
CHROMA_DISTANCE_FUNCTION = "cosine"

# ── NLP / Medical Entity Labels ───────────────────────────────
MEDICAL_ENTITY_LABELS = [
    "DISEASE", "CHEMICAL", "DRUG", "GENE_OR_GENE_PRODUCT",
    "ORGANISM", "PROCEDURE", "ANATOMY", "SYMPTOM", "DOSAGE",
]

# ── AI Response Confidence Thresholds ────────────────────────
CONFIDENCE_HIGH = 0.80
CONFIDENCE_MEDIUM = 0.60
CONFIDENCE_LOW = 0.40

# ── Session Keys ──────────────────────────────────────────────
SESSION_TOKEN_KEY = "mediverse_session_token"
SESSION_USER_KEY = "mediverse_current_user"

# ── Audit Actions ─────────────────────────────────────────────
class AuditAction(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    UPLOAD_DOCUMENT = "upload_document"
    DELETE_DOCUMENT = "delete_document"
    SEARCH = "search"
    AI_QUERY = "ai_query"
    EXPORT = "export"
    PASSWORD_RESET = "password_reset"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
