"""
MediVerse AI — Animated Splash Screen.
Shown for ~3 seconds on application startup while initializing subsystems.
"""
from __future__ import annotations

import sys
from typing import Callable, Optional

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QThread, Signal, QObject, QPointF
)
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter,
    QPainterPath, QPixmap, QRadialGradient
)
from PySide6.QtWidgets import QApplication, QSplashScreen, QLabel, QProgressBar, QWidget, QVBoxLayout


class InitWorker(QObject):
    """Background worker that runs all initialization tasks."""
    progress = Signal(int, str)   # (percent, message)
    finished = Signal(bool, str)  # (success, error_message)

    def __init__(self, init_steps: list[tuple[str, Callable]]) -> None:
        super().__init__()
        self._steps = init_steps

    def run(self) -> None:
        total = len(self._steps)
        for i, (label, fn) in enumerate(self._steps):
            self.progress.emit(int((i / total) * 100), label)
            try:
                fn()
            except Exception as e:
                self.finished.emit(False, str(e))
                return
        self.progress.emit(100, "Ready")
        self.finished.emit(True, "")


class SplashScreen(QWidget):
    """
    Premium animated splash screen with gradient background,
    animated progress bar, and initialization status messages.
    """
    initialization_complete = Signal(bool, str)

    def __init__(self, init_steps: Optional[list[tuple[str, Callable]]] = None) -> None:
        super().__init__()
        self._init_steps = init_steps or []
        self._thread: Optional[QThread] = None
        self._worker: Optional[InitWorker] = None
        self._setup_ui()
        self._setup_animations()

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(680, 420)
        self._center_on_screen()

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 50, 40, 40)
        layout.setSpacing(0)

        # Logo/Icon label
        self._logo_label = QLabel("⚕", self)
        self._logo_label.setAlignment(Qt.AlignCenter)
        self._logo_label.setStyleSheet("font-size: 72px; color: #60a5fa; background: transparent;")
        layout.addWidget(self._logo_label)

        layout.addSpacing(16)

        # App name
        self._title_label = QLabel("MediVerse AI", self)
        self._title_label.setAlignment(Qt.AlignCenter)
        font = QFont("Inter", 32, QFont.Bold)
        self._title_label.setFont(font)
        self._title_label.setStyleSheet(
            "color: white; background: transparent; letter-spacing: 2px;"
        )
        layout.addWidget(self._title_label)

        # Tagline
        self._tagline_label = QLabel(
            "AI-Powered Medical Knowledge Intelligence Platform", self
        )
        self._tagline_label.setAlignment(Qt.AlignCenter)
        self._tagline_label.setStyleSheet(
            "color: rgba(255,255,255,0.65); font-size: 13px; background: transparent;"
        )
        layout.addWidget(self._tagline_label)

        layout.addStretch(1)

        # Status message
        self._status_label = QLabel("Initializing...", self)
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setStyleSheet(
            "color: rgba(255,255,255,0.75); font-size: 12px; background: transparent;"
        )
        layout.addWidget(self._status_label)

        layout.addSpacing(10)

        # Progress bar
        self._progress_bar = QProgressBar(self)
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255,255,255,0.15);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #60a5fa,
                    stop:1 #a78bfa
                );
                border-radius: 2px;
            }
        """)
        layout.addWidget(self._progress_bar)

        layout.addSpacing(12)

        # Version label
        version_label = QLabel("Version 1.0.0  ·  Enterprise Edition", self)
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet(
            "color: rgba(255,255,255,0.35); font-size: 10px; background: transparent;"
        )
        layout.addWidget(version_label)

    def _setup_animations(self) -> None:
        """Fade-in animation on show."""
        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_anim.setDuration(600)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.OutCubic)

    def paintEvent(self, event) -> None:
        """Draw premium gradient background with rounded corners."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Rounded rect path
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 20, 20)
        painter.setClipPath(path)

        # Dark gradient background
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor(13, 17, 35))
        gradient.setColorAt(0.5, QColor(20, 25, 50))
        gradient.setColorAt(1.0, QColor(10, 14, 30))
        painter.fillPath(path, gradient)

        # Subtle radial glow top-center
        radial = QRadialGradient(self.width() / 2, 60, 200)
        radial.setColorAt(0, QColor(96, 165, 250, 40))
        radial.setColorAt(1, QColor(96, 165, 250, 0))
        painter.fillPath(path, radial)

        # Border
        painter.setPen(QColor(255, 255, 255, 25))
        painter.drawPath(path)

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def show_and_initialize(self) -> None:
        """Show splash and start initialization in background thread."""
        self.show()
        self._opacity_anim.start()

        if not self._init_steps:
            QTimer.singleShot(2000, lambda: self.initialization_complete.emit(True, ""))
            return

        self._thread = QThread()
        self._worker = InitWorker(self._init_steps)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)

        self._thread.start()

    def _on_progress(self, percent: int, message: str) -> None:
        self._progress_bar.setValue(percent)
        self._status_label.setText(message)

    def _on_finished(self, success: bool, error: str) -> None:
        if success:
            self._progress_bar.setValue(100)
            self._status_label.setText("Ready — launching workspace...")
            QTimer.singleShot(600, lambda: self.initialization_complete.emit(True, ""))
        else:
            self._status_label.setText(f"Error: {error}")
            QTimer.singleShot(3000, lambda: self.initialization_complete.emit(False, error))
