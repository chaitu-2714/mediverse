"""
MediVerse AI — Login Portal.
Redesigned with custom-painted rotating DNA helix illustration, interactive neural mesh, and premium glass components.
"""
from __future__ import annotations

import logging
import random
import math
from typing import Optional, List

from PySide6.QtCore import Qt, Signal, QTimer, QPointF
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath, QCursor,
    QRadialGradient, QPen, QBrush, QIcon, QPixmap
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QCheckBox, QFrame,
    QSizePolicy, QSpacerItem, QApplication, QDialog
)

from auth.services.auth_service import AuthService, LoginResult
from auth.services.oauth_server import LocalOAuthCallbackServer
from shared.components.notification_toast import NotificationToast
from core.exceptions import InvalidCredentialsError, AccountDeactivatedError
from core.models.user import User
from shared.components.base_window import BaseFramelessWindow
from typing import Callable

logger = logging.getLogger("mediverse.auth.ui")


GOOGLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="16px" height="16px">
  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
  <path fill="#4285F4" d="M46.5 24c0-1.61-.15-3.16-.42-4.69H24v8.89h12.64c-.55 2.92-2.19 5.39-4.67 7.05l7.27 5.64C43.5 36.31 46.5 30.73 46.5 24z"/>
  <path fill="#FBBC05" d="M10.54 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.98-6.19z"/>
  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.27-5.64c-2.21 1.48-5.02 2.37-8.62 2.37-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
</svg>"""

APPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 170" width="16px" height="16px" fill="#FFFFFF">
  <path d="M150.37 130.25c-2.45 5.66-5.35 10.87-8.71 15.66-4.58 6.53-8.33 11.05-11.22 13.56-4.48 4.12-9.28 6.23-14.42 6.35-3.69 0-8.14-1.05-13.32-3.18-5.19-2.12-9.97-3.17-14.34-3.17-4.58 0-9.49 1.05-14.75 3.17-5.26 2.13-9.5 3.24-12.74 3.35-4.34.13-9.13-1.92-14.37-6.15-2.89-2.41-6.66-6.93-11.31-13.56-5.82-8.34-10.63-18.06-14.43-29.17-3.8-11.12-5.7-22.13-5.7-33.05 0-20.3 5.42-35.68 16.27-46.12 7.78-7.53 17.06-11.37 27.85-11.51 4.58 0 9.8 1.25 15.66 3.76 5.86 2.5 9.53 3.76 11.01 3.76 1.48 0 5.43-1.39 11.83-4.18 6.4-2.8 11.57-4.04 15.52-3.76 12.01.27 21.61 4.54 28.79 12.82-11.2 6.78-16.73 16.14-16.6 28.09.13 9.4 3.73 17.39 10.8 23.95 7.07 6.56 15.5 10.05 25.31 10.46-2.12 6.27-5.12 12.77-9.01 19.5zM119.22 31.95c0-7.72 2.76-14.88 8.27-21.49 5.51-6.61 12.39-10.45 20.62-10.46.13.8.2-1.57-.22 2.37-1.12 10.05-5.63 18.57-13.54 25.56-7.91 6.99-16.59 10.5-26.06 10.5-.32-1.5-.13-3.69-.13-6.48z"/>
</svg>"""

def create_icon_from_svg(svg_str: str) -> QIcon:
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtGui import QPixmap, QPainter, QIcon
    from PySide6.QtCore import Qt
    
    renderer = QSvgRenderer(svg_str.encode('utf-8'))
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    
    return QIcon(pixmap)


class Particle:
    """Represents a single particle in the interactive network background."""
    def __init__(self, width: int, height: int):
        self.x = random.uniform(0, width)
        self.y = random.uniform(0, height)
        self.vx = random.uniform(-0.4, 0.4)
        self.vy = random.uniform(-0.4, 0.4)
        self.radius = random.uniform(1.2, 3.5)
        self.color = QColor(6, 182, 212, random.randint(40, 140)) # Cyan glow spectrum

    def update(self, width: int, height: int):
        self.x += self.vx
        self.y += self.vy

        if self.x < 0 or self.x > width:
            self.vx *= -1
        if self.y < 0 or self.y > height:
            self.vy *= -1


