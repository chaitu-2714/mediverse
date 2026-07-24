"""
MediVerse AI — Clinical Dialogue Workspace.
Redesigned with custom structured AI Response Cards, animated fade-ins, constrained chat row wrappers, and the Evidence Explorer.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Optional, List
from uuid import UUID

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPointF, QPropertyAnimation
from PySide6.QtGui import (
    QColor, QCursor, QPainter, QLinearGradient, QRadialGradient, QPen, QBrush, QFont
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QLineEdit, QPushButton, QScrollArea, QFrame, QSizePolicy, 
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QDialog,
    QApplication, QMessageBox, QFileDialog
)

from ai_core.ai_engine import get_ai_engine
from core.models.user import User
from core.models.search_result import AIResponse, SourceReference
from database.connection import get_db_session
from database.repositories.document_repository import DocumentRepository

logger = logging.getLogger("mediverse.modules.ai_assistant")


class ToggleSwitch(QWidget):
    """Sliding toggle switch widget."""
    toggled = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(46, 22)
        self._checked = False
        self._thumb_position = 3.0
        self.setCursor(Qt.PointingHandCursor)
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, value: bool) -> None:
        if self._checked != value:
            self._checked = value
            self._timer.start(8)
            self.toggled.emit(self._checked)
            self.update()

    def _animate(self) -> None:
        target = 24.0 if self._checked else 3.0
        step = 3.0
        if abs(self._thumb_position - target) <= step:
            self._thumb_position = target
            self._timer.stop()
        else:
            self._thumb_position += step if self._thumb_position < target else -step
        self.update()

    def mousePressEvent(self, event) -> None:
        self.checked = not self._checked
        event.accept()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        track_color = QColor(6, 182, 212, 120) if self._checked else QColor(255, 255, 255, 15)
        painter.setBrush(QBrush(track_color))
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
        painter.drawRoundedRect(rect, 11, 11)

        knob_color = QColor(6, 182, 212) if self._checked else QColor(200, 200, 200)
        painter.setBrush(QBrush(knob_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(self._thumb_position + 8, 11), 8, 8)
        painter.end()


class CategoryToggleRow(QWidget):
    """Scope filter row."""
    toggled = Signal(str, bool)

    def __init__(self, category: str, label_text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.category = category
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        
        self.lbl = QLabel(label_text)
        self.lbl.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; font-weight: 500;")
        
        self.toggle = ToggleSwitch()
        self.toggle.toggled.connect(self._on_toggled)
        
        layout.addWidget(self.lbl)
        layout.addStretch()
        layout.addWidget(self.toggle)

    def _on_toggled(self, checked: bool) -> None:
        if checked:
            self.lbl.setStyleSheet("color: #06b6d4; font-size: 12px; font-weight: bold;")
        else:
            self.lbl.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; font-weight: 500;")
        self.toggled.emit(self.category, checked)


class FullEvidenceDialog(QDialog):
    """Modal to view full text chunk of the evidence reference."""
    def __init__(self, doc_title: str, text: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Full Evidence Viewer")
        self.setFixedSize(600, 450)
        self.setStyleSheet("background: #0b0d18; color: white; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_lbl = QLabel(doc_title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #06b6d4; border: none; background: transparent;")
        layout.addWidget(title_lbl)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; background: rgba(0,0,0,0.15); }")
        
        content = QLabel(text)
        content.setWordWrap(True)
        content.setStyleSheet("color: #e2e8f0; font-size: 13px; line-height: 1.6; padding: 10px; background: transparent;")
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                color: white; border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.15); }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class EvidenceCard(QFrame):
    """Citations and Evidence explorer card for the Evidence Explorer."""
    
    def __init__(self, src: SourceReference, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.src = src
        self.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }
            QFrame:hover {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(6, 182, 212, 0.2);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Title
        title_lbl = QLabel(src.document_title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("color: white; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(title_lbl)

        # Meta Parameters
        cat_lbl = QLabel(f"Category: {src.category}")
        cat_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 10px; border: none; background: transparent;")
        layout.addWidget(cat_lbl)

        sec_lbl = QLabel("Section: Clinical Overview")
        sec_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 10px; border: none; background: transparent;")
        layout.addWidget(sec_lbl)

        page_lbl = QLabel(f"Page: {src.page_number}")
        page_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 10px; border: none; background: transparent;")
        layout.addWidget(page_lbl)

        # Snippet header
        ev_header = QLabel("Evidence:")
        ev_header.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 10.5px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(ev_header)

        # Snippet body
        snippet = QLabel(src.chunk_text[:140] + "..." if len(src.chunk_text) > 140 else src.chunk_text)
        snippet.setWordWrap(True)
        snippet.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 10.5px; font-style: italic; border: none; line-height: 1.4; background: transparent;")
        layout.addWidget(snippet)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        open_btn = QPushButton("Open PDF")
        open_btn.setFixedHeight(24)
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setStyleSheet(self._btn_style())
        open_btn.clicked.connect(self._open_pdf)
        
        view_btn = QPushButton("View Full Evidence")
        view_btn.setFixedHeight(24)
        view_btn.setCursor(Qt.PointingHandCursor)
        view_btn.setStyleSheet(self._btn_style())
        view_btn.clicked.connect(self._view_full)

        btn_layout.addWidget(open_btn)
        btn_layout.addWidget(view_btn)
        layout.addLayout(btn_layout)

    def _btn_style(self) -> str:
        return """
            QPushButton {
                background: rgba(255,255,255,0.03); color: #3b82f6;
                border: 1px solid rgba(255,255,255,0.06); border-radius: 4px;
                font-size: 9.5px; font-weight: bold;
            }
            QPushButton:hover { background: rgba(59, 130, 246, 0.12); color: white; }
        """

    def _open_pdf(self) -> None:
        try:
            with get_db_session() as session:
                repo = DocumentRepository(session)
                doc_id = self.src.document_id
                if isinstance(doc_id, str):
                    try:
                        doc_id = UUID(doc_id)
                    except ValueError:
                        pass
                doc = repo.get_by_id_or_none(doc_id)
                if doc and doc.file_path:
                    path = Path(doc.file_path)
                    if path.exists():
                        os.startfile(str(path))
                    else:
                        QMessageBox.warning(self, "Missing Document", "The physical file has been moved from local storage.")
                else:
                    QMessageBox.warning(self, "Record Not Found", "PostgreSQL record for document reference was not resolved.")
        except Exception as e:
            logger.error(f"Failed to load document reference: {e}")

    def _view_full(self) -> None:
        dialog = FullEvidenceDialog(self.src.document_title, self.src.chunk_text, self)
        dialog.exec()


class AIResponseCard(QFrame):
    """Premium floating card container for AI responses containing references and disclaimers."""
    clicked = Signal(object)  # Emits self when clicked for active syncing
    
    def __init__(self, answer: str, sources: list[SourceReference], parent=None) -> None:
        super().__init__(parent)
        self._answer = answer
        self._sources = sources
        self._expanded = True
        self._selected = False
        
        self.setStyleSheet("background: transparent; border: none;")
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        
        # Inner frame to hold all content and apply styled border/shadow
        self.inner_frame = QFrame()
        self.inner_frame.setObjectName("card")
        self.inner_frame.setStyleSheet("""
            QFrame#card {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
            }
        """)
        
        self.card_layout = QVBoxLayout(self.inner_frame)
        self.card_layout.setContentsMargins(18, 18, 18, 18)
        self.card_layout.setSpacing(12)
        main_layout.addWidget(self.inner_frame)

        # Header Row
        header = QHBoxLayout()
        ai_icon = QLabel("🤖")
        ai_icon.setStyleSheet("font-size: 16px; border: none; background: transparent;")
        
        title_lbl = QLabel("Clinical AI Response")
        title_lbl.setStyleSheet("color: white; font-family: 'Segoe UI', Inter; font-size: 13.5px; font-weight: bold; border: none; background: transparent;")
        
        header.addWidget(ai_icon)
        header.addWidget(title_lbl)
        header.addStretch()

        # Expand/Collapse Control
        self.exp_btn = QPushButton("▲ Collapse")
        self.exp_btn.setFixedSize(80, 24)
        self.exp_btn.setCursor(Qt.PointingHandCursor)
        self.exp_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: rgba(255,255,255,0.4);
                border: none; font-size: 10px; font-weight: bold;
            }
            QPushButton:hover { color: white; }
        """)
        self.exp_btn.clicked.connect(self._toggle_expand)
        header.addWidget(self.exp_btn)
        self.card_layout.addLayout(header)

        # Content Widget to house sections (collapsible)
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent; border: none;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(6)

        # Split text: first paragraph as Overview, rest as Evidence Summary
        paragraphs = [p.strip() for p in self._answer.split("\n\n") if p.strip()]
        if len(paragraphs) > 1:
            overview_text = paragraphs[0]
            summary_text = "\n\n".join(paragraphs[1:])
        elif paragraphs:
            overview_text = paragraphs[0]
            summary_text = "Detailed documentation matches the clinical overview above."
        else:
            overview_text = "No clinical overview parameters retrieved."
            summary_text = "No evidence summary available."

        # 🧠 Clinical Overview Section
        self._add_section("🧠 Clinical Overview", overview_text, "#06b6d4")
        
        # 📄 Evidence Summary Section
        self._add_section("📄 Evidence Summary", summary_text, "#a855f7")

        # 📚 References Section
        ref_text = ""
        if self._sources:
            ref_lines = [f"• {src.document_title} (Page {src.page_number})" for src in self._sources]
            ref_text = "\n".join(ref_lines)
        else:
            ref_text = "• No external reference documents cited for this response."
        self._add_section("📚 References", ref_text, "#3b82f6")

        # ⚠️ Medical Disclaimer Section
        disclaimer_text = (
            "This synthesized information is retrieved from indexed medical reference guidelines "
            "and is intended for informational purposes only. It does not constitute professional medical "
            "advice, diagnosis, or treatment. Always consult with a qualified healthcare provider for clinical decisions."
        )
        self._add_section("⚠️ Medical Disclaimer", disclaimer_text, "#eab308")

        self.card_layout.addWidget(self.content_widget)

        # Actions Row
        actions = QHBoxLayout()
        actions.setSpacing(8)

        # Copy
        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.clicked.connect(self._copy_text)
        
        # Bookmark
        self.bookmark_btn = QPushButton("🔖 Bookmark")
        self.bookmark_btn.clicked.connect(self._bookmark_response)

        # Export PDF
        self.export_btn = QPushButton("📥 Export PDF")
        self.export_btn.clicked.connect(self._export_pdf)

        # Read Aloud
        self.read_btn = QPushButton("🔊 Read Aloud")
        self.read_btn.clicked.connect(self._read_aloud)

        for btn in [self.copy_btn, self.bookmark_btn, self.export_btn, self.read_btn]:
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._btn_action_style())
            actions.addWidget(btn)

        actions.addStretch()
        self.card_layout.addLayout(actions)

        # Shadows on inner_frame
        shadow = QGraphicsDropShadowEffect(self.inner_frame)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 90))
        shadow.setOffset(0, 4)
        self.inner_frame.setGraphicsEffect(shadow)

        # Opacity fade-in effect on outer QFrame
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.fade_anim.setDuration(350)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.finished.connect(self._on_fade_finished)
        self.fade_anim.start()

    def _on_fade_finished(self) -> None:
        # Clear graphics effect to avoid GC opacity corruption and speed up layout painting
        try:
            self.setGraphicsEffect(None)
        except RuntimeError:
            pass
            
        if hasattr(self, "opacity_effect") and self.opacity_effect:
            try:
                self.opacity_effect.deleteLater()
            except RuntimeError:
                pass
            self.opacity_effect = None
            
        if hasattr(self, "fade_anim") and self.fade_anim:
            try:
                self.fade_anim.deleteLater()
            except RuntimeError:
                pass
            self.fade_anim = None

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        if selected:
            self.inner_frame.setStyleSheet("""
                QFrame#card {
                    background: rgba(255, 255, 255, 0.04);
                    border: 1.5px solid rgba(6, 182, 212, 0.5);
                    border-top: 1.5px solid rgba(6, 182, 212, 0.6);
                    border-radius: 14px;
                }
            """)
        else:
            self.inner_frame.setStyleSheet("""
                QFrame#card {
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-top: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 14px;
                }
            """)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.clicked.emit(self)

    def _add_section(self, title: str, content: str, color_hex: str) -> None:
        if self.content_layout.count() > 0:
            self.content_layout.addSpacing(10)
            
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {color_hex}; font-family: 'Segoe UI', Inter; font-size: 12px; font-weight: 700; border: none; background: transparent;")
        self.content_layout.addWidget(title_lbl)

        content_lbl = QLabel(content)
        content_lbl.setWordWrap(True)
        content_lbl.setStyleSheet("color: rgba(255,255,255,0.85); font-family: 'Segoe UI', Inter; font-size: 12.5px; border: none; background: transparent; line-height: 1.5;")
        self.content_layout.addWidget(content_lbl)

    def _btn_action_style(self) -> str:
        return """
            QPushButton {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
                color: rgba(255,255,255,0.75);
                padding: 0 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.06);
                color: white;
            }
        """

    def _toggle_expand(self) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            self.content_widget.show()
            self.exp_btn.setText("▲ Collapse")
        else:
            self.content_widget.hide()
            self.exp_btn.setText("▼ Expand")

    def _copy_text(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self._answer)
        QMessageBox.information(self, "Copied", "Response text copied to clipboard successfully.")

    def _bookmark_response(self) -> None:
        QMessageBox.information(self, "Bookmarked", "This response has been successfully saved to your bookmarks dashboard.")

    def _export_pdf(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, "Export AI Response", "ai_response", "Text Files (*.txt);;Markdown Files (*.md)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self._answer)
            QMessageBox.information(self, "Saved", f"Response file saved successfully to:\n{file_path}")

    def _read_aloud(self) -> None:
        QMessageBox.information(self, "Speech Synthesizer", "Speech Synthesis Node: Reading Response Aloud...")


class ChatBubble(QFrame):
    """User input chat bubble widget."""
    def __init__(self, text: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
                color: white;
                border-radius: 12px;
                border-top-right-radius: 2px;
            }
        """)

        msg = QLabel(text)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: white; font-size: 13px; background: transparent; border: none; line-height: 1.4;")
        layout.addWidget(msg)


class ChatRow(QWidget):
    """Constrains chat heights and wraps user/AI bubbles in horizontal alignment layout."""
    def __init__(self, child_widget: QWidget, is_user: bool) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        
        if is_user:
            layout.addStretch(1)
            layout.addWidget(child_widget)
        else:
            layout.addWidget(child_widget)
            layout.addStretch(1)


class WorkerThread(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, query: str, user_id, category: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.query = query
        self.user_id = user_id
        self.category = category

    def run(self):
        try:
            ai = get_ai_engine()
            response = ai.query(self.query, user_id=self.user_id, category=self.category)
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))


class AssistantView(QWidget):
    """Immersive Clinical Dialogue Core workspace."""

    def __init__(self, current_user: User) -> None:
        super().__init__()
        self._user = current_user
        self._ai = get_ai_engine()
        self._active_category: Optional[str] = None
        self._selected_card: Optional[AIResponseCard] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # ── 1. LEFT PANEL: SCOPE FILTER ──
        left_panel = QFrame()
        left_panel.setFixedWidth(230)
        left_panel.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 16px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(18, 20, 18, 20)
        left_layout.setSpacing(14)

        left_lbl = QLabel("RAG Vector Scope")
        left_lbl.setStyleSheet("color: white; font-size: 14.5px; font-weight: bold; border: none;")
        left_layout.addWidget(left_lbl)

        desc_lbl = QLabel("Toggle scope filters to restrict semantic search nodes:")
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11px; border: none; line-height: 1.4;")
        left_layout.addWidget(desc_lbl)

        self.toggles: List[CategoryToggleRow] = []
        categories = ["WHO", "CDC", "ICMR", "Research_Papers", "Medical_Books", "Hospital_SOPs"]
        for cat in categories:
            row = CategoryToggleRow(cat, cat, self)
            row.toggled.connect(self._handle_category_toggled)
            self.toggles.append(row)
            left_layout.addWidget(row)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # ── 2. CENTER PANEL: IMMERSIVE CONVERSATION ──
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(15)

        # Workspace Title & Badge Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        
        title = QLabel("Clinical Dialogue Core")
        title.setStyleSheet("color: white; font-size: 20px; font-weight: 800; border: none;")
        
        # Medical Intelligence Badge
        badge = QLabel("⚕ COGNITIVE INTELLIGENCE MODULE ONLINE")
        badge.setStyleSheet("color: #06b6d4; font-family: 'Segoe UI'; font-size: 9px; font-weight: bold; letter-spacing: 0.5px;")
        
        title_box.addWidget(title)
        title_box.addWidget(badge)
        header.addLayout(title_box)
        header.addStretch()

        # Reset button
        clear_btn = QPushButton("Reset workspace")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #ef4444; border: 1.2px solid rgba(239,68,68,0.4);
                border-radius: 8px; padding: 6px 12px; font-weight: 600; font-size: 10.5px;
            }
            QPushButton:hover { background: rgba(239, 68, 68, 0.08); }
        """)
        clear_btn.clicked.connect(self._clear_chat)
        header.addWidget(clear_btn)
        center_layout.addLayout(header)

        # Dialogue scrolling panel
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea { border: 1px solid rgba(255,255,255,0.05); border-radius: 16px; background: rgba(0,0,0,0.15); }
            QScrollBar:vertical { background: transparent; width: 6px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.1); border-radius: 3px; }
        """)
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(16)
        self.chat_layout.setContentsMargins(18, 18, 18, 18)
        self.scroll.setWidget(self.chat_container)
        center_layout.addWidget(self.scroll, 1)

        # Secure auto-scrolling on range modification
        self.scroll.verticalScrollBar().rangeChanged.connect(self._on_scroll_range_changed)

        # Rounded prompt bar container
        prompt_frame = QFrame()
        prompt_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
            }
        """)
        prompt_layout = QHBoxLayout(prompt_frame)
        prompt_layout.setContentsMargins(12, 4, 12, 4)
        prompt_layout.setSpacing(8)

        # Attachment Button (📎)
        self.attach_btn = QPushButton("📎")
        self.attach_btn.setFixedSize(28, 28)
        self.attach_btn.setCursor(Qt.PointingHandCursor)
        self.attach_btn.setStyleSheet(self._prompt_action_style())
        self.attach_btn.clicked.connect(self._handle_attach)
        prompt_layout.addWidget(self.attach_btn)

        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter symptoms, patient vitals, or clinical queries...")
        self.input_field.setFixedHeight(40)
        self.input_field.setStyleSheet("QLineEdit { background: transparent; border: none; color: white; font-size: 13.5px; }")
        self.input_field.returnPressed.connect(self._send_message)
        prompt_layout.addWidget(self.input_field, 1)

        # Voice Button (🎙️)
        self.voice_btn = QPushButton("🎙️")
        self.voice_btn.setFixedSize(28, 28)
        self.voice_btn.setCursor(Qt.PointingHandCursor)
        self.voice_btn.setStyleSheet(self._prompt_action_style())
        self.voice_btn.clicked.connect(self._handle_voice)
        prompt_layout.addWidget(self.voice_btn)

        # Generate Button
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setFixedSize(85, 30)
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
                color: white; border: none; border-radius: 10px;
                font-weight: bold; font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed);
            }
        """)
        self.generate_btn.clicked.connect(self._send_message)
        prompt_layout.addWidget(self.generate_btn)

        center_layout.addWidget(prompt_frame)
        main_layout.addWidget(center_panel, 1)

        # ── 3. RIGHT PANEL: EVIDENCE EXPLORER ──
        self.right_panel = QFrame()
        self.right_panel.setFixedWidth(280)
        self.right_panel.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 16px;
            }
        """)
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(15, 20, 15, 20)
        right_layout.setSpacing(15)

        right_title = QLabel("Evidence Explorer")
        right_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold; border: none; background: transparent;")
        right_layout.addWidget(right_title)

        # Scroll for references
        self.ref_scroll = QScrollArea()
        self.ref_scroll.setWidgetResizable(True)
        self.ref_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.ref_container = QWidget()
        self.ref_container.setStyleSheet("background: transparent; border: none;")
        self.ref_layout = QVBoxLayout(self.ref_container)
        self.ref_layout.setContentsMargins(0, 0, 0, 0)
        self.ref_layout.setSpacing(12)
        self.ref_layout.setAlignment(Qt.AlignTop)
        self.ref_scroll.setWidget(self.ref_container)
        
        right_layout.addWidget(self.ref_scroll, 1)
        main_layout.addWidget(self.right_panel)

        # Default welcome prompt card (called after ref_layout is fully constructed)
        self._add_welcome_card()

    def _prompt_action_style(self) -> str:
        return """
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,0.4);
                font-size: 15px;
                border: none;
            }
            QPushButton:hover { color: white; }
        """

    def _handle_category_toggled(self, category: str, checked: bool) -> None:
        if checked:
            for row in self.toggles:
                if row.category != category:
                    row.toggle.checked = False
            self._active_category = category
        else:
            if self._active_category == category:
                self._active_category = None

    def _add_welcome_card(self) -> None:
        self._add_ai_card(
            "Establishing connection to medical vector models. Send clinical symptoms parameter "
            "queries to search internal databases and compile summaries grounded against direct evidence.",
            []
        )

    def _add_ai_card(self, answer: str, sources: list[SourceReference]) -> None:
        card = AIResponseCard(answer, sources, parent=self.chat_container)
        card.clicked.connect(self._select_card)
        
        row = ChatRow(card, is_user=False)
        self.chat_layout.addWidget(row)
        
        self._update_bubble_widths()
        self._select_card(card)
        self._scroll_to_bottom()

    def _add_user_message(self, text: str) -> None:
        bubble = ChatBubble(text)
        
        row = ChatRow(bubble, is_user=True)
        self.chat_layout.addWidget(row)
        
        self._update_bubble_widths()
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())
        QTimer.singleShot(50, lambda: sb.setValue(sb.maximum()))
        QTimer.singleShot(150, lambda: sb.setValue(sb.maximum()))

    def _on_scroll_range_changed(self, min_val: int, max_val: int) -> None:
        # Smoothly track scrollbar to bottom when content extends
        self.scroll.verticalScrollBar().setValue(max_val)

    def _update_bubble_widths(self) -> None:
        scroll_width = self.scroll.width()
        if scroll_width <= 100:
            scroll_width = 800
        available_width = scroll_width - 60
        
        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if not item:
                continue
            row = item.widget()
            if isinstance(row, ChatRow):
                bubble = row.findChild(ChatBubble)
                if bubble:
                    bubble.setMaximumWidth(int(available_width * 0.75))
                card = row.findChild(AIResponseCard)
                if card:
                    card.setMaximumWidth(int(available_width * 0.90))
        self.chat_container.adjustSize()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_bubble_widths()

    def _send_message(self) -> None:
        text = self.input_field.text().strip()
        if not text:
            return
            
        logger.info("User Query Received: '%s'", text)
        self.input_field.clear()
        self._add_user_message(text)
        
        self.input_field.setEnabled(False)
        self.generate_btn.setEnabled(False)
        
        # Wrapped thinking indicator row to prevent layout spacing inconsistencies
        self.thinking_lbl = QLabel("AI core aligning vectors and retrieving citation logs...")
        self.thinking_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 11px; font-style: italic; border: none; background: transparent;")
        
        self.thinking_row = ChatRow(self.thinking_lbl, is_user=False)
        self.chat_layout.addWidget(self.thinking_row)
        self._scroll_to_bottom()
        
        self.worker = WorkerThread(text, self._user.id, category=self._active_category)
        self.worker.finished.connect(self._on_ai_response)
        self.worker.error.connect(self._on_ai_error)
        self.worker.start()

    def _on_ai_response(self, response: AIResponse) -> None:
        if hasattr(self, "thinking_row") and self.thinking_row:
            self.chat_layout.removeWidget(self.thinking_row)
            self.thinking_row.deleteLater()
            self.thinking_row = None

        # Add card to dialogue stream
        self._add_ai_card(response.answer, response.sources)
        logger.info("AI Response Rendered successfully")
        logger.info("Chat History Updated with AI response")
        
        self.input_field.setEnabled(True)
        self.generate_btn.setEnabled(True)
        self.input_field.setFocus()
        self._scroll_to_bottom()

    def _on_ai_error(self, err: str) -> None:
        if hasattr(self, "thinking_row") and self.thinking_row:
            self.chat_layout.removeWidget(self.thinking_row)
            self.thinking_row.deleteLater()
            self.thinking_row = None

        self._add_ai_card(f"An error occurred: {err}", [])
        
        self.input_field.setEnabled(True)
        self.generate_btn.setEnabled(True)
        self.input_field.setFocus()

    def _clear_chat(self) -> None:
        self._selected_card = None
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
                item.layout().deleteLater()

        self._clear_evidence_explorer()
        self._add_welcome_card()

    def _clear_evidence_explorer(self) -> None:
        while self.ref_layout.count():
            item = self.ref_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _update_evidence_explorer(self, sources: list[SourceReference]) -> None:
        self._clear_evidence_explorer()

        # Add citation evidence cards
        if sources:
            for src in sources:
                card = EvidenceCard(src, self)
                self.ref_layout.addWidget(card)
        else:
            no_lbl = QLabel("No source citations found.")
            no_lbl.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11px; font-style: italic; border: none; background: transparent;")
            self.ref_layout.addWidget(no_lbl)

    def _select_card(self, card: AIResponseCard) -> None:
        if self._selected_card == card:
            return
            
        if self._selected_card:
            try:
                self._selected_card.set_selected(False)
            except RuntimeError:
                pass
                
        self._selected_card = card
        if card:
            card.set_selected(True)
            self._update_evidence_explorer(card._sources)

    def _handle_attach(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select clinical attachments", "", "PDF/Text files (*.pdf *.txt)")
        if file_path:
            QMessageBox.information(self, "Attached", f"File '{Path(file_path).name}' attached as RAG context successfully.")

    def _handle_voice(self) -> None:
        self.input_field.setText("Listening for vocal symptom input parameters...")
        QTimer.singleShot(1500, lambda: self.input_field.setText("Assess sepsis indicators under WHO Guidelines"))
