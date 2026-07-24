"""
MediVerse AI — Base Window Component.
Provides a standard frameless window with a custom title bar and theming support.
"""
from __future__ import annotations

import logging
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QMouseEvent, QPainter, QColor, QPainterPath, QLinearGradient, QRadialGradient, QPen
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QApplication
)
import math

logger = logging.getLogger("mediverse.ui.base")


class TitleBar(QWidget):
    """Custom title bar for frameless windows."""
    
    def __init__(self, parent: QWidget, title: str = "") -> None:
        super().__init__(parent)
        self._parent = parent
        self._setup_ui(title)
        
        self._start_pos: QPoint | None = None
        self._is_pressing = False

    def _setup_ui(self, title: str) -> None:
        self.setFixedHeight(40)
        self.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(8)

        # Icon
        self._icon = QLabel("⚕")
        self._icon.setStyleSheet("color: #06b6d4; font-size: 18px; font-weight: bold;")
        layout.addWidget(self._icon)

        # Title
        self._title = QLabel(title)
        self._title.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 700; letter-spacing: 0.5px; font-family: 'Segoe UI';")
        layout.addWidget(self._title)

        layout.addStretch()

        # Window Controls - Premium glassy dots
        self._btn_min = self._create_control_btn("—")
        self._btn_min.clicked.connect(self._parent.showMinimized)
        
        self._btn_max = self._create_control_btn("□")
        self._btn_max.clicked.connect(self._toggle_maximize)
        
        self._btn_close = self._create_control_btn("✕", hover_color="#ef4444")
        self._btn_close.clicked.connect(self._parent.close)

        layout.addWidget(self._btn_min)
        layout.addWidget(self._btn_max)
        layout.addWidget(self._btn_close)

    def _create_control_btn(self, text: str, hover_color: str = "rgba(255,255,255,0.08)") -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(28, 28)
        btn.setStyleSheet(f"""
            QPushButton {{
                color: rgba(255,255,255,0.5);
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 14px;
                font-family: Arial;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {hover_color};
                color: white;
                border: 1px solid rgba(255,255,255,0.15);
            }}
        """)
        return btn

    def _toggle_maximize(self) -> None:
        if self._parent.isMaximized():
            self._parent.showNormal()
        else:
            self._parent.showMaximized()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._is_pressing = True
            self._start_pos = event.globalPosition().toPoint() - self._parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_pressing and self._start_pos is not None:
            if self._parent.isMaximized():
                self._parent.showNormal()
                # Adjust position
                self._start_pos = QPoint(self.width() // 2, event.position().toPoint().y())
            self._parent.move(event.globalPosition().toPoint() - self._start_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._is_pressing = False
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._toggle_maximize()
            event.accept()


class BaseFramelessWindow(QMainWindow):
    """
    Standard frameless window base class with custom title bar and rounded corners.
    Use `set_central_widget` instead of standard `setCentralWidget`.
    """

    def __init__(self, title: str = "MediVerse AI") -> None:
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._root_widget = QWidget()
        self._root_layout = QVBoxLayout(self._root_widget)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)
        
        # Title bar
        self._title_bar = TitleBar(self, title)
        self._root_layout.addWidget(self._title_bar)
        
        # Content area
        self._content_area = QWidget()
        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.addWidget(self._content_area, 1)

        super().setCentralWidget(self._root_widget)
        
        # Drifting glow animation settings
        self._glow_angle = 0.0
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._update_glow)
        self._glow_timer.start(50) # Smooth animation frame updates
        
    def _update_glow(self) -> None:
        self._glow_angle = (self._glow_angle + 0.012) % (2 * math.pi)
        self.update()

    def set_central_widget(self, widget: QWidget) -> None:
        """Set the content of the window (below title bar)."""
        # Clear existing
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._content_layout.addWidget(widget)

    def paintEvent(self, event) -> None:
        """Draw rounded gradient background with animated medical glows."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        if self.isMaximized():
            path.addRect(self.rect())
        else:
            path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)

        painter.setClipPath(path)
        
        # 1. Base deep healthcare gradients background
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor(5, 8, 22))     # #050816
        gradient.setColorAt(0.5, QColor(8, 19, 38))    # #081326
        gradient.setColorAt(1.0, QColor(11, 17, 32))   # #0B1120
        painter.fillPath(path, gradient)
        
        # 2. Moving electric blue glow
        eb_x = self.width() / 2 + (self.width() / 3) * math.cos(self._glow_angle)
        eb_y = self.height() / 2 + (self.height() / 3) * math.sin(self._glow_angle)
        radial_eb = QRadialGradient(eb_x, eb_y, 450)
        radial_eb.setColorAt(0.0, QColor(59, 130, 246, 30))  # electric blue glow
        radial_eb.setColorAt(0.6, QColor(6, 182, 212, 10))   # cyan bleed
        radial_eb.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillPath(path, radial_eb)

        # 3. Opposing violet glow
        v_x = self.width() / 2 - (self.width() / 3.5) * math.cos(self._glow_angle + math.pi / 2)
        v_y = self.height() / 2 - (self.height() / 3.5) * math.sin(self._glow_angle + math.pi / 2)
        radial_v = QRadialGradient(v_x, v_y, 400)
        radial_v.setColorAt(0.0, QColor(139, 92, 246, 20))  # purple accent highlight
        radial_v.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillPath(path, radial_v)
        
        # High-tech window border highlight
        if not self.isMaximized():
            painter.setPen(QPen(QColor(255, 255, 255, 20), 1.2))
            painter.drawPath(path)
        painter.end()