class ParticleBackgroundWidget(QWidget):
    """Dynamic neural network particle system background."""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.particles: List[Particle] = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_particles)
        self.timer.start(25) # ~40fps
        
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.particles = [Particle(self.width(), self.height()) for _ in range(65)]

    def _update_particles(self) -> None:
        for p in self.particles:
            p.update(self.width(), self.height())
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0.0, QColor(4, 6, 15))
        gradient.setColorAt(0.5, QColor(8, 14, 28))
        gradient.setColorAt(1.0, QColor(3, 4, 8))
        painter.fillRect(rect, gradient)

        # Ambient glows (Electric blue & Purple)
        glow_radial = QRadialGradient(rect.width() * 0.15, rect.height() * 0.25, 650)
        glow_radial.setColorAt(0.0, QColor(59, 130, 246, 32))
        glow_radial.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(rect, glow_radial)

        glow_radial2 = QRadialGradient(rect.width() * 0.85, rect.height() * 0.75, 550)
        glow_radial2.setColorAt(0.0, QColor(139, 92, 246, 22))
        glow_radial2.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(rect, glow_radial2)

        # Draw connections
        pen = QPen()
        for i in range(len(self.particles)):
            p1 = self.particles[i]
            for j in range(i + 1, len(self.particles)):
                p2 = self.particles[j]
                dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
                if dist < 120:
                    alpha = int((1.0 - (dist / 120)) * 50)
                    pen.setColor(QColor(6, 182, 212, alpha))
                    pen.setWidthF(0.8)
                    painter.setPen(pen)
                    painter.drawLine(QPointF(p1.x, p1.y), QPointF(p2.x, p2.y))

        # Draw particles
        painter.setPen(Qt.NoPen)
        for p in self.particles:
            painter.setBrush(QBrush(p.color))
            painter.drawEllipse(QPointF(p.x, p.y), p.radius, p.radius)
        painter.end()


class GlowingLogo(QWidget):
    """Futuristic glowing medical AI emblem widget."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(100, 100)
        self._pulse = 0.0
        self._dir = 1
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_glow)
        self._timer.start(35)

    def _update_glow(self) -> None:
        self._pulse += 0.04 * self._dir
        if self._pulse > 1.0:
            self._pulse = 1.0
            self._dir = -1
        elif self._pulse < 0.0:
            self._pulse = 0.0
            self._dir = 1
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = self.rect().center()
        radius = 28 + int(self._pulse * 4)

        # Pulse outer glowing aura
        glow_rad = QRadialGradient(center.x(), center.y(), radius + 15)
        glow_rad.setColorAt(0.0, QColor(6, 182, 212, 100))
        glow_rad.setColorAt(0.6, QColor(99, 102, 241, 25))
        glow_rad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_rad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, radius + 20, radius + 20)

        # Inner tech ring
        pen = QPen(QColor(6, 182, 212, 220))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, 24, 24)

        # Cross structure in core
        cross_path = QPainterPath()
        cw, ch = 6, 18
        cross_path.addRoundedRect(center.x() - cw/2, center.y() - ch/2, cw, ch, 2, 2)
        cross_path.addRoundedRect(center.x() - ch/2, center.y() - cw/2, ch, cw, 2, 2)
        
        cross_grad = QLinearGradient(0, center.y() - 10, 0, center.y() + 10)
        cross_grad.setColorAt(0.0, QColor(59, 130, 246))
        cross_grad.setColorAt(1.0, QColor(139, 92, 246))
        painter.fillPath(cross_path, cross_grad)
        painter.end()


class MedicalIllustrationWidget(QWidget):
    """Pulsing, rotating medical AI double helix structure representing DNA/neural mesh."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(300, 300)
        self.angle = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        self.timer.start(25)

    def _rotate(self) -> None:
        self.angle = (self.angle + 0.035) % (2 * math.pi)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        cx, cy = rect.center().x(), rect.center().y()
        
        # Grid layout
        painter.setPen(QPen(QColor(6, 182, 212, 12), 1, Qt.DashLine))
        painter.drawEllipse(QPointF(cx, cy), 110, 110)
        painter.drawEllipse(QPointF(cx, cy), 70, 70)
        
        # Paint double helix sine nodes
        points_a = []
        points_b = []
        num_nodes = 14
        
        for i in range(num_nodes):
            t = i / (num_nodes - 1)
            y = cy - 100 + t * 200
            
            rot_val = self.angle + t * math.pi * 2.5
            x_a = cx + 55 * math.sin(rot_val)
            x_b = cx - 55 * math.sin(rot_val)
            
            z_a = math.cos(rot_val)
            z_b = -math.cos(rot_val)
            
            points_a.append((x_a, y, z_a))
            points_b.append((x_b, y, z_b))
            
        # Draw connections
        for i in range(num_nodes):
            xa, ya, za = points_a[i]
            xb, yb, zb = points_b[i]
            
            avg_z = (za + zb) / 2.0
            alpha = int(120 + 80 * avg_z)
            
            painter.setPen(QPen(QColor(99, 102, 241, alpha), 1.5))
            painter.drawLine(QPointF(xa, ya), QPointF(xb, yb))
            
        # Draw node capsules
        for i in range(num_nodes):
            xa, ya, za = points_a[i]
            xb, yb, zb = points_b[i]
            
            r_a = 4.0 + 2.0 * za
            alpha_a = int(180 + 75 * za)
            painter.setBrush(QBrush(QColor(6, 182, 212, alpha_a)))
            painter.setPen(QPen(QColor(255, 255, 255, alpha_a), 1))
            painter.drawEllipse(QPointF(xa, ya), r_a, r_a)
            
            r_b = 4.0 + 2.0 * zb
            alpha_b = int(180 + 75 * zb)
            painter.setBrush(QBrush(QColor(139, 92, 246, alpha_b)))
            painter.setPen(QPen(QColor(255, 255, 255, alpha_b), 1))
            painter.drawEllipse(QPointF(xb, yb), r_b, r_b)
        painter.end()


