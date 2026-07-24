"""
MediVerse AI — Operator User Profile Workspace.
Provides a premium visual display of operator credentials, security clearance level,
and allows modifying credentials/password securely.
"""
from __future__ import annotations

import logging
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QGridLayout, QMessageBox
)

from core.models.user import User
from auth.services.auth_service import AuthService
from shared.components.notification_toast import NotificationToast

logger = logging.getLogger("mediverse.modules.profile")


class UserProfileView(QWidget):
    """Operator Profile workspace view."""

    def __init__(self, current_user: User) -> None:
        super().__init__()
        self._user = current_user
        self._auth = AuthService()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        # Header Area
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Operator Profile")
        title.setStyleSheet("color: white; font-size: 26px; font-weight: 800; letter-spacing: 0.5px;")
        sub = QLabel("View system authorization status, security clearance level, and manage security credentials.")
        sub.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        layout.addLayout(header)

        # Content Box
        content_box = QHBoxLayout()
        content_box.setSpacing(25)

        # Left Column: Profile Card
        profile_card = QFrame()
        profile_card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 16px;
            }
        """)
        profile_card_layout = QVBoxLayout(profile_card)
        profile_card_layout.setContentsMargins(30, 35, 30, 35)
        profile_card_layout.setSpacing(20)

        # Avatar indicator
        avatar_layout = QHBoxLayout()
        self.avatar_lbl = QLabel("👤")
        self.avatar_lbl.setFixedSize(80, 80)
        self.avatar_lbl.setAlignment(Qt.AlignCenter)
        self.avatar_lbl.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(6, 182, 212, 0.15), stop:1 rgba(59, 130, 246, 0.15));
                border: 2px solid #06b6d4;
                border-radius: 40px;
                font-size: 36px;
                color: white;
            }
        """)
        avatar_layout.addWidget(self.avatar_lbl)
        profile_card_layout.addLayout(avatar_layout)

        # User details block
        name_lbl = QLabel(self._user.full_name or self._user.username)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet("color: white; font-size: 18px; font-weight: bold; border: none; background: transparent;")
        profile_card_layout.addWidget(name_lbl)

        role_badge = QLabel(self._user.role_display.upper())
        role_badge.setAlignment(Qt.AlignCenter)
        role_badge.setStyleSheet("""
            background: rgba(6, 182, 212, 0.12); 
            color: #06b6d4;
            border: 1px solid rgba(6, 182, 212, 0.25);
            border-radius: 6px; 
            padding: 4px 10px; 
            font-size: 10px; 
            font-weight: bold;
            margin: 0 auto;
        """)
        profile_card_layout.addWidget(role_badge)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255, 255, 255, 0.06); border: none;")
        profile_card_layout.addWidget(div)

        # Stats Grid
        grid = QGridLayout()
        grid.setSpacing(15)

        def add_info_row(label_text, val_text, row):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 11px; font-weight: 600; border: none; background: transparent;")
            val = QLabel(val_text)
            val.setStyleSheet("color: white; font-size: 12px; font-weight: 500; border: none; background: transparent;")
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)

        add_info_row("Username", self._user.username, 0)
        add_info_row("Email Node", self._user.email, 1)
        add_info_row("Onboarded", "Verified" if self._user.is_onboarded else "Pending", 2)
        add_info_row("System Sessions", str(self._user.login_count), 3)

        created_str = self._user.created_at.strftime("%Y-%m-%d") if self._user.created_at else "N/A"
        add_info_row("Registered", created_str, 4)

        last_login_str = self._user.last_login.strftime("%Y-%m-%d %H:%M") if self._user.last_login else "N/A"
        add_info_row("Last Access", last_login_str, 5)

        profile_card_layout.addLayout(grid)
        profile_card_layout.addStretch()

        content_box.addWidget(profile_card, 1)

        # Right Column: Security Configurations (Password Change)
        security_card = QFrame()
        security_card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 16px;
            }
        """)
        sec_layout = QVBoxLayout(security_card)
        sec_layout.setContentsMargins(30, 30, 30, 30)
        sec_layout.setSpacing(20)

        sec_title = QLabel("Modify Credentials / Password")
        sec_title.setStyleSheet("color: #06b6d4; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        sec_layout.addWidget(sec_title)

        inputs_grid = QGridLayout()
        inputs_grid.setSpacing(15)

        # Old password input
        old_lbl = QLabel("Current Password")
        old_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11.5px; font-weight: 600; border: none;")
        self.old_pass_input = QLineEdit()
        self.old_pass_input.setEchoMode(QLineEdit.Password)
        self.old_pass_input.setFixedHeight(36)
        self.old_pass_input.setStyleSheet(self._input_style())
        inputs_grid.addWidget(old_lbl, 0, 0)
        inputs_grid.addWidget(self.old_pass_input, 0, 1)

        # New password input
        new_lbl = QLabel("New Password")
        new_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11.5px; font-weight: 600; border: none;")
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setEchoMode(QLineEdit.Password)
        self.new_pass_input.setFixedHeight(36)
        self.new_pass_input.setStyleSheet(self._input_style())
        inputs_grid.addWidget(new_lbl, 1, 0)
        inputs_grid.addWidget(self.new_pass_input, 1, 1)

        # Confirm new password input
        conf_lbl = QLabel("Confirm New Password")
        conf_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11.5px; font-weight: 600; border: none;")
        self.confirm_pass_input = QLineEdit()
        self.confirm_pass_input.setEchoMode(QLineEdit.Password)
        self.confirm_pass_input.setFixedHeight(36)
        self.confirm_pass_input.setStyleSheet(self._input_style())
        inputs_grid.addWidget(conf_lbl, 2, 0)
        inputs_grid.addWidget(self.confirm_pass_input, 2, 1)

        sec_layout.addLayout(inputs_grid)
        sec_layout.addStretch()

        # Update button
        update_btn = QPushButton("Update Security Credentials")
        update_btn.setFixedHeight(40)
        update_btn.setCursor(Qt.PointingHandCursor)
        update_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #06b6d4);
                color: white; border: none; border-radius: 8px;
                font-weight: bold; font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #0891b2);
            }
        """)
        update_btn.clicked.connect(self._change_password)
        sec_layout.addWidget(update_btn)

        content_box.addWidget(security_card, 1)
        layout.addLayout(content_box, 1)

    def _input_style(self) -> str:
        return """
            QLineEdit {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: white;
                font-size: 13px;
                padding: 0 12px;
            }
            QLineEdit:focus { border: 1px solid #06b6d4; }
        """

    def _change_password(self) -> None:
        old = self.old_pass_input.text().strip()
        new = self.new_pass_input.text().strip()
        confirm = self.confirm_pass_input.text().strip()

        if not old or not new or not confirm:
            NotificationToast.show_message(self.window(), "Please fill in all password fields.", "warning")
            return

        if new != confirm:
            NotificationToast.show_message(self.window(), "New passwords do not match.", "error")
            return

        if len(new) < 6:
            NotificationToast.show_message(self.window(), "Password must be at least 6 characters.", "warning")
            return

        try:
            self._auth.change_password(self._user.id, old, new)
            NotificationToast.show_message(self.window(), "Password updated successfully!", "success")
            # Clear inputs
            self.old_pass_input.clear()
            self.new_pass_input.clear()
            self.confirm_pass_input.clear()
        except Exception as e:
            logger.exception("Failed to change password")
            NotificationToast.show_message(self.window(), f"Failed to update password: {e}", "error")
