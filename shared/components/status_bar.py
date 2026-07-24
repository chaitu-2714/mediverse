"""
MediVerse AI — Status Bar Component.
Displays system state, database connections, and background task indicators.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from database.connection import check_database_connection
from vector_db.chroma_client import check_chroma_connection


class StatusBar(QWidget):
    """Bottom status bar indicating system health parameters."""

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        
        # Periodic health check
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_health)
        self._timer.start(30000) # Every 30s
        
        # Initial check
        QTimer.singleShot(1000, self._check_health)

    def _setup_ui(self) -> None:
        self.setFixedHeight(28)
        self.setStyleSheet("""
            QWidget {
                background: rgba(5, 8, 22, 0.9);
                border-top: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(15)
        
        self._db_status = QLabel("● POSTGRESQL: CONNECTING")
        self._db_status.setStyleSheet("color: #eab308; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        
        self._ai_status = QLabel("● CHROMADB: CONNECTING")
        self._ai_status.setStyleSheet("color: #eab308; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        
        self._info = QLabel("SYSTEM CORE NODE: ACTIVE // RAG STACK OPERATIONAL")
        self._info.setStyleSheet("color: rgba(255, 255, 255, 0.35); font-family: 'Segoe UI', sans-serif; font-size: 10px; font-weight: 600; letter-spacing: 0.8px; background: transparent; border: none;")
        
        layout.addWidget(self._db_status)
        layout.addWidget(self._ai_status)
        layout.addStretch()
        layout.addWidget(self._info)

    def _check_health(self) -> None:
        """Ping services to update status indicators."""
        db_ok = True
        try:
            check_database_connection()
        except Exception:
            db_ok = False

        chroma_ok = True
        try:
            check_chroma_connection()
        except Exception:
            chroma_ok = False
            
        if db_ok:
            self._db_status.setText("● SQL DATABASE: ONLINE")
            self._db_status.setStyleSheet("color: #10b981; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        else:
            self._db_status.setText("● SQL DATABASE: OFFLINE")
            self._db_status.setStyleSheet("color: #ef4444; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold; background: transparent; border: none;")
            
        if chroma_ok:
            self._ai_status.setText("● VECTOR INDEX: ONLINE")
            self._ai_status.setStyleSheet("color: #06b6d4; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        else:
            self._ai_status.setText("● VECTOR INDEX: OFFLINE")
            self._ai_status.setStyleSheet("color: #ef4444; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold; background: transparent; border: none;")

    def set_custom_status(self, text: str) -> None:
        self._info.setText(text.upper())
