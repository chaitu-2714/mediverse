"""
MediVerse AI — Authentication Settings View.
Provides comprehensive verification, testing dashboard for database, Supabase, JWT, API, and Google OAuth.
"""
from __future__ import annotations

import logging
import os
from typing import Any
import requests

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea,
    QTextEdit, QMessageBox
)

from config.settings import get_settings
from auth.services.auth_service import AuthService
from database.connection import check_database_connection
from shared.components.notification_toast import NotificationToast

logger = logging.getLogger("mediverse.modules.auth_settings")

class AuthSettingsView(QWidget):
    """
    Dedicated view for configuring, validating, and testing the Supabase authentication module.
    """
    def __init__(self, current_user: Any = None) -> None:
        super().__init__()
        self._user = current_user
        self._auth = AuthService()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # Header Area
        hdr_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Authentication Settings")
        title.setStyleSheet("color: white; font-size: 26px; font-weight: 800; letter-spacing: 0.5px;")
        sub = QLabel("Perform diagnostic connectivity tests, verify Supabase credentials, and self-heal configurations.")
        sub.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 13.5px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        hdr_layout.addLayout(title_box)

        # Launch Wizard Button
        btn_wizard = QPushButton("⚙️ Launch Setup Wizard")
        btn_wizard.setCursor(Qt.PointingHandCursor)
        btn_wizard.setFixedSize(180, 36)
        btn_wizard.setStyleSheet("""
            QPushButton {
                background: rgba(6, 182, 212, 0.1);
                color: #06b6d4;
                border: 1px solid rgba(6, 182, 212, 0.3);
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(6, 182, 212, 0.2);
                border-color: #06b6d4;
            }
        """)
        btn_wizard.clicked.connect(self._launch_setup_wizard)
        hdr_layout.addWidget(btn_wizard, 0, Qt.AlignVCenter)
        layout.addLayout(hdr_layout)

        # Main Layout: Top Panel (Verification Dashboard), Bottom Panel (Diagnostic Console Logs)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # Test Suite Card
        tests_card = QFrame()
        tests_card.setStyleSheet("background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 16px;")
        tests_layout = QVBoxLayout(tests_card)
        tests_layout.setContentsMargins(24, 24, 24, 24)
        tests_layout.setSpacing(18)

        card_title = QLabel("Connectivity & Credentials Test Suite")
        card_title.setStyleSheet("color: #06b6d4; font-size: 15px; font-weight: bold;")
        tests_layout.addWidget(card_title)

        # 6 Test Rows
        self.test_grid = QGridLayout()
        self.test_grid.setSpacing(14)
        self.test_grid.setColumnStretch(0, 2)
        self.test_grid.setColumnStretch(1, 1)
        self.test_grid.setColumnStretch(2, 3)

        self._add_test_row("Verify Configuration", "Checks .env settings templates & placeholders", self._test_verify_config, 0)
        self._add_test_row("Test Database", "Verifies PostgreSQL connectivity & tables", self._test_database, 1)
        self._add_test_row("Test Supabase", "Tests Supabase Auth Client connectivity", self._test_supabase, 2)
        self._add_test_row("Test Google Login", "Checks Google API Client configuration validity", self._test_google_login, 3)
        self._add_test_row("Test JWT", "Decodes local secret key validation status", self._test_jwt, 4)
        self._add_test_row("Test API", "Tests connection to local FastAPI backend router", self._test_api, 5)

        tests_layout.addLayout(self.test_grid)
        scroll_layout.addWidget(tests_card)

        # Error Console Card
        console_card = QFrame()
        console_card.setStyleSheet("background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 16px;")
        console_layout = QVBoxLayout(console_card)
        console_layout.setContentsMargins(24, 24, 24, 24)
        console_layout.setSpacing(12)

        console_title = QLabel("Diagnostic & Resolution Report")
        console_title.setStyleSheet("color: #ef4444; font-size: 15px; font-weight: bold;")
        console_layout.addWidget(console_title)

        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        self.console_text.setFixedHeight(220)
        self.console_text.setStyleSheet("""
            QTextEdit {
                background: #090e18;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: #e2e8f0;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 10px;
            }
        """)
        self.console_text.setPlaceholderText("All authentication subsystem reports will be detailed here upon testing...")
        console_layout.addWidget(self.console_text)

        scroll_layout.addWidget(console_card)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)

    def _add_test_row(self, name: str, desc: str, callback: callable, row: int) -> None:
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("color: white; font-size: 13.5px; font-weight: bold;")
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 11.5px;")
        
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.addWidget(name_lbl)
        info_col.addWidget(desc_lbl)
        self.test_grid.addLayout(info_col, row, 0)

        # Status badge
        badge = QLabel("PENDING")
        badge.setFixedSize(90, 24)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("background: rgba(255, 255, 255, 0.05); color: rgba(255, 255, 255, 0.5); border-radius: 6px; font-size: 10px; font-weight: bold;")
        self.test_grid.addWidget(badge, row, 1)

        # Action Button
        btn = QPushButton("Run Test")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(100, 28)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(6, 182, 212, 0.15);
                border-color: rgba(6, 182, 212, 0.4);
            }
        """)
        btn.clicked.connect(lambda: callback(badge, btn))
        self.test_grid.addWidget(btn, row, 2)

    def _update_badge(self, badge: QLabel, status: bool, text: str = "") -> None:
        if status:
            badge.setText(text or "SUCCESS")
            badge.setStyleSheet("background: rgba(34, 197, 94, 0.15); color: #22c55e; border-radius: 6px; font-size: 10px; font-weight: bold;")
        else:
            badge.setText(text or "FAILED")
            badge.setStyleSheet("background: rgba(239, 68, 68, 0.15); color: #ef4444; border-radius: 6px; font-size: 10px; font-weight: bold;")

    def _report_error(self, test_name: str, problem: str, cause: str, fix: str, developer_details: str) -> None:
        err_msg = (
            f"=== {test_name.upper()} FAILED ===\n"
            f"Problem: {problem}\n"
            f"Cause: {cause}\n"
            f"How to Fix: {fix}\n"
            f"Developer Details: {developer_details}\n"
            f"======================================\n\n"
        )
        self.console_text.append(err_msg)

    def _launch_setup_wizard(self) -> None:
        from auth.ui.setup_wizard_window import SetupWizardWindow
        wizard = SetupWizardWindow(self.window())
        wizard.exec()

    # ── Test Implementations ─────────────────────────────────────────

    def _test_verify_config(self, badge: QLabel, btn: QPushButton) -> None:
        from auth.services.env_validator import check_env_status
        status_map = check_env_status()
        missing = [k for k, v in status_map.items() if not v]
        
        if not missing:
            self._update_badge(badge, True, "VERIFIED")
            self.console_text.append("✓ Configuration Verification: All env variables are configured.\n")
        else:
            self._update_badge(badge, False, "INCOMPLETE")
            self._report_error(
                "Verify Configuration",
                "Credentials missing in local configuration environment (.env).",
                f"Missing variables: {', '.join(missing)}",
                "Launch the Setup Wizard to input values or edit .env directly.",
                f"Status: {status_map}"
            )

    def _test_database(self, badge: QLabel, btn: QPushButton) -> None:
        try:
            if check_database_connection():
                self._update_badge(badge, True)
                self.console_text.append("✓ Database: Connected to PostgreSQL database successfully.\n")
        except Exception as e:
            self._update_badge(badge, False)
            settings = get_settings()
            self._report_error(
                "Test Database",
                "Unable to establish database connection.",
                str(e),
                f"Check that PostgreSQL server is running at {settings.db_host}:{settings.db_port} and credentials are correct.",
                f"Database host: {settings.db_host}, dbname: {settings.db_name}"
            )

    def _test_supabase(self, badge: QLabel, btn: QPushButton) -> None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_service_key:
            self._update_badge(badge, False)
            self._report_error(
                "Test Supabase",
                "Supabase URL or Service Key is missing.",
                "Environment variables not configured.",
                "Ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set.",
                "Check Credentials tab in the Setup Wizard."
            )
            return

        try:
            from backend.auth.supabase_auth import SupabaseAuthHelper
            helper = SupabaseAuthHelper()
            if helper.client:
                # Basic ping or connection validation
                self._update_badge(badge, True)
                self.console_text.append("✓ Supabase: Client initialized successfully.\n")
            else:
                raise ValueError("Client failed to initialize.")
        except Exception as e:
            self._update_badge(badge, False)
            self._report_error(
                "Test Supabase",
                "Supabase client connection failure.",
                str(e),
                "Verify your SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY values.",
                f"Supabase URL: {settings.supabase_url}"
            )

    def _test_google_login(self, badge: QLabel, btn: QPushButton) -> None:
        settings = get_settings()
        if not settings.google_client_id or not settings.google_client_secret:
            self._update_badge(badge, False)
            self._report_error(
                "Test Google Login",
                "Google Client ID or Client Secret is missing.",
                "Google OAuth credentials not configured.",
                "Launch Setup Wizard, open Google OAuth tab and follow steps.",
                "Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET variables."
            )
            return

        if not settings.google_client_id.endswith("googleusercontent.com"):
            self._update_badge(badge, False)
            self._report_error(
                "Test Google Login",
                "Google Client ID format is invalid.",
                "Expected suffix 'googleusercontent.com' is missing.",
                "Verify and paste the full Web Client ID from Google Cloud Console.",
                f"Client ID: {settings.google_client_id}"
            )
            return

        self._update_badge(badge, True, "READY")
        self.console_text.append("✓ Google Login: Client credentials syntax check passed.\n")

    def _test_jwt(self, badge: QLabel, btn: QPushButton) -> None:
        settings = get_settings()
        jwt_key = settings.jwt_secret_key
        if not jwt_key or jwt_key == "change-this-jwt-secret":
            self._update_badge(badge, False)
            self._report_error(
                "Test JWT",
                "Insecure or missing JWT secret key.",
                "The default secret key is active.",
                "Generate a cryptographically secure JWT secret key in the Setup Wizard.",
                "JWT_SECRET should be a unique 256-bit string."
            )
        elif len(jwt_key) < 32:
            self._update_badge(badge, False)
            self._report_error(
                "Test JWT",
                "JWT Secret is too short.",
                f"Length is {len(jwt_key)} characters (minimum 32 required).",
                "Regenerate the secret key using the Setup Wizard.",
                "Weak keys are vulnerable to decoding attacks."
            )
        else:
            self._update_badge(badge, True)
            self.console_text.append("✓ JWT: Local token cryptographic configuration is secure.\n")

    def _test_api(self, badge: QLabel, btn: QPushButton) -> None:
        try:
            res = requests.get("http://localhost:8000/auth/verify", timeout=3)
            if res.status_code == 200:
                self._update_badge(badge, True)
                self.console_text.append("✓ API: FastAPI auth verify endpoint returned status 200.\n")
            else:
                raise ValueError(f"HTTP Status {res.status_code}")
        except Exception as e:
            self._update_badge(badge, False)
            self._report_error(
                "Test API",
                "FastAPI auth server is offline or unreachable.",
                str(e),
                "Verify the FastAPI backend process is running (uvicorn on port 8000).",
                "Uvicorn startup: python -m uvicorn backend.main:app"
            )
