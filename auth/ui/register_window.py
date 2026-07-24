"""
MediVerse AI — Access Node Creation.
Redesigned with rotating DNA helix illustration, glassmorphic credentials card, and matching system role selectors.
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QCursor, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QFrame, QApplication,
)

from auth.services.auth_service import AuthService, RegisterResult
from core.exceptions import UserAlreadyExistsError
from config.constants import UserRole, ROLE_DISPLAY_NAMES
from shared.components.base_window import BaseFramelessWindow
from auth.ui.login_window import (
    ParticleBackgroundWidget, GlowingLogo, MedicalIllustrationWidget, _InputField
)

logger = logging.getLogger("mediverse.auth.ui.register")


class RegisterWindow(BaseFramelessWindow):
    """Registration form for new user accounts."""
    register_successful = Signal(object, str)   # (User, token)
    navigate_to_login = Signal()

    def __init__(self, auth_service: Optional[AuthService] = None) -> None:
        super().__init__(title="MediVerse AI — Access Node Registry")
        self._auth = auth_service or AuthService()
        self.setMinimumSize(1200, 750)
        self._setup_ui()

    def _setup_ui(self) -> None:
        bg_overlay = ParticleBackgroundWidget(self)
        self.set_central_widget(bg_overlay)

        main_layout = QHBoxLayout(bg_overlay)
        main_layout.setContentsMargins(60, 40, 60, 40)
        main_layout.setSpacing(40)

        # Left panel: Branding and DNA illustration
        left_widget = QWidget()
        left_widget.setStyleSheet("background: transparent;")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(40, 0, 40, 0)
        left_layout.setAlignment(Qt.AlignCenter)

        logo = GlowingLogo()
        left_layout.addWidget(logo, 0, Qt.AlignCenter)
        left_layout.addSpacing(10)

        title = QLabel("MEDIVERSE AI")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            color: white;
            font-size: 36px;
            font-weight: 900;
            letter-spacing: 4px;
            font-family: 'Segoe UI', Arial;
        """)
        left_layout.addWidget(title)

        subtitle = QLabel("CLINICAL AI WORKSPACE & INTELLIGENCE")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            color: #06b6d4;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2px;
        """)
        left_layout.addWidget(subtitle)

        # DNA Illustration
        self.illustration = MedicalIllustrationWidget()
        left_layout.addWidget(self.illustration, 0, Qt.AlignCenter)
        left_layout.addSpacing(10)

        main_layout.addWidget(left_widget, 1)

        # Right panel: Sign Up Card
        right_container = QWidget()
        right_container.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_container)
        right_layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setFixedWidth(460)
        card.setStyleSheet("""
            QFrame {
                background: rgba(8, 12, 28, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
            }
        """)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(32, 32, 32, 32)
        cl.setSpacing(12)

        header = QLabel("Register Access Node")
        header.setStyleSheet("color: white; font-size: 22px; font-weight: 800; border: none; background: transparent;")
        cl.addWidget(header)

        sub_desc = QLabel("Configure credentials for enterprise medical systems")
        sub_desc.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 12px; border: none; background: transparent;")
        cl.addWidget(sub_desc)

        cl.addSpacing(4)

        # Input fields
        self._name_field = _InputField("Full Name", "Dr. Jane Smith", "👤")
        cl.addWidget(self._name_field)

        row = QHBoxLayout()
        self._email_field = _InputField("Email Address", "name@hospital.com", "✉")
        self._username_field = _InputField("Username", "drsmith", "🆔")
        row.addWidget(self._email_field)
        row.addWidget(self._username_field)
        cl.addLayout(row)

        row2 = QHBoxLayout()
        self._pass_field = _InputField("Password", "Min 8 characters", "🔑", password=True)
        self._confirm_field = _InputField("Confirm Password", "Min 8 characters", "🔑", password=True)
        row2.addWidget(self._pass_field)
        row2.addWidget(self._confirm_field)
        cl.addLayout(row2)

        # Role selection
        role_layout = QVBoxLayout()
        role_layout.setSpacing(6)
        role_lbl = QLabel("System Role Assignment")
        role_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-family: 'Segoe UI'; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        role_layout.addWidget(role_lbl)
        
        self._role_combo = QComboBox()
        self._role_combo.setFixedHeight(42)
        self._role_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                color: white; 
                font-size: 13.5px; 
                padding: 0 14px;
            }
            QComboBox::drop-down { 
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid rgba(255, 255, 255, 0.5);
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background: #080c18; 
                color: white;
                selection-background-color: #3b82f6;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
        """)
        for role_val, display in ROLE_DISPLAY_NAMES.items():
            self._role_combo.addItem(display, role_val)
        role_layout.addWidget(self._role_combo)
        cl.addLayout(role_layout)

        # Error text
        self._error_label = QLabel("")
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(
            "color: #ef4444; font-size: 11.5px; border: 1px solid rgba(239, 68, 68, 0.25); "
            "background: rgba(239, 68, 68, 0.08); border-radius: 8px; padding: 10px 14px;"
        )
        self._error_label.hide()
        cl.addWidget(self._error_label)

        # Register button
        self._reg_btn = QPushButton("Register Operator Node")
        self._reg_btn.setFixedHeight(46)
        self._reg_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._reg_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #06b6d4, stop:1 #3b82f6);
                color: white; 
                font-size: 13px; 
                font-weight: bold;
                border: none; 
                border-radius: 10px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0891b2, stop:1 #2563eb);
            }
            QPushButton:disabled { 
                background: rgba(255, 255, 255, 0.08); 
                color: rgba(255, 255, 255, 0.3); 
            }
        """)
        self._reg_btn.clicked.connect(self._do_register)
        cl.addWidget(self._reg_btn)

        # Back link
        back_row = QHBoxLayout()
        back_row.setAlignment(Qt.AlignCenter)
        back_lbl = QLabel("Already possess access credentials?")
        back_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 12px; border: none; background: transparent;")
        back_row.addWidget(back_lbl)
        
        back_btn = QPushButton("Authenticate Connection")
        back_btn.setFlat(True)
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet("color: #06b6d4; font-size: 12px; border: none; background: transparent; font-weight: 700;")
        back_btn.clicked.connect(self.navigate_to_login.emit)
        back_row.addWidget(back_btn)
        cl.addLayout(back_row)

        right_layout.addWidget(card)
        main_layout.addWidget(right_container, 1)

    def _do_register(self) -> None:
        full_name = self._name_field.text.strip()
        email = self._email_field.text.strip()
        username = self._username_field.text.strip()
        password = self._pass_field.text
        confirm = self._confirm_field.text
        role = self._role_combo.currentData()

        if not all([full_name, email, username, password, confirm]):
            self._show_error("All profile fields are parameters required for assignment.")
            return
        if password != confirm:
            self._show_error("Token verification confirm mismatch.")
            self._pass_field.set_error(True)
            self._confirm_field.set_error(True)
            return

        from auth.services.password_service import PasswordService
        is_valid, strength_err = PasswordService.validate_password_strength(password)
        if not is_valid:
            self._show_error(strength_err)
            self._pass_field.set_error(True)
            return

        self._pass_field.set_error(False)
        self._confirm_field.set_error(False)
        self._reg_btn.setEnabled(False)
        self._reg_btn.setText("Generating Secure Access Credentials...")
        self._error_label.hide()
        QApplication.processEvents()

        try:
            result: RegisterResult = self._auth.register(
                email=email, username=username, password=password,
                full_name=full_name, role=role,
            )
            self.register_successful.emit(result.user, result.token)
        except (UserAlreadyExistsError, ValueError) as e:
            self._show_error(str(e))
        except Exception as e:
            self._show_error(f"Registry link failure: {e}")
        finally:
            self._reg_btn.setEnabled(True)
            self._reg_btn.setText("Register Operator Node")

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.show()
