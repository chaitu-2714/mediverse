"""
MediVerse AI — Progress Dialog Component.
Premium modal dialog showing a progress bar and status text.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout
)


class ProgressDialog(QDialog):
    """A styled modal progress dialog."""
    
    canceled = Signal()

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.title_text = title
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 180)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Title
        self._title = QLabel(self.title_text)
        self._title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(self._title)
        
        # Status
        self._status = QLabel("Initializing...")
        self._status.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 13px;")
        layout.addWidget(self._status)
        
        # Progress Bar
        self._progress = QProgressBar()
        self._progress.setFixedHeight(6)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet("""
            QProgressBar {
                background: rgba(255,255,255,0.1);
                border: none; border-radius: 3px;
            }
            QProgressBar::chunk {
                background: #3b82f6; border-radius: 3px;
            }
        """)
        layout.addWidget(self._progress)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05); color: white;
                border: 1px solid rgba(255,255,255,0.1); border-radius: 6px;
                padding: 6px 16px; font-size: 13px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); }
        """)
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)
        
        layout.addLayout(btn_layout)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 12, 12)
        painter.fillPath(path, QColor("#1e2532"))
        painter.setPen(QColor(255, 255, 255, 20))
        painter.drawPath(path)

    def set_progress(self, percent: int, text: str) -> None:
        self._progress.setValue(percent)
        self._status.setText(text)

    def _on_cancel(self) -> None:
        self._status.setText("Canceling...")
        self._cancel_btn.setEnabled(False)
        self.canceled.emit()
