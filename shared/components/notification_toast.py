"""
MediVerse AI — Notification Toast Component.
Floating non-blocking notifications.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication

from config.constants import TOAST_DURATION_MS


class NotificationToast(QWidget):
    """A floating toast notification that disappears automatically."""

    def __init__(self, parent: QWidget, message: str, type_: str = "info") -> None:
        super().__init__(parent)
        self.message = message
        self.type_ = type_
        self._setup_ui()
        
        # Animations
        self._anim_in = QPropertyAnimation(self, b"windowOpacity")
        self._anim_in.setDuration(300)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)
        self._anim_in.setEasingCurve(QEasingCurve.OutCubic)
        
        self._anim_out = QPropertyAnimation(self, b"windowOpacity")
        self._anim_out.setDuration(300)
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.InCubic)
        self._anim_out.finished.connect(self.deleteLater)
        
        # Timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(TOAST_DURATION_MS)
        self._timer.timeout.connect(self._anim_out.start)

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Icon
        icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
        icon_lbl = QLabel(icons.get(self.type_, "ℹ️"))
        icon_lbl.setStyleSheet("font-size: 16px; background: transparent;")
        layout.addWidget(icon_lbl)
        
        # Message
        msg_lbl = QLabel(self.message)
        msg_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: 500; background: transparent;")
        layout.addWidget(msg_lbl)
        
        self.adjustSize()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 8, 8)
        
        # Colors based on type
        colors = {
            "info": QColor(30, 41, 59, 230),
            "success": QColor(6, 78, 59, 230),
            "warning": QColor(120, 53, 15, 230),
            "error": QColor(127, 29, 29, 230)
        }
        painter.fillPath(path, colors.get(self.type_, colors["info"]))
        
        # Border
        painter.setPen(QColor(255, 255, 255, 30))
        painter.drawPath(path)

    def show_toast(self) -> None:
        # Position at bottom right of parent
        if self.parentWidget():
            parent_rect = self.parentWidget().rect()
            parent_pos = self.parentWidget().mapToGlobal(parent_rect.topLeft())
            x = parent_pos.x() + parent_rect.width() - self.width() - 24
            y = parent_pos.y() + parent_rect.height() - self.height() - 24
            self.move(x, y)
        
        self.show()
        self._anim_in.start()
        self._timer.start()

    @classmethod
    def show_message(cls, parent: QWidget, message: str, type_: str = "info") -> None:
        """Helper to show a toast immediately."""
        toast = cls(parent, message, type_)
        toast.show_toast()
