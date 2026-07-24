"""
MediVerse AI — Supabase & Google OAuth Configuration Setup Wizard.
Redesigned with beautiful tabs, 10-Point check, guided Google steps, and self-healing diagnostics cards.
"""
from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QPalette, QCursor, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit, QTabWidget,
    QScrollArea, QApplication, QMessageBox, QWidget,
    QSizePolicy, QGridLayout, QTextEdit
)

from auth.services.env_validator import check_env_status, save_env_config
from config.settings import get_settings
from database.connection import check_database_connection
from shared.components.notification_toast import NotificationToast

logger = logging.getLogger("mediverse.setup_wizard")

_DIALOG_STYLE = """
    QDialog {
        background-color: #080c16;
        color: #e2e8f0;
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }
    QLabel {
        color: rgba(255,255,255,0.9);
        background: transparent;
    }
    QTabWidget::pane {
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.01);
        padding: 12px;
    }
    QTabBar::tab {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        padding: 10px 20px;
        color: rgba(255, 255, 255, 0.55);
        font-weight: bold;
        font-size: 12px;
    }
    QTabBar::tab:selected {
        background: rgba(6, 182, 212, 0.12);
        border-color: rgba(6, 182, 212, 0.35);
        color: #06b6d4;
    }
    QTabBar::tab:hover {
        background: rgba(255, 255, 255, 0.05);
        color: white;
    }
    QScrollArea {
        border: none;
        background: transparent;
    }
    QScrollBar:vertical {
        background: rgba(255, 255, 255, 0.02);
        width: 6px;
        border-radius: 3px;
    }
    QScrollBar::handle:vertical {
        background: rgba(6, 182, 212, 0.3);
        border-radius: 3px;
    }
"""

_FIELD_STYLE = """
    QLineEdit {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px;
        color: white;
        padding: 0 12px;
        font-size: 12px;
        font-family: 'Consolas', monospace;
    }
    QLineEdit:focus {
        border: 1.5px solid #06b6d4;
        background: rgba(6, 182, 212, 0.04);
    }
    QLineEdit::placeholder { color: rgba(255,255,255,0.25); }
"""

_BTN_ACTION = """
    QPushButton {
        background: rgba(255,255,255,0.06);
        color: rgba(255,255,255,0.9);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px;
        font-size: 11px;
        font-weight: bold;
        padding: 6px 12px;
    }
    QPushButton:hover {
        background: rgba(6,182,212,0.18);
        border-color: rgba(6,182,212,0.4);
        color: white;
    }
"""

_BTN_SAVE = """
    QPushButton {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #06b6d4,stop:1 #3b82f6);
        color: white; border: none; border-radius: 10px;
        font-size: 13.5px; font-weight: bold; height: 40px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0891b2,stop:1 #2563eb);
    }
    QPushButton:disabled {
        background: rgba(255,255,255,0.05);
        color: rgba(255,255,255,0.3);
    }
"""

_BTN_EXIT = """
    QPushButton {
        background: rgba(239,68,68,0.08); color: #ef4444;
        border: 1px solid rgba(239,68,68,0.2); border-radius: 10px;
        font-size: 13.5px; font-weight: bold; height: 40px;
    }
    QPushButton:hover { background: rgba(239,68,68,0.16); }
"""


