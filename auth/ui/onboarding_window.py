"""
MediVerse AI — Operator Onboarding & Role Selection Portal.
Glassmorphic, VisionOS-inspired role selector card grid.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QApplication
)

from config.constants import UserRole
from auth.services.auth_service import AuthService
from shared.components.base_window import BaseFramelessWindow
from auth.ui.login_window import ParticleBackgroundWidget, GlowingLogo

logger = logging.getLogger("mediverse.auth.ui.onboarding")


class RoleSelectionCard(QFrame):
    """A glassmorphic selection card for a user role."""
    clicked = Signal(str)

    def __init__(self, role_id: str, title: str, description: str, icon: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.role_id = role_id
        self.selected = False
        
        self.setFixedHeight(180)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)
        
        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setStyleSheet("font-size: 32px; background: transparent; border: none;")
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_lbl)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("color: white; font-size: 15px; font-weight: bold; background: transparent; border: none;")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_lbl)
        
        self.desc_lbl = QLabel(description)
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setAlignment(Qt.AlignCenter)
        self.desc_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 11px; line-height: 1.4; background: transparent; border: none;")
        layout.addWidget(self.desc_lbl)
        
        self.update_style()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.role_id)
        super().mousePressEvent(event)

    def set_selected(self, is_selected: bool) -> None:
        self.selected = is_selected
        self.update_style()

    def update_style(self) -> None:
        if self.selected:
            self.setStyleSheet("""
                QFrame {
                    background: rgba(6, 182, 212, 0.12);
                    border: 2px solid #06b6d4;
                    border-radius: 16px;
                }
            """)
            self.title_lbl.setStyleSheet("color: #06b6d4; font-size: 15px; font-weight: bold; background: transparent; border: none;")
        else:
            self.setStyleSheet("""
                QFrame {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 16px;
                }
                QFrame:hover {
                    background: rgba(255, 255, 255, 0.06);
                    border: 1px solid rgba(255, 255, 255, 0.16);
                }
            """)
            self.title_lbl.setStyleSheet("color: white; font-size: 15px; font-weight: bold; background: transparent; border: none;")


class OnboardingWindow(BaseFramelessWindow):
    """One-time role onboarding selection portal."""
    onboarding_completed = Signal(object) # Emit the updated User object

    def __init__(self, user_id: UUID, auth_service: Optional[AuthService] = None) -> None:
        super().__init__(title="MediVerse AI — Operator Assignment Portal")
        self.user_id = user_id
        self._auth = auth_service or AuthService()
        self.selected_role: Optional[str] = None
        
        self.setMinimumSize(950, 600)
        self._setup_ui()

    def _setup_ui(self) -> None:
        bg_overlay = ParticleBackgroundWidget(self)
        self.set_central_widget(bg_overlay)
        
        layout = QVBoxLayout(bg_overlay)
        layout.setContentsMargins(50, 40, 50, 40)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignCenter)
        
        logo = GlowingLogo()
        layout.addWidget(logo, 0, Qt.AlignCenter)
        
        title = QLabel("Select Operator Credentials Role")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: white; font-size: 24px; font-weight: 800;")
        layout.addWidget(title)
        
        subtitle = QLabel("Please configure your system clearance role. Your assignment determines available diagnostic systems and analytical tools.")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 12px; max-width: 600px;")
        layout.addWidget(subtitle)
        
        card_grid_widget = QWidget()
        card_grid_widget.setStyleSheet("background: transparent; border: none;")
        card_grid = QHBoxLayout(card_grid_widget)
        card_grid.setSpacing(20)
        
        # Cards definition (predefining normal non-admin roles)
        self.card_doctor = RoleSelectionCard(
            UserRole.DOCTOR, "Doctor",
            "Access full diagnostic PACS scanners, write analysis reports, and invoke RAG intelligence lookups.",
            "👩‍⚕️", self
        )
        self.card_researcher = RoleSelectionCard(
            UserRole.RESEARCHER, "Researcher",
            "Process medical documents, run NLP entity extractions, index custom clinical logs, and view analysis portals.",
            "🔬", self
        )
        self.card_student = RoleSelectionCard(
            UserRole.MEDICAL_STUDENT, "Medical Student",
            "Browse indexed clinical documentation databases, inspect analysis reports, and interact with educational decision support models.",
            "📚", self
        )
        
        card_grid.addWidget(self.card_doctor)
        card_grid.addWidget(self.card_researcher)
        card_grid.addWidget(self.card_student)
        layout.addWidget(card_grid_widget)
        
        # Connect signals
        self.card_doctor.clicked.connect(self._select_role)
        self.card_researcher.clicked.connect(self._select_role)
        self.card_student.clicked.connect(self._select_role)
        
        self.btn_confirm = QPushButton("Assign System Role")
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.setFixedHeight(48)
        self.btn_confirm.setFixedWidth(280)
        self.btn_confirm.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                font-size: 13.5px;
                font-weight: bold;
            }
            QPushButton:enabled {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06b6d4, stop:1 #3b82f6);
                color: white;
                border: none;
            }
            QPushButton:enabled:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0891b2, stop:1 #2563eb);
            }
        """)
        self.btn_confirm.clicked.connect(self._confirm_role)
        layout.addWidget(self.btn_confirm, 0, Qt.AlignCenter)

    def _select_role(self, role_id: str) -> None:
        self.selected_role = role_id
        self.card_doctor.set_selected(role_id == UserRole.DOCTOR)
        self.card_researcher.set_selected(role_id == UserRole.RESEARCHER)
        self.card_student.set_selected(role_id == UserRole.MEDICAL_STUDENT)
        self.btn_confirm.setEnabled(True)

    def _confirm_role(self) -> None:
        if not self.selected_role:
            return
            
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.setText("Configuring Operators Node...")
        QApplication.processEvents()
        
        try:
            # Complete operator configuration
            updated_user = self._auth.complete_onboarding(self.user_id, self.selected_role)
            self.onboarding_completed.emit(updated_user)
        except Exception as e:
            logger.error(f"Onboarding confirmation exception: {e}")
            self.btn_confirm.setEnabled(True)
            self.btn_confirm.setText("Assign System Role")
