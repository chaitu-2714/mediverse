"""
MediVerse AI — Upload & Automatic Detection Dialog Component.
Modal dialog with animated diagnostic checks showing auto-classification of medical files.
"""
from __future__ import annotations

import os
from typing import Optional, Any
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QFont, QPen, QBrush
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QFrame
)

from ai_core.engines.detection_engine import MedicalFileDetectionEngine

class UploadDetectionDialog(QDialog):
    """
    A premium dark glassmorphic dialog that auto-detects medical files
    and runs the animated pipeline check sequence.
    """
    
    detection_complete = Signal(dict)

    def __init__(self, file_path: str, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.file_path = file_path
        self.detected_data = {}
        self.animation_step = 0
        self._setup_ui()
        self._start_detection_simulation()

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(460, 340)
        self.setModal(True)

        # Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 28, 28, 28)
        self.main_layout.setSpacing(14)

        # Header Title
        self.title_lbl = QLabel("AUTOMATIC MEDICAL FILE DETECTION")
        self.title_lbl.setStyleSheet("color: white; font-size: 14px; font-weight: 800; letter-spacing: 0.5px; border: none; background: transparent;")
        self.main_layout.addWidget(self.title_lbl)

        # Active File name
        fn = os.path.basename(self.file_path)
        self.fn_lbl = QLabel(f"Ingesting: {fn}")
        self.fn_lbl.setWordWrap(True)
        self.fn_lbl.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 11px; border: none; background: transparent;")
        self.main_layout.addWidget(self.fn_lbl)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(8)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.04);
                border: none; border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06b6d4, stop:1 #3b82f6);
                border-radius: 4px;
            }
        """)
        self.main_layout.addWidget(self.progress)

        # Steps Area
        self.steps_frame = QFrame()
        self.steps_frame.setStyleSheet("background: rgba(0,0,0,0.15); border: 1px solid rgba(255,255,255,0.03); border-radius: 10px;")
        self.steps_layout = QVBoxLayout(self.steps_frame)
        self.steps_layout.setContentsMargins(15, 12, 15, 12)
        self.steps_layout.setSpacing(8)

        self.step_msgs = [
            "Analyzing uploaded medical file...",
            "Detecting file type...",
            "Identifying medical modality...",
            "Loading AI processing pipeline...",
            "Processing complete."
        ]
        self.step_labels: list[QLabel] = []
        for msg in self.step_msgs:
            lbl = QLabel(f"○  {msg}")
            lbl.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 11px; font-weight: 500;")
            self.steps_layout.addWidget(lbl)
            self.step_labels.append(lbl)

        self.main_layout.addWidget(self.steps_frame)

        # Detected Result Panel (hidden by default)
        self.result_card = QFrame()
        self.result_card.setFixedHeight(50)
        self.result_card.setStyleSheet("background: rgba(16, 185, 129, 0.08); border: 1.5px solid rgba(16, 185, 129, 0.25); border-radius: 8px;")
        self.result_layout = QHBoxLayout(self.result_card)
        self.result_layout.setContentsMargins(12, 0, 12, 0)
        
        self.lbl_result = QLabel("")
        self.lbl_result.setStyleSheet("color: #10b981; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        self.result_layout.addWidget(self.lbl_result)
        self.result_layout.addStretch()
        
        self.lbl_check = QLabel("✓")
        self.lbl_check.setStyleSheet("color: #10b981; font-size: 18px; font-weight: bold; border: none; background: transparent;")
        self.result_layout.addWidget(self.lbl_check)
        
        self.main_layout.addWidget(self.result_card)
        self.result_card.hide()

        # Action Buttons
        self.btn_layout = QHBoxLayout()
        self.btn_layout.addStretch()

        self.btn_action = QPushButton("Cancel")
        self.btn_action.setFixedSize(100, 32)
        self.btn_action.setCursor(Qt.PointingHandCursor)
        self.btn_action.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04); color: white;
                border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px;
                font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.08); }
        """)
        self.btn_action.clicked.connect(self._on_action_clicked)
        self.btn_layout.addWidget(self.btn_action)
        self.main_layout.addLayout(self.btn_layout)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 16, 16)
        
        # Apple VisionOS styled glassmorphism fill
        painter.fillPath(path, QBrush(QColor(10, 12, 22, 245)))
        
        # Border
        painter.setPen(QPen(QColor(255, 255, 255, 12), 1.5))
        painter.drawPath(path)

    def _start_detection_simulation(self) -> None:
        # Load detector synchronously to fetch results immediately
        try:
            self.detected_data = MedicalFileDetectionEngine.detect_file(self.file_path)
        except Exception as e:
            QMessageBox.critical(self, "Detection Failure", f"Automatic file analysis failed:\n{e}")
            self.reject()
            return

        # Animate steps using a QTimer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_next_step)
        self.timer.start(450) # 450ms intervals for a premium fast feel

    def _animate_next_step(self) -> None:
        if self.animation_step < len(self.step_labels):
            lbl = self.step_labels[self.animation_step]
            lbl.setStyleSheet("color: #06b6d4; font-size: 11px; font-weight: bold;")
            lbl.setText(f"✓  {lbl.text()[3:]}")
            self.animation_step += 1
            self.progress.setValue(int((self.animation_step / len(self.step_labels)) * 100))
        else:
            self.timer.stop()
            self._display_final_detected_result()

    def _display_final_detected_result(self) -> None:
        label = self.detected_data.get("display_label", "Processed File")
        self.lbl_result.setText(f"Detected: {label}")
        
        # Animate view transitions
        self.steps_frame.hide()
        self.result_card.show()
        
        self.btn_action.setText("Proceed")
        self.btn_action.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                color: white; border: none; border-radius: 6px;
                font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background: #059669; }
        """)

    def _on_action_clicked(self) -> None:
        if self.btn_action.text() == "Proceed":
            self.detection_complete.emit(self.detected_data)
            self.accept()
        else:
            self.reject()
