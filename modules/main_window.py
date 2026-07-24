"""
MediVerse AI — Main Window.
Orchestrates the main layout, sidebar navigation, stacked views, and background system checks.
"""
from __future__ import annotations

import logging
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QFrame, QLabel, QLineEdit, QPushButton, QFileDialog
)

from core.models.user import User
from shared.components.base_window import BaseFramelessWindow
from shared.components.animated_sidebar import AnimatedSidebar
from shared.components.status_bar import StatusBar

from database.connection import get_db_session, check_database_connection
from vector_db.chroma_client import check_chroma_connection

# Views imports
from modules.dashboard.ui.dashboard_view import DashboardView
from modules.repository.ui.repository_view import RepositoryView
from modules.ai_assistant.ui.assistant_view import AssistantView
from modules.knowledge_graph.ui.graph_view import KnowledgeGraphView
from modules.profile.ui.profile_view import UserProfileView
from modules.admin_panel.ui.admin_view import AdminPanelView
from modules.imaging_analysis.ui.imaging_analysis_view import ClinicalAnalysisWorkspaceView
from modules.auth_settings.ui.auth_settings_view import AuthSettingsView
from config.constants import UserRole
from shared.components.notification_toast import NotificationToast

logger = logging.getLogger("mediverse.ui.main")