class SetupWizardWindow(QDialog):
    """
    Stunning multi-step/tab Supabase and Google OAuth Setup Wizard.
    """
    configuration_completed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setWindowTitle("MediVerse AI — Auth Setup Wizard")
        self.setMinimumSize(960, 680)
        self.setStyleSheet(_DIALOG_STYLE)
        self.setModal(True)

        self.settings = get_settings()
        self._fields: Dict[str, QLineEdit] = {}
        
        self._build_ui()
        self._run_diagnostics()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # Header Title
        hdr = QHBoxLayout()
        logo_lbl = QLabel("⚕  MediVerse AI")
        logo_lbl.setStyleSheet("color: #06b6d4; font-size: 20px; font-weight: 900; letter-spacing: 2px;")
        hdr.addWidget(logo_lbl)
        hdr.addStretch()
        
        status_lbl = QLabel("Authentication setup portal")
        status_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 12px; font-style: italic;")
        hdr.addWidget(status_lbl)
        root.addLayout(hdr)

        self.tab_widget = QTabWidget()
        root.addWidget(self.tab_widget, 1)

        # ── TAB 1: 10-Point Health Checks ────────────────────────────────
        self.tab_status = QWidget()
        status_layout = QVBoxLayout(self.tab_status)
        status_layout.setContentsMargins(10, 10, 10, 10)
        status_layout.setSpacing(12)

        status_desc = QLabel("Real-time analysis of the 10 authentication and connection requirements:")
        status_desc.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 13px; font-weight: bold;")
        status_layout.addWidget(status_desc)

        # Grid of status cards
        self.checks_grid_layout = QGridLayout()
        self.checks_grid_layout.setSpacing(12)
        
        scroll_status = QScrollArea()
        scroll_status_widget = QWidget()
        scroll_status_widget.setLayout(self.checks_grid_layout)
        scroll_status.setWidget(scroll_status_widget)
        scroll_status.setWidgetResizable(True)
        status_layout.addWidget(scroll_status, 1)

        self.tab_widget.addTab(self.tab_status, "🔍  10-Point Check")

        # ── TAB 2: Guided Google OAuth Steps ─────────────────────────────
        self.tab_google = QWidget()
        google_layout = QVBoxLayout(self.tab_google)
        google_layout.setContentsMargins(15, 15, 15, 15)
        google_layout.setSpacing(14)

        g_title = QLabel("Guided Google OAuth 2.0 Credentials Setup")
        g_title.setStyleSheet("color: #38bdf8; font-size: 16px; font-weight: bold;")
        google_layout.addWidget(g_title)

        # Create step instructions
        steps_box = QFrame()
        steps_box.setStyleSheet("background: rgba(255, 255, 255, 0.015); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;")
        steps_layout = QVBoxLayout(steps_box)
        steps_layout.setSpacing(18)
        steps_layout.setContentsMargins(20, 20, 20, 20)

        def add_step(num: str, title: str, text: str):
            row = QHBoxLayout()
            badge = QLabel(num)
            badge.setFixedSize(28, 28)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet("background: #0284c7; color: white; border-radius: 14px; font-weight: 900; font-size: 13px;")
            
            content = QVBoxLayout()
            content.setSpacing(2)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
            d_lbl = QLabel(text)
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.55); font-size: 11.5px;")
            content.addWidget(t_lbl)
            content.addWidget(d_lbl)
            
            row.addWidget(badge, 0, Qt.AlignTop)
            row.addLayout(content, 1)
            steps_layout.addLayout(row)

        add_step("1", "Create Google OAuth Client", 
                 "Go to the Google Cloud Console > Credentials. Click '+ Create Credentials' and select 'OAuth Client ID'. Set application type to 'Web application'.")
        
        add_step("2", "Configure Redirect URIs", 
                 "In Google Console under Authorized Redirect URIs, add: http://localhost:8000/auth/google/callback and http://127.0.0.1:8000/auth/google/callback")

        add_step("3", "Copy Client Credentials", 
                 "Once created, copy the generated Client ID and Client Secret into the Credentials Config tab of this wizard.")

        add_step("4", "Click Verify", 
                 "Go to the Config tab, save your changes, and run configuration verification to automatically test Google OAuth.")

        google_layout.addWidget(steps_box, 1)
        self.tab_widget.addTab(self.tab_google, "🤖  Google OAuth Wizard")

        # ── TAB 3: Credentials Config Editor ─────────────────────────────
        self.tab_config = QWidget()
        config_layout = QVBoxLayout(self.tab_config)
        config_layout.setContentsMargins(15, 15, 15, 15)
        config_layout.setSpacing(14)

        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(4, 4, 4, 4)

        # Variables lists to construct edit rows
        vars_to_edit = [
            ("SUPABASE_URL", "Supabase Project URL", "https://yourproject.supabase.co"),
            ("SUPABASE_ANON_KEY", "Supabase Publishable/Anon Key", "eyJhbGciOiJIUzI1Ni..."),
            ("SUPABASE_SERVICE_ROLE_KEY", "Supabase Service Role Key", "eyJhbGciOiJIUzI1Ni..."),
            ("GOOGLE_CLIENT_ID", "Google Client ID", "128254797009-xxx.apps.googleusercontent.com"),
            ("GOOGLE_CLIENT_SECRET", "Google Client Secret", "GOCSPX-xxx"),
            ("GOOGLE_REDIRECT_URI", "Google Callback Redirect URL", "http://localhost:8000/auth/google/callback"),
            ("JWT_SECRET", "Application JWT Secret Key", "secure-sha256-string")
        ]

        for var, label, placeholder in vars_to_edit:
            self._add_config_row(form_layout, var, label, placeholder)

        form_scroll.setWidget(form_widget)
        config_layout.addWidget(form_scroll, 1)

        self.tab_widget.addTab(self.tab_config, "⚙️  Credentials Config")

        # ── TAB 4: Self-Healing Diagnostics ──────────────────────────────
        self.tab_heal = QWidget()
        heal_layout = QVBoxLayout(self.tab_heal)
        heal_layout.setContentsMargins(15, 15, 15, 15)
        heal_layout.setSpacing(12)

        heal_title = QLabel("Self-Healing Diagnostic Engine")
        heal_title.setStyleSheet("color: #ef4444; font-size: 16px; font-weight: bold;")
        heal_layout.addWidget(heal_title)

        self.heal_scroll = QScrollArea()
        self.heal_scroll.setWidgetResizable(True)
        self.heal_list_widget = QWidget()
        self.heal_list_layout = QVBoxLayout(self.heal_list_widget)
        self.heal_list_layout.setSpacing(14)
        self.heal_list_layout.setAlignment(Qt.AlignTop)
        self.heal_scroll.setWidget(self.heal_list_widget)
        heal_layout.addWidget(self.heal_scroll, 1)

        self.tab_widget.addTab(self.tab_heal, "🩺  Self-Healing Log")

        # Footer Row Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet(_BTN_EXIT)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_verify = QPushButton("Save and Validate Configuration")
        self.btn_verify.setStyleSheet(_BTN_SAVE)
        self.btn_verify.setCursor(Qt.PointingHandCursor)
        self.btn_verify.clicked.connect(self._save_and_verify)

        btn_row.addWidget(self.btn_cancel, 1)
        btn_row.addWidget(self.btn_verify, 2)
        root.addLayout(btn_row)

    def _add_config_row(self, layout: QVBoxLayout, var_name: str, label: str, placeholder: str) -> None:
        card = QFrame()
        card.setStyleSheet("background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;")
        
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        col = QVBoxLayout()
        col.setSpacing(2)
        name_lbl = QLabel(label)
        name_lbl.setStyleSheet("color: white; font-size: 11.5px; font-weight: bold;")
        var_lbl = QLabel(var_name)
        var_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.35); font-size: 9.5px; font-family: 'Consolas';")
        col.addWidget(name_lbl)
        col.addWidget(var_lbl)
        row.addLayout(col, 2)

        edit = QLineEdit()
        edit.setFixedHeight(34)
        edit.setStyleSheet(_FIELD_STYLE)
        edit.setPlaceholderText(placeholder)
        
        # Load value
        current_val = os.environ.get(var_name) or getattr(self.settings, var_name.lower(), "")
        if current_val:
            edit.setText(str(current_val))
            
        self._fields[var_name] = edit
        row.addWidget(edit, 3)

        if var_name == "JWT_SECRET":
            btn = QPushButton("Generate")
            btn.setStyleSheet(_BTN_ACTION)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda: edit.setText(secrets.token_hex(32)))
            row.addWidget(btn)

        layout.addWidget(card)

    def _run_diagnostics(self) -> None:
        """Evaluate configuration state across 10 distinct health points."""
        # Refresh local environment variables from file first
        from dotenv import load_dotenv
        load_dotenv(override=True)
        self.settings = get_settings()

        # 10 Point Checks Array
        checks = []

        # 1. Supabase configured
        sb_url = os.environ.get("SUPABASE_URL") or ""
        sb_anon = os.environ.get("SUPABASE_ANON_KEY") or ""
        sb_service = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""
        sb_configured = bool(sb_url and sb_anon and sb_service)
        checks.append({
            "name": "Supabase Configuration Status",
            "ok": sb_configured,
            "problem": "Supabase credentials incomplete",
            "reason": "One or more of SUPABASE_URL, SUPABASE_ANON_KEY, or SUPABASE_SERVICE_ROLE_KEY are empty or placeholder values.",
            "fix": "Locate and copy all 3 API details from Project Settings > API on Supabase Dashboard.",
            "current": f"URL={bool(sb_url)}, Anon={bool(sb_anon)}, ServiceRole={bool(sb_service)}",
            "expected": "URL, Anon and ServiceRole keys all configured"
        })

        # 2. Google OAuth configured
        g_id = os.environ.get("GOOGLE_CLIENT_ID") or ""
        g_sec = os.environ.get("GOOGLE_CLIENT_SECRET") or ""
        google_configured = bool(g_id and g_sec)
        checks.append({
            "name": "Google OAuth Setup Status",
            "ok": google_configured,
            "problem": "Google OAuth is not configured",
            "reason": "Client ID and Client Secret from Google Cloud Console are not configured in your .env.",
            "fix": "Open Google Cloud Console > Credentials, create a Web application client ID, and input the credentials.",
            "current": f"ID={bool(g_id)}, Secret={bool(g_sec)}",
            "expected": "Google Client ID and Client Secret configured"
        })

        # 3. Redirect URIs missing check
        g_redir = os.environ.get("GOOGLE_REDIRECT_URI") or ""
        redir_ok = bool(g_redir and ("auth/google/callback" in g_redir))
        checks.append({
            "name": "Callback Redirect URI Configuration",
            "ok": redir_ok,
            "problem": "Missing or mismatched Redirect URI",
            "reason": "GOOGLE_REDIRECT_URI is not set or does not route to the correct FastAPI callback path.",
            "fix": "Set GOOGLE_REDIRECT_URI to http://localhost:8000/auth/google/callback in your .env file.",
            "current": g_redir or "Not set",
            "expected": "http://localhost:8000/auth/google/callback"
        })

        # 4. Invalid Client ID check
        cid_valid = bool(g_id and g_id.endswith("googleusercontent.com"))
        checks.append({
            "name": "Google Client ID Validation",
            "ok": cid_valid if g_id else False,
            "problem": "Invalid Google Client ID Format",
            "reason": "The Client ID does not end with 'googleusercontent.com'.",
            "fix": "Verify you copied the full web application client ID from the Google Console.",
            "current": g_id or "Not set",
            "expected": "<random-hash>.apps.googleusercontent.com"
        })

        # 5. Invalid Client Secret check
        csec_valid = bool(g_sec and len(g_sec) > 8 and not g_sec.startswith("your-"))
        checks.append({
            "name": "Google Client Secret Integrity",
            "ok": csec_valid if g_sec else False,
            "problem": "Invalid Google Client Secret",
            "reason": "The Google Client Secret key is missing or contains placeholder templates.",
            "fix": "Copy the secure Client Secret string directly from the Google Credentials dashboard.",
            "current": g_sec[:6] + "..." if g_sec else "Not set",
            "expected": "Valid secret alphanumeric string"
        })

        # 6. Invalid Supabase URL check
        url_valid = bool(sb_url and sb_url.startswith("https://") and "supabase.co" in sb_url)
        checks.append({
            "name": "Supabase Project URL Integrity",
            "ok": url_valid,
            "problem": "Invalid Supabase URL Format",
            "reason": "The Supabase URL must be a valid secure HTTPS link ending in '.supabase.co'.",
            "fix": "Ensure you did not copy dashboard URL. Use API Project URL (e.g. https://xxxx.supabase.co).",
            "current": sb_url or "Not set",
            "expected": "https://<project-ref>.supabase.co"
        })

        # 7. Invalid Publishable (Anon) Key check
        anon_valid = bool(sb_anon and len(sb_anon) > 50 and sb_anon.startswith("eyJ"))
        checks.append({
            "name": "Supabase Publishable Key Check",
            "ok": anon_valid,
            "problem": "Invalid Supabase Anon/Publishable Key",
            "reason": "The Anon Key must be a valid JWT (starts with 'eyJ').",
            "fix": "Ensure you copy the public 'anon' key from the Supabase settings.",
            "current": sb_anon[:10] + "..." if sb_anon else "Not set",
            "expected": "Long JWT signature starting with eyJ"
        })

        # 8. Invalid Service Role Key check
        role_valid = bool(sb_service and len(sb_service) > 50 and sb_service.startswith("eyJ"))
        checks.append({
            "name": "Supabase Service Role Key Check",
            "ok": role_valid,
            "problem": "Invalid Supabase Service Role Key",
            "reason": "The Service Role Key must be a valid private JWT (starts with 'eyJ').",
            "fix": "Copy the secure 'service_role' key. Keep this key confidential.",
            "current": sb_service[:10] + "..." if sb_service else "Not set",
            "expected": "Long administrative JWT starting with eyJ"
        })

        # 9. Validate JWT configuration
        jwt_sec = os.environ.get("JWT_SECRET") or ""
        jwt_valid = bool(jwt_sec and len(jwt_sec) >= 32 and jwt_sec != "change-this-jwt-secret")
        checks.append({
            "name": "JWT Cryptographic Configuration",
            "ok": jwt_valid,
            "problem": "Weak or missing local JWT Secret",
            "reason": "JWT_SECRET is either not configured or too short (needs at least 32 characters for local session encryption security).",
            "fix": "Press the 'Generate' button next to JWT_SECRET in the Config tab to create a secure key.",
            "current": jwt_sec or "Not set",
            "expected": "Secure 32+ character hex/alphanumeric string"
        })

        # 10. Validate PostgreSQL connection
        db_connected = False
        db_err = "Not tested"
        try:
            db_connected = check_database_connection()
            db_err = "Connection healthy"
        except Exception as e:
            db_err = str(e)
            
        checks.append({
            "name": "PostgreSQL Database Connection",
            "ok": db_connected,
            "problem": "PostgreSQL database connection failed",
            "reason": f"Connection handshake failed: {db_err}",
            "fix": "Verify that your local PostgreSQL instance is running on the port configured in .env.",
            "current": f"host={os.environ.get('DB_HOST', 'localhost')}, port={os.environ.get('DB_PORT', '5432')}",
            "expected": "Database connection healthy"
        })

        # Update 10-Point check UI grid
        # Clear layout first
        for i in reversed(range(self.checks_grid_layout.count())): 
            self.checks_grid_layout.itemAt(i).widget().setParent(None)

        for i, chk in enumerate(checks):
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            cl = QVBoxLayout(card)
            cl.setSpacing(4)
            
            top = QHBoxLayout()
            name_lbl = QLabel(chk["name"])
            name_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
            
            badge = QLabel("PASS" if chk["ok"] else "FAIL")
            badge.setFixedSize(48, 18)
            badge.setAlignment(Qt.AlignCenter)
            if chk["ok"]:
                badge.setStyleSheet("background: rgba(34, 197, 94, 0.12); color: #22c55e; border-radius: 4px; font-size: 9.5px; font-weight: bold;")
            else:
                badge.setStyleSheet("background: rgba(239, 68, 68, 0.12); color: #ef4444; border-radius: 4px; font-size: 9.5px; font-weight: bold;")
                
            top.addWidget(name_lbl)
            top.addStretch()
            top.addWidget(badge)
            cl.addLayout(top)
            
            curr = QLabel(f"Current: {chk['current']}")
            curr.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 9.5px;")
            cl.addWidget(curr)

            row = i // 2
            col = i % 2
            self.checks_grid_layout.addWidget(card, row, col)

        # Update Self-Healing Logs UI
        for i in reversed(range(self.heal_list_layout.count())):
            item = self.heal_list_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        failed_checks = [c for c in checks if not c["ok"]]
        if failed_checks:
            for chk in failed_checks:
                card = QFrame()
                card.setStyleSheet("""
                    QFrame {
                        background: rgba(239, 68, 68, 0.03);
                        border: 1px solid rgba(239, 68, 68, 0.2);
                        border-radius: 10px;
                        padding: 14px;
                    }
                """)
                hl = QVBoxLayout(card)
                hl.setSpacing(6)
                
                prob_lbl = QLabel(f"⚠️ Problem: {chk['problem']}")
                prob_lbl.setStyleSheet("color: #ef4444; font-size: 13.5px; font-weight: bold;")
                hl.addWidget(prob_lbl)

                reason_lbl = QLabel(f"<b>Reason:</b> {chk['reason']}")
                reason_lbl.setWordWrap(True)
                reason_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 11.5px;")
                hl.addWidget(reason_lbl)

                fix_lbl = QLabel(f"<b>Fix:</b> {chk['fix']}")
                fix_lbl.setWordWrap(True)
                fix_lbl.setStyleSheet("color: #22c55e; font-size: 11.5px; font-weight: bold;")
                hl.addWidget(fix_lbl)

                det_lbl = QLabel(f"<b>Current Value:</b> <font color='#e2e8f0'>{chk['current']}</font> &nbsp;&nbsp;|&nbsp;&nbsp; <b>Expected:</b> <font color='#a7f3d0'>{chk['expected']}</font>")
                det_lbl.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 10.5px;")
                hl.addWidget(det_lbl)
                
                self.heal_list_layout.addWidget(card)
        else:
            no_issues = QLabel("🎉  Perfect Configuration! No authentication or configuration anomalies detected.")
            no_issues.setAlignment(Qt.AlignCenter)
            no_issues.setStyleSheet("color: #22c55e; font-size: 13px; font-weight: bold; padding: 40px;")
            self.heal_list_layout.addWidget(no_issues)

    def _save_and_verify(self) -> None:
        self.btn_verify.setEnabled(False)
        self.btn_verify.setText("Saving & Validating…")
        QApplication.processEvents()

        updates = {}
        for var, edit in self._fields.items():
            updates[var] = edit.text().strip()

        try:
            save_env_config(updates)
            logger.info("Credentials written to .env file successfully.")
            
            # Reload diagnostics
            self._run_diagnostics()
            
            # Check if there are any failures left
            from auth.services.env_validator import get_missing_vars
            missing = get_missing_vars()
            
            # Re-read database to see if it links
            db_ok = False
            try:
                db_ok = check_database_connection()
            except Exception:
                pass

            if not missing and db_ok:
                NotificationToast.show_message(self, "All configurations verified successfully!", "success")
                QTimer.singleShot(1500, self._on_success)
            else:
                NotificationToast.show_message(self, "Configuration saved with warnings. Review healing logs.", "warning")
                self.tab_widget.setCurrentIndex(3) # Switch to Self-Healing tab
        except Exception as e:
            logger.error(f"Failed saving configuration: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to persist configuration to .env:\n{str(e)}")
        finally:
            self.btn_verify.setEnabled(True)
            self.btn_verify.setText("Save and Validate Configuration")

    def _on_success(self) -> None:
        self.configuration_completed.emit()
        self.accept()