class _InputField(QWidget):
    """Glassmorphic input field with active border highlighting and visibility options."""

    def __init__(
        self,
        label: str,
        placeholder: str,
        icon: str = "",
        password: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._password = password
        self._is_visible = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(f"{icon}  {label}" if icon else label)
        lbl.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-family: 'Segoe UI'; font-size: 11px; font-weight: 700; background: transparent;")
        layout.addWidget(lbl)

        field_container = QFrame()
        field_container.setFixedHeight(44)
        field_container.setObjectName("container")
        self._set_container_style(field_container, False)
        
        f_layout = QHBoxLayout(field_container)
        f_layout.setContentsMargins(12, 0, 12, 0)
        f_layout.setSpacing(8)

        self.field = QLineEdit()
        self.field.setPlaceholderText(placeholder)
        if password:
            self.field.setEchoMode(QLineEdit.Password)
        self.field.setStyleSheet("QLineEdit { background: transparent; border: none; color: white; font-size: 13.5px; }")
        self.field.focusInEvent = lambda e: (self._set_container_style(field_container, True), QLineEdit.focusInEvent(self.field, e))
        self.field.focusOutEvent = lambda e: (self._set_container_style(field_container, False), QLineEdit.focusOutEvent(self.field, e))
        f_layout.addWidget(self.field, 1)

        if password:
            self.toggle_btn = QPushButton("👁️")
            self.toggle_btn.setFixedSize(26, 26)
            self.toggle_btn.setCursor(Qt.PointingHandCursor)
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: rgba(255,255,255,0.4);
                    font-size: 14px;
                    border: none;
                }
                QPushButton:hover {
                    color: white;
                }
            """)
            self.toggle_btn.clicked.connect(self._toggle_visibility)
            f_layout.addWidget(self.toggle_btn)

        layout.addWidget(field_container)

    def _set_container_style(self, w: QFrame, has_focus: bool, has_error: bool = False) -> None:
        if has_error:
            border = "1.5px solid #ef4444"
            bg = "rgba(239, 68, 68, 0.06)"
        elif has_focus:
            border = "1.5px solid #06b6d4"
            bg = "rgba(6, 182, 212, 0.08)"
        else:
            border = "1px solid rgba(255, 255, 255, 0.12)"
            bg = "rgba(255, 255, 255, 0.03)"
            
        w.setStyleSheet(f"QFrame#container {{ background: {bg}; border: {border}; border-radius: 10px; }}")

    def _toggle_visibility(self) -> None:
        self._is_visible = not self._is_visible
        if self._is_visible:
            self.field.setEchoMode(QLineEdit.Normal)
            self.toggle_btn.setText("🙈")
        else:
            self.field.setEchoMode(QLineEdit.Password)
            self.toggle_btn.setText("👁️")

    @property
    def text(self) -> str:
        return self.field.text()

    def set_error(self, has_error: bool) -> None:
        container = self.findChild(QFrame, "container")
        if container:
            self._set_container_style(container, False, has_error)


class ForgotPasswordDialog(QDialog):
    """Futuristic password reset request dialog."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.email = ""
        self.success = False
        
        self.setFixedSize(380, 200)
        self.setStyleSheet("""
            QDialog {
                background: rgba(8, 12, 28, 0.98);
                border: 2px solid rgba(6, 182, 212, 0.4);
                border-radius: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        
        title = QLabel("Reset Security Token")
        title.setStyleSheet("color: white; font-family: 'Segoe UI'; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(title)
        
        desc = QLabel("Enter your account email to receive a secure password reset link.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: rgba(255,255,255,0.5); font-family: 'Segoe UI'; font-size: 11px; border: none; background: transparent;")
        layout.addWidget(desc)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email address")
        self.email_input.setFixedHeight(36)
        self.email_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                color: white;
                padding: 0 10px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #06b6d4; }
        """)
        layout.addWidget(self.email_input)
        
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.04); color: white; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; height: 32px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.08); }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_send = QPushButton("Send Reset Link")
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06b6d4, stop:1 #3b82f6); color: white; border: none; border-radius: 6px; height: 32px; font-weight: bold;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0891b2, stop:1 #2563eb); }
        """)
        self.btn_send.clicked.connect(self.do_send)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_send)
        layout.addLayout(btn_layout)

    def do_send(self) -> None:
        self.email = self.email_input.text().strip()
        if self.email:
            self.success = True
            self.accept()


class OAuthLoadingOverlay(QFrame):
    """Semi-transparent glass overlay showing rotating neural loading state during browser OAuth sign-in."""
    def __init__(self, parent_card: QWidget, on_cancel: Callable) -> None:
        super().__init__(parent_card)
        self.on_cancel = on_cancel
        self.setObjectName("sso_loader")
        self.setGeometry(parent_card.rect())
        self.setStyleSheet("""
            QFrame#sso_loader {
                background: rgba(8, 12, 28, 0.95);
                border: 1px solid rgba(6, 182, 212, 0.3);
                border-radius: 20px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        self.spinner = QLabel("⚡")
        self.spinner.setAlignment(Qt.AlignCenter)
        self.spinner.setStyleSheet("font-size: 38px; color: #06b6d4;")
        layout.addWidget(self.spinner)
        
        self.pulse_timer = QTimer(self)
        self.pulse_angle = 0
        self.pulse_timer.timeout.connect(self._rotate_spinner)
        self.pulse_timer.start(50)
        
        title = QLabel("Establishing SSO Authentication Link")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: white; font-family: 'Segoe UI'; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)
        
        desc = QLabel("We have launched a secure login window in your default browser. Select your credentials to authorize this operator session.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: rgba(255, 255, 255, 0.55); font-family: 'Segoe UI'; font-size: 11.5px; line-height: 1.5;")
        layout.addWidget(desc)
        
        cancel_btn = QPushButton("Cancel Authentication")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(34)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                color: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.15);
                color: white;
                border-color: rgba(239, 68, 68, 0.35);
            }
        """)
        cancel_btn.clicked.connect(self.on_cancel)
        layout.addWidget(cancel_btn)

    def _rotate_spinner(self) -> None:
        self.pulse_angle = (self.pulse_angle + 15) % 360
        chars = ["⚡", "🧬", "🧠", "🌀", "⚙️", "🌐"]
        self.spinner.setText(chars[(self.pulse_angle // 60) % len(chars)])
        
    def closeEvent(self, event) -> None:
        self.pulse_timer.stop()
        super().closeEvent(event)


class LoginWindow(BaseFramelessWindow):
    """
    Glassmorphic login window with interactive neural network background.
    """
    login_successful = Signal(object, str)   # (User, token)
    navigate_to_register = Signal()
    navigate_to_forgot_password = Signal()
    sso_completed = Signal(str, dict)        # (provider, data)

    def __init__(self, auth_service: Optional[AuthService] = None) -> None:
        super().__init__(title="MediVerse AI — Access Validation Portal")
        self._auth = auth_service or AuthService()
        self.oauth_server: Optional[LocalOAuthCallbackServer] = None
        self._oauth_overlay: Optional[OAuthLoadingOverlay] = None
        self.sso_completed.connect(self._complete_sso)
        self.setMinimumSize(1200, 750)
        self._setup_ui()

    def _setup_ui(self) -> None:
        bg_overlay = ParticleBackgroundWidget(self)
        self.set_central_widget(bg_overlay)
        
        main_layout = QHBoxLayout(bg_overlay)
        main_layout.setContentsMargins(60, 40, 60, 40)
        main_layout.setSpacing(40)

        # Left panel: Branding and Rotating DNA Illustration
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

        # Pulsing sine helix DNA illustration
        self.illustration = MedicalIllustrationWidget()
        left_layout.addWidget(self.illustration, 0, Qt.AlignCenter)
        left_layout.addSpacing(10)

        main_layout.addWidget(left_widget, 1)

        # Right panel: Floating Glassmorphic Login Card
        right_container = QWidget()
        right_container.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_container)
        right_layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        self._card = card
        card.setFixedWidth(440)
        card.setStyleSheet("""
            QFrame {
                background: rgba(8, 12, 28, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 40, 36, 40)
        card_layout.setSpacing(18)

        welcome = QLabel("Initialize Operator Node")
        welcome.setStyleSheet("color: white; font-size: 22px; font-weight: 800; border: none; background: transparent;")
        card_layout.addWidget(welcome)

        info_lbl = QLabel("Establish communication via verified credentials")
        info_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 12px; border: none; background: transparent;")
        card_layout.addWidget(info_lbl)

        card_layout.addSpacing(8)

        # Primary SSO Buttons
        self._google_btn = QPushButton(" Continue with Google")
        self._google_btn.setFixedHeight(40)
        self._google_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._google_btn.setIcon(create_icon_from_svg(GOOGLE_SVG))
        self._google_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: rgba(255,255,255,0.85);
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(66, 133, 244, 0.35);
                color: white;
            }
        """)
        self._google_btn.clicked.connect(self._do_google_sso)

        self._apple_btn = QPushButton(" Continue with Apple")
        self._apple_btn.setFixedHeight(40)
        self._apple_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._apple_btn.setIcon(create_icon_from_svg(APPLE_SVG))
        self._apple_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: rgba(255,255,255,0.85);
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.25);
                color: white;
            }
        """)
        self._apple_btn.clicked.connect(self._do_apple_sso)

        sso_layout = QHBoxLayout()
        sso_layout.setSpacing(10)
        sso_layout.addWidget(self._google_btn, 1)
        sso_layout.addWidget(self._apple_btn, 1)
        card_layout.addLayout(sso_layout)

        # Divider Section
        divider_layout = QHBoxLayout()
        line1 = QFrame()
        line1.setFixedHeight(1)
        line1.setStyleSheet("background: rgba(255, 255, 255, 0.08); border: none;")
        div_lbl = QLabel("OR CONNECT WITH SECURITY CREDENTIALS")
        div_lbl.setStyleSheet("color: rgba(255,255,255,0.35); font-family: 'Segoe UI'; font-size: 8.5px; font-weight: bold; letter-spacing: 0.5px; border: none; background: transparent;")
        div_lbl.setAlignment(Qt.AlignCenter)
        line2 = QFrame()
        line2.setFixedHeight(1)
        line2.setStyleSheet("background: rgba(255, 255, 255, 0.08); border: none;")
        
        divider_layout.addWidget(line1, 1)
        divider_layout.addWidget(div_lbl)
        divider_layout.addWidget(line2, 1)
        card_layout.addLayout(divider_layout)

        # Email/User Input
        self._email_field = _InputField("Portal Identity (Email)", "name@hospital.com", "✉")
        card_layout.addWidget(self._email_field)

        # Password Input
        self._pass_field = _InputField("Security Token (Password)", "••••••••", "🔑", password=True)
        card_layout.addWidget(self._pass_field)

        # Remember Session & Forgot Button
        row = QHBoxLayout()
        self._remember = QCheckBox("Save Session State")
        self._remember.setStyleSheet(
            "color: rgba(255, 255, 255, 0.5); font-size: 11px; border: none; background: transparent;"
        )
        row.addWidget(self._remember)
        row.addStretch()
        
        forgot = QPushButton("Forgot Security Token?")
        forgot.setCursor(QCursor(Qt.PointingHandCursor))
        forgot.setFlat(True)
        forgot.setStyleSheet("color: #06b6d4; font-size: 11px; border: none; background: transparent; font-weight: bold;")
        forgot.clicked.connect(self._handle_forgot_password)
        row.addWidget(forgot)
        card_layout.addLayout(row)

        # Errors
        self._error_label = QLabel("")
        self._error_label.setStyleSheet(
            "color: #ef4444; font-size: 11.5px; border: 1px solid rgba(239, 68, 68, 0.25); "
            "background: rgba(239, 68, 68, 0.08); border-radius: 8px; padding: 10px 14px;"
        )
        self._error_label.hide()
        self._error_label.setWordWrap(True)
        card_layout.addWidget(self._error_label)

        # Connect button
        self._login_btn = QPushButton("Establish Portal Access")
        self._login_btn.setFixedHeight(46)
        self._login_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #7c3aed);
            }
            QPushButton:disabled {
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.3);
            }
        """)
        self._login_btn.clicked.connect(self._do_login)
        card_layout.addWidget(self._login_btn)

        self._pass_field.field.returnPressed.connect(self._do_login)
        self._email_field.field.returnPressed.connect(self._pass_field.field.setFocus)

        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: rgba(255, 255, 255, 0.08); border: none;")
        card_layout.addWidget(divider)

        # Sign Up
        signUp_row = QHBoxLayout()
        signUp_row.setAlignment(Qt.AlignCenter)
        signUp_lbl = QLabel("New system operator?")
        signUp_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 12px; border: none; background: transparent;")
        signUp_row.addWidget(signUp_lbl)
        
        signUp_btn = QPushButton("Create Node Node")
        signUp_btn.setText("Configure Access Node")
        signUp_btn.setFlat(True)
        signUp_btn.setCursor(QCursor(Qt.PointingHandCursor))
        signUp_btn.setStyleSheet("color: #06b6d4; font-size: 12px; border: none; background: transparent; font-weight: 700;")
        signUp_btn.clicked.connect(self.navigate_to_register.emit)
        signUp_row.addWidget(signUp_btn)
        card_layout.addLayout(signUp_row)

        right_layout.addWidget(card)
        main_layout.addWidget(right_container, 1)

    def _do_login(self) -> None:
        """Validate inputs and attempt login."""
        email = self._email_field.text.strip()
        password = self._pass_field.text

        if not email or not password:
            self._show_error("All credentials parameters are required.")
            self._email_field.set_error(not email)
            self._pass_field.set_error(not password)
            return

        self._email_field.set_error(False)
        self._pass_field.set_error(False)
        self._login_btn.setEnabled(False)
        self._login_btn.setText("Establishing Security Node Link...")
        self._error_label.hide()
        QApplication.processEvents()

        try:
            result: LoginResult = self._auth.login(email, password)
            if self._remember.isChecked():
                self._auth.save_session(result.token, "dummy-refresh-token", str(result.user.id), result.user.email)
            self.login_successful.emit(result.user, result.token)
        except (InvalidCredentialsError, AccountDeactivatedError, ValueError) as e:
            self._show_error(str(e))
            self._email_field.set_error(True)
            self._pass_field.set_error(True)
        except Exception as e:
            self._show_error(f"Validation anomaly: {e}")
        finally:
            self._login_btn.setEnabled(True)
            self._login_btn.setText("Establish Portal Access")

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.show()

    def _do_google_sso(self) -> None:
        self._run_sso_flow("Google")

    def _do_apple_sso(self) -> None:
        self._run_sso_flow("Apple")

    def _run_sso_flow(self, provider: str) -> None:
        self._error_label.hide()
        
        # Check if SSO is configured — if not, open the setup wizard
        from auth.services.env_validator import get_missing_vars
        missing = get_missing_vars()
        if missing:
            logger.warning(f"SSO missing env vars: {missing}")
            self._open_setup_wizard()
            return
        
        # 1. Start OAuth local redirect server
        self.oauth_server = LocalOAuthCallbackServer()
        
        # 2. Show the loading overlay
        self._oauth_overlay = OAuthLoadingOverlay(self._card, self._cancel_oauth)
        self._oauth_overlay.show()
        
        # Callback on success
        def sso_success_callback(data):
            self.sso_completed.emit(provider, data)
            
        try:
            self.oauth_server.start(sso_success_callback)
            # 3. Launch system browser proxy signin flow
            self.oauth_server.open_browser(provider)
        except Exception as e:
            logger.error(f"OAuth launch failed: {e}")
            self._cancel_oauth()
            self._show_error(f"Failed to start OAuth: {e}")

    def _open_setup_wizard(self) -> None:
        """Open the setup wizard to configure missing SSO credentials."""
        try:
            from auth.ui.setup_wizard_window import SetupWizardWindow
            self._wizard = SetupWizardWindow()
            
            def on_config_done():
                self._wizard = None
                NotificationToast.show_message(self, "Configuration saved! You can now sign in with Google.", "success")
                
            self._wizard.configuration_completed.connect(on_config_done)
            self._wizard.show()
        except Exception as e:
            self._show_error(
                f"Google/Apple sign-in requires Supabase and OAuth configuration.\n"
                f"Please launch the Setup Wizard or create a .env file with your credentials."
            )

    def _complete_sso(self, provider: str, data: dict) -> None:
        # Clean up UI
        if self._oauth_overlay:
            self._oauth_overlay.deleteLater()
            self._oauth_overlay = None
            
        if self.oauth_server:
            self.oauth_server.stop()
            self.oauth_server = None
            
        self._login_btn.setEnabled(False)
        self._login_btn.setText("Establishing Security Node Link...")
        QApplication.processEvents()

        try:
            # Map SSO return dictionary into domain User entity
            from core.models.user import User
            from config.constants import UserRole
            from uuid import UUID
            
            user = User(
                id=UUID(data["uid"]),
                email=data["email"],
                username=data["username"],
                full_name=data["name"],
                role=UserRole(data["role"]),
                is_active=True,
                is_verified=True,
                avatar_url=None,
                auth_provider=provider.lower(),
                is_onboarded=data["is_onboarded"],
                login_count=1,
                created_at=None,
                last_login=None
            )
            
            token = data["token"]
            
            # Save session if requested
            if self._remember.isChecked():
                self._auth.save_session(token, data["refresh_token"], str(user.id), user.email)
                
            NotificationToast.show_message(self.window(), f"Successfully linked {provider} account!", "success")
            self.login_successful.emit(user, token)
        except Exception as e:
            self._show_error(f"{provider} handshaking exception: {e}")
        finally:
            self._login_btn.setEnabled(True)
            self._login_btn.setText("Establish Portal Access")

    def _cancel_oauth(self) -> None:
        if self._oauth_overlay:
            self._oauth_overlay.deleteLater()
            self._oauth_overlay = None
            
        if self.oauth_server:
            self.oauth_server.stop()
            self.oauth_server = None
            
        self._show_error("Authentication process canceled by operator.")

    def _handle_forgot_password(self) -> None:
        dialog = ForgotPasswordDialog(self)
        if dialog.exec() == QDialog.Accepted and dialog.success:
            try:
                self._auth.send_password_reset(dialog.email)
                NotificationToast.show_message(self, "Security token reset link has been dispatched.", "success")
            except Exception as e:
                self._show_error(f"Reset failed: {e}")