class MainWindow(BaseFramelessWindow):
    """Main Enterprise Application Shell."""
    
    logout_requested = Signal()

    def __init__(self, current_user: User) -> None:
        super().__init__(title="MediVerse AI Enterprise Workspace")
        self._user = current_user
        
        self.setMinimumSize(1280, 800)
        self._setup_ui()
        
        # Diagnostics update loop
        self._diagnostics_timer = QTimer(self)
        self._diagnostics_timer.timeout.connect(self._run_diagnostics)
        self._diagnostics_timer.start(10000) # Check status every 10s
        QTimer.singleShot(800, self._run_diagnostics) # Quick initial check

    def _setup_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Top Navigation Bar
        self.top_nav = QFrame()
        self.top_nav.setFixedHeight(60)
        self.top_nav.setStyleSheet("""
            QFrame {
                background: rgba(8, 12, 28, 0.95);
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        top_layout = QHBoxLayout(self.top_nav)
        top_layout.setContentsMargins(20, 0, 20, 0)
        top_layout.setSpacing(15)
        
        # MediVerse AI Logo
        logo_lbl = QLabel("⚕ MediVerse AI")
        logo_lbl.setStyleSheet("color: white; font-size: 16px; font-weight: 900; letter-spacing: 1px;")
        top_layout.addWidget(logo_lbl)
        
        # AI Status Badge
        status_badge = QLabel("● AI STATUS: ONLINE (Ollama Core)")
        status_badge.setStyleSheet("""
            color: #10b981;
            background: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 9.5px;
            font-weight: bold;
        """)
        top_layout.addWidget(status_badge)
        
        top_layout.addStretch()
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search reports, patient MRNs, anatomical terms...")
        self.search_input.setFixedWidth(300)
        self.search_input.setFixedHeight(32)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: white;
                padding-left: 10px;
                font-size: 11.5px;
            }
            QLineEdit:focus {
                border: 1px solid #06b6d4;
                background: rgba(255, 255, 255, 0.05);
            }
        """)
        top_layout.addWidget(self.search_input)
        
        # Notification Button
        btn_notif = QPushButton("🔔")
        btn_notif.setFixedSize(32, 32)
        btn_notif.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.06); }
        """)
        btn_notif.clicked.connect(lambda: NotificationToast.show_message(self, "No new clinical alerts.", "info"))
        top_layout.addWidget(btn_notif)
        
        # Theme Switch Button
        btn_theme = QPushButton("🌙")
        btn_theme.setFixedSize(32, 32)
        btn_theme.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.06); }
        """)
        btn_theme.clicked.connect(lambda: NotificationToast.show_message(self, "Dark theme locked for futuristic medical workspace.", "info"))
        top_layout.addWidget(btn_theme)
        
        # Upload Button
        btn_top_upload = QPushButton("📤 Upload Asset")
        btn_top_upload.setFixedHeight(32)
        btn_top_upload.setFixedWidth(130)
        btn_top_upload.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06b6d4, stop:1 #3b82f6);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0891b2, stop:1 #2563eb);
            }
        """)
        btn_top_upload.clicked.connect(self._trigger_top_upload)
        top_layout.addWidget(btn_top_upload)
        
        # User Profile Display (removed name)

        
        layout.addWidget(self.top_nav)

        # Main work area (Sidebar + Content)
        work_area = QWidget()
        work_layout = QHBoxLayout(work_area)
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(0)
        
        # 1. Sidebar
        self.sidebar = AnimatedSidebar()
        self.sidebar.logo_title.hide() # Hide default logo since it's on top nav
        self.sidebar.add_module("dashboard", "🏠", "Dashboard", is_active=True)
        self.sidebar.add_module("repository", "📂", "Repository")
        self.sidebar.add_module("upload_action", "📤", "Upload File")
        self.sidebar.add_module("imaging_analysis", "🧠", "AI Analysis")
        self.sidebar.add_module("assistant", "💬", "AI Assistant")
        self.sidebar.add_module("graph", "🧬", "Knowledge Graph")
        self.sidebar.add_module("anatomy_explorer", "🧍", "Anatomy Explorer")
        self.sidebar.add_module("history", "📜", "History")
        
        # Dynamic Admin Panel clearance access
        if self._user.role == UserRole.ADMIN:
            self.sidebar.add_module("admin", "🛡️", "Admin Panel")
            
        self.sidebar.add_spacer()

        
        self.sidebar.module_selected.connect(self._on_module_selected)
        work_layout.addWidget(self.sidebar)
        
        # 2. Content Stack
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: transparent;")
        
        # Initialize Workspaces
        self.dashboard_view = DashboardView(self._user)
        self.repository_view = RepositoryView(self._user)
        self.repository_view.document_indexed.connect(self.dashboard_view.refresh_stats)
        self.assistant_view = AssistantView(self._user)
        self.graph_view = KnowledgeGraphView(self._user)
        self.profile_view = UserProfileView(self._user)
        self.admin_view = AdminPanelView(self._user)
        self.imaging_analysis_view = ClinicalAnalysisWorkspaceView(self._user)
        self.auth_settings_view = AuthSettingsView(self._user)
        
        # Connect Dashboard upload button to main upload routing
        self.dashboard_view.upload_requested.connect(self._trigger_top_upload)
        self.dashboard_view.action_triggered.connect(self._on_dashboard_action_triggered)
 
        self.content_stack.addWidget(self.dashboard_view)
        self.content_stack.addWidget(self.repository_view)
        self.content_stack.addWidget(self.imaging_analysis_view)
        self.content_stack.addWidget(self.assistant_view)
        self.content_stack.addWidget(self.graph_view)
        self.content_stack.addWidget(self.profile_view)
        self.content_stack.addWidget(self.admin_view)
        self.content_stack.addWidget(self.auth_settings_view)
        
        # Stack indices mapping
        self.module_indices = {
            "dashboard": 0,
            "repository": 1,
            "imaging_analysis": 2,
            "assistant": 3,
            "graph": 4,
            "profile": 5,
            "admin": 6,
            "auth_settings": 7
        }
        
        work_layout.addWidget(self.content_stack, 1)
        layout.addWidget(work_area, 1)
        
        # 3. Status Bar
        self.status_bar = StatusBar()
        layout.addWidget(self.status_bar)
        
        self.set_central_widget(container)

    def _trigger_top_upload(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Medical File for AI Analysis", "", 
            "Medical Files (*.pdf *.png *.jpg *.jpeg *.tiff *.bmp *.dcm *.dicom);;All Files (*)"
        )
        if file_path:
            self.content_stack.setCurrentIndex(2) # Switch to AI Analysis stack view
            self.sidebar.set_active("imaging_analysis")
            self.imaging_analysis_view._start_file_analysis(file_path)

    def _on_dashboard_action_triggered(self, action_id: str) -> None:
        if action_id == "ai_chat":
            self.content_stack.setCurrentIndex(3) # Switch to AI Assistant stack view
            self.sidebar.set_active("assistant")

    def _on_module_selected(self, module_id: str) -> None:
        if module_id == "logout":
            self.logout_requested.emit()
            return
            
        if module_id == "upload_action":
            self._trigger_top_upload()
            return
            
        if module_id == "anatomy_explorer":
            self.content_stack.setCurrentIndex(2) # imaging_analysis
            self.imaging_analysis_view.left_stack.setCurrentIndex(1) # Anatomy Navigator
            self.sidebar.set_active("imaging_analysis")
            return
            
        if module_id == "history":
            self.content_stack.setCurrentIndex(1) # repository
            self.sidebar.set_active("repository")
            return

        if module_id in self.module_indices:
            idx = self.module_indices[module_id]
            self.content_stack.setCurrentIndex(idx)
            
            # Refresh appropriate workspaces on load
            if module_id == "dashboard":
                self.dashboard_view.refresh_stats()
            elif module_id == "repository":
                self.repository_view.refresh_data()
            elif module_id == "admin":
                self.admin_view.load_data()


    def _run_diagnostics(self) -> None:
        """Fetch system configurations and diagnostics to feed progress rings."""
        try:
            db_ok = True
            try:
                check_database_connection()
            except Exception:
                db_ok = False

            chroma_ok = True
            try:
                check_chroma_connection()
            except Exception:
                chroma_ok = False

            ollama_ok = False
            try:
                from ai_core.ai_engine import get_ai_engine
                ai = get_ai_engine()
                ollama_ok = ai.llm._check_availability()
            except Exception:
                ollama_ok = False

            docs_cnt = 0
            chunks_cnt = 0
            storage_mb = 0.0
            
            with get_db_session() as session:
                from database.repositories.document_repository import DocumentRepository
                doc_repo = DocumentRepository(session)
                docs = doc_repo.get_all()
                docs_cnt = len(docs)
                
                from database.models.chunk_model import DocumentChunkModel
                chunks_cnt = session.query(DocumentChunkModel).count()
                
                total_size_bytes = sum([d.file_size or 0 for d in docs])
                storage_mb = total_size_bytes / (1024 * 1024)

            # Calculation metrics
            embed_pct = 100.0 if docs_cnt > 0 else 0.0
            storage_pct = min(100.0, (storage_mb / 250.0) * 100.0) # Quota cap of 250MB

            self.sidebar.update_diagnostics(
                db_ok=db_ok,
                chroma_ok=chroma_ok,
                ollama_ok=ollama_ok,
                embed_pct=embed_pct,
                storage_pct=storage_pct,
                docs_cnt=docs_cnt,
                chunks_cnt=chunks_cnt,
                storage_mb=storage_mb
            )
            
            self.status_bar.set_custom_status(
                f"SYSTEM CORE NODE: ACTIVE // DOCS: {docs_cnt} // CHUNKS: {chunks_cnt}"
            )
        except Exception as e:
            logger.error(f"Failed to query system diagnostics: {e}")
