"""
MediVerse AI — Document Repository View.
Lightroom-inspired premium visual grid for medical documents: upload, view, re-index, and metadata cards.
"""
from __future__ import annotations

import logging
import os
import math
from pathlib import Path
import shutil
from typing import Optional
from uuid import UUID

from PySide6.QtCore import Qt, Signal, QThread, QRectF, QPoint, QTimer
from PySide6.QtGui import (
    QColor, QCursor, QPainter, QLinearGradient, QRadialGradient, QPen, QBrush, QFont
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFileDialog, QMessageBox, QComboBox, QMenu, 
    QInputDialog, QDialog, QTextEdit, QFrame, QGridLayout, 
    QGraphicsDropShadowEffect, QApplication
)

from ai_core.ai_engine import get_ai_engine
from core.models.user import User
from config.settings import get_settings
from database.connection import get_db_session
from database.repositories.document_repository import DocumentRepository
from database.models.document_model import DocumentModel

logger = logging.getLogger("mediverse.modules.repository")


class MetadataViewDialog(QDialog):
    """Dialog to view document metadata, keywords, and medical entities in structured JSON."""
    def __init__(self, doc_title: str, metadata: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Document Metadata Viewer")
        self.setFixedSize(550, 440)
        self.setStyleSheet("background: #0b0d18; color: white; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(15)
        
        lbl = QLabel(f"Metadata Logs: {doc_title}")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #06b6d4; border: none; background: transparent;")
        layout.addWidget(lbl)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: #e2e8f0;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 10px;
            }
        """)
        
        import json
        formatted = json.dumps(metadata, indent=4)
        self.text_edit.setText(formatted)
        layout.addWidget(self.text_edit)
        
        close_btn = QPushButton("Close Viewer")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedHeight(38)
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
                color: white; border: none; border-radius: 8px;
                font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background: #2563eb; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class DocumentCard(QFrame):
    """Premium 3D Lightroom-style document visual card."""
    view_requested = Signal()
    reindex_requested = Signal()
    meta_requested = Signal()
    delete_requested = Signal()
    folder_requested = Signal()

    def __init__(self, doc: DocumentModel, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.doc_id = doc.id
        self.title = doc.title
        self.category = doc.category
        self.status = doc.embedding_status
        self.file_size = doc.file_size
        self.chunk_count = len(doc.chunks)
        self.created_at = doc.created_at
        
        self.hovered = False
        self.setFixedSize(260, 310)
        self.setMouseTracking(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        # Layout structure
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(10)

        # Custom thumbnail placeholder box (painted in paintEvent)
        self.thumb_box = QFrame()
        self.thumb_box.setFixedHeight(140)
        self.thumb_box.setStyleSheet("background: transparent; border: none;")
        self.main_layout.addWidget(self.thumb_box)

        # Title Label
        self.title_lbl = QLabel(self.title)
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setStyleSheet("color: white; font-size: 12.5px; font-weight: bold; background: transparent;")
        self.main_layout.addWidget(self.title_lbl)

        # Secondary Metadata Text
        self.meta_lbl = QLabel(f"Size: {self._format_size(self.file_size)}  |  Chunks: {self.chunk_count}\nUploaded: {self.created_at.strftime('%Y-%m-%d')}")
        self.meta_lbl.setWordWrap(True)
        self.meta_lbl.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 10.5px; background: transparent; line-height: 1.4;")
        self.main_layout.addWidget(self.meta_lbl)

        # Action Buttons Layer
        actions_row = QHBoxLayout()
        actions_row.setSpacing(6)
        
        self.view_btn = QPushButton("Open")
        self.view_btn.setCursor(Qt.PointingHandCursor)
        self.view_btn.setFixedHeight(28)
        self.view_btn.clicked.connect(self.view_requested.emit)
        self.view_btn.setStyleSheet(self._get_btn_style("#3b82f6"))
        
        self.options_btn = QPushButton("⚙ Actions")
        self.options_btn.setCursor(Qt.PointingHandCursor)
        self.options_btn.setFixedHeight(28)
        self.options_btn.clicked.connect(self._show_actions_menu)
        self.options_btn.setStyleSheet(self._get_btn_style("rgba(255,255,255,0.1)"))

        actions_row.addWidget(self.view_btn, 1)
        actions_row.addWidget(self.options_btn, 1)
        self.main_layout.addLayout(actions_row)

        # Drop shadow for depth
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 90))
        self.shadow.setOffset(0, 5)
        self.setGraphicsEffect(self.shadow)

    def _get_btn_style(self, color_base: str) -> str:
        return f"""
            QPushButton {{
                background: {color_base};
                color: white;
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.15);
            }}
        """

    def _show_actions_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #111424; color: white; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
            QMenu::item { padding: 8px 20px; }
            QMenu::item:selected { background: #3b82f6; }
        """)
        
        view_act = menu.addAction("👁️ View Document")
        reindex_act = menu.addAction("🔄 Re-index")
        folder_act = menu.addAction("📂 Open Folder")
        meta_act = menu.addAction("📝 View Metadata")
        delete_act = menu.addAction("❌ Delete")

        view_act.triggered.connect(self.view_requested.emit)
        reindex_act.triggered.connect(self.reindex_requested.emit)
        folder_act.triggered.connect(self.folder_requested.emit)
        meta_act.triggered.connect(self.meta_requested.emit)
        delete_act.triggered.connect(self.delete_requested.emit)

        # Show at cursor position
        menu.exec(QCursor.pos())

    def enterEvent(self, event) -> None:
        self.hovered = True
        self.shadow.setBlurRadius(25)
        self.shadow.setColor(QColor(6, 182, 212, 50))  # glowing cyan shadow on hover
        self.shadow.setOffset(0, 8)
        self.update()

    def leaveEvent(self, event) -> None:
        self.hovered = False
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 90))
        self.shadow.setOffset(0, 5)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        # Frosted glass card background
        gradient = QLinearGradient(0, 0, 0, rect.height())
        if self.hovered:
            gradient.setColorAt(0.0, QColor(255, 255, 255, 14))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 4))
        else:
            gradient.setColorAt(0.0, QColor(255, 255, 255, 8))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 2))
        painter.setBrush(QBrush(gradient))
        
        pen_gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        if self.hovered:
            pen_gradient.setColorAt(0.0, QColor(6, 182, 212, 200)) # Glowing cyan border
            pen_gradient.setColorAt(1.0, QColor(255, 255, 255, 15))
        else:
            pen_gradient.setColorAt(0.0, QColor(255, 255, 255, 15))
            pen_gradient.setColorAt(1.0, QColor(255, 255, 255, 3))
        painter.setPen(QPen(pen_gradient, 1))
        
        card_rect = rect.adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(card_rect, 16, 16)

        # Draw PDF Thumbnail Graphic in the thumbnail area
        tb_rect = self.thumb_box.geometry().adjusted(4, 4, -4, -4)
        
        # PDF Document Card Shape inside
        doc_grad = QLinearGradient(tb_rect.left(), tb_rect.top(), tb_rect.right(), tb_rect.bottom())
        doc_grad.setColorAt(0.0, QColor(15, 23, 42))
        doc_grad.setColorAt(1.0, QColor(30, 41, 59))
        painter.setBrush(QBrush(doc_grad))
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
        
        # Rounded PDF outline
        painter.drawRoundedRect(tb_rect, 10, 10)

        # Draw medical background icon grid in thumbnail
        painter.setPen(QPen(QColor(255, 255, 255, 5), 1))
        for line_y in range(int(tb_rect.top() + 25), int(tb_rect.bottom() - 15), 12):
            painter.drawLine(tb_rect.left() + 20, line_y, tb_rect.right() - 20, line_y)

        # Draw category capsule badge on top-left of thumbnail
        badge_text = self.category.upper()
        font_badge = QFont("Segoe UI", 7.5, QFont.Bold)
        painter.setFont(font_badge)
        
        badge_rect = QRectF(tb_rect.left() + 10, tb_rect.top() + 10, 65, 18)
        painter.setBrush(QBrush(QColor(139, 92, 246, 50)))  # Purple badge color
        painter.setPen(QPen(QColor(139, 92, 246, 150), 1))
        painter.drawRoundedRect(badge_rect, 4, 4)
        
        painter.setPen(QColor(168, 85, 247))
        painter.drawText(badge_rect, Qt.AlignCenter, badge_text)

        # Draw index status indicator bulb on top-right
        dot_color = QColor(251, 191, 36) # yellow
        if self.status == "complete":
            dot_color = QColor(16, 185, 129) # green
        elif self.status == "failed":
            dot_color = QColor(239, 68, 68) # red
            
        dot_center = QPoint(int(tb_rect.right() - 18), int(tb_rect.top() + 18))
        
        # Outer glow
        painter.setBrush(QBrush(QColor(dot_color.red(), dot_color.green(), dot_color.blue(), 60)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(dot_center, 8, 8)
        
        # Inner core
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(dot_center, 4, 4)

        # Giant PDF text emblem on thumbnail
        painter.setPen(QColor(255, 255, 255, 50))
        font_pdf = QFont("Segoe UI", 24, QFont.Black)
        painter.setFont(font_pdf)
        painter.drawText(tb_rect.adjusted(0, -10, 0, -10), Qt.AlignCenter, "PDF")

        # Draw Indexed and Embedded status capsules at bottom of thumbnail
        badge_y = tb_rect.bottom() - 25
        
        # 1. Indexed Badge
        ind_rect = QRectF(tb_rect.left() + 10, badge_y, 50, 16)
        painter.setBrush(QBrush(QColor(16, 185, 129, 30)))  # Green
        painter.setPen(QPen(QColor(16, 185, 129, 130), 1))
        painter.drawRoundedRect(ind_rect, 3, 3)
        painter.setPen(QColor(16, 185, 129))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        painter.drawText(ind_rect, Qt.AlignCenter, "INDEXED")

        # 2. Embedding Badge
        emb_rect = QRectF(tb_rect.left() + 66, badge_y, 60, 16)
        if self.status == "complete":
            painter.setBrush(QBrush(QColor(6, 182, 212, 30)))  # Cyan
            painter.setPen(QPen(QColor(6, 182, 212, 130), 1))
            painter.drawRoundedRect(emb_rect, 3, 3)
            painter.setPen(QColor(6, 182, 212))
            painter.drawText(emb_rect, Qt.AlignCenter, "EMBEDDED")
        else:
            painter.setBrush(QBrush(QColor(251, 191, 36, 30)))  # Amber
            painter.setPen(QPen(QColor(251, 191, 36, 130), 1))
            painter.drawRoundedRect(emb_rect, 3, 3)
            painter.setPen(QColor(251, 191, 36))
            painter.drawText(emb_rect, Qt.AlignCenter, "PENDING")

    def _format_size(self, size_bytes: Optional[int]) -> str:
        if size_bytes is None:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


class IndexingWorker(QThread):
    """Background worker to index documents via AI Engine without freezing UI."""
    progress = Signal(int, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, document_id, parent=None):
        super().__init__(parent)
        self.document_id = document_id

    def run(self):
        try:
            ai = get_ai_engine()
            ai.process_document(self.document_id, self._emit_progress)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

    def _emit_progress(self, percent: int, text: str):
        self.progress.emit(percent, text)


class RepositoryView(QWidget):
    """Manage the medical knowledge repository with a high-fidelity visual cards grid."""
    document_indexed = Signal() # Connected to main dashboard refreshes

    def __init__(self, current_user: User) -> None:
        super().__init__()
        self._user = current_user
        self._settings = get_settings()
        
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        # Header Area
        header = QHBoxLayout()
        title = QLabel("Knowledge Repository")
        title.setStyleSheet("color: white; font-size: 26px; font-weight: 800; letter-spacing: 0.5px;")
        header.addWidget(title)
        header.addStretch()

        # Premium Upload Button
        self.upload_btn = QPushButton("📤 Index Medical Document")
        self.upload_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.upload_btn.setFixedHeight(42)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #06b6d4);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 24px;
                font-weight: bold;
                font-size: 13px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #0891b2);
            }
        """)
        self.upload_btn.clicked.connect(self._handle_upload)
        header.addWidget(self.upload_btn)
        layout.addLayout(header)

        # Subheader Controls (Filters & Descs)
        sub = QHBoxLayout()
        sub.setSpacing(15)
        
        desc = QLabel("Manage clinical files. All PDFs are automatically chunked, metadata-extracted, and vector-embedded.")
        desc.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 13px;")
        sub.addWidget(desc)
        sub.addStretch()

        self.cat_filter = QComboBox()
        self.cat_filter.addItems([
            "All Categories", "WHO", "CDC", "ICMR", "Research_Papers", 
            "Medical_Books", "Hospital_SOPs", "Medical_Reports", "X_Rays", "Scan_Reports"
        ])
        self.cat_filter.setFixedHeight(36)
        self.cat_filter.setMinimumWidth(180)
        self.cat_filter.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.04);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 5px 15px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #111424; color: white;
                selection-background-color: #3b82f6;
            }
        """)
        self.cat_filter.currentTextChanged.connect(self.refresh_data)
        sub.addWidget(self.cat_filter)
        layout.addLayout(sub)

        # Lightroom Scroll Area Container
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.1);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.25);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Container inside Scroll Area
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent; border: none;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(20)
        
        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area, 1)

    def refresh_data(self) -> None:
        """Fetch documents from DB and populate Lightroom grid cards."""
        # Clear current grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        category = self.cat_filter.currentText()
        if category == "All Categories":
            category = None

        with get_db_session() as session:
            repo = DocumentRepository(session)
            docs = repo.get_all()
            
            if category:
                docs = [d for d in docs if d.category == category]

            cols = self._calculate_columns()

            # Populate grid cards
            for i, doc in enumerate(docs):
                card = DocumentCard(doc, self)
                
                # Wire signals
                doc_id = doc.id
                file_path = doc.file_path
                doc_title = doc.title
                
                metadata = {
                    "document_id": str(doc.id),
                    "title": doc.title,
                    "category": doc.category,
                    "file_size": doc.file_size,
                    "language": doc.language,
                    "keywords": doc.keywords,
                    "medical_entities": doc.medical_entities,
                    "embedding_status": doc.embedding_status,
                    "is_indexed": doc.is_indexed,
                    "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }

                card.view_requested.connect(lambda p=file_path: self._view_document(p))
                card.reindex_requested.connect(lambda d=doc_id: self._reindex_document(d))
                card.folder_requested.connect(lambda p=file_path: self._open_folder(p))
                card.meta_requested.connect(lambda t=doc_title, m=metadata: self._view_metadata(t, m))
                card.delete_requested.connect(lambda d=doc_id: self._delete_document(d))
                
                # Flow into columns based on width
                row = i // cols
                col = i % cols
                self.grid_layout.addWidget(card, row, col, Qt.AlignLeft | Qt.AlignTop)

            # Add stretch to bottom-right cell to anchor grid neatly
            self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)
            self.grid_layout.setColumnStretch(cols, 1)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Redraw layout grid columns on window scaling
        QTimer.singleShot(50, self.refresh_data)

    def _calculate_columns(self) -> int:
        scroll_width = self.scroll_area.width()
        card_w = 260 + 20 # width + spacing
        cols = max(1, scroll_width // card_w)
        return cols

    def _handle_upload(self) -> None:
        logger.info("File upload triggered by user")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Medical Document or Scan", "", 
            "Medical Files (*.pdf *.png *.jpg *.jpeg *.tiff *.bmp *.dcm *.dicom);;All Files (*)"
        )
        if not file_path:
            return
            
        path = Path(file_path)
        ext = path.suffix.lower()[1:]
        
        # Validation checks
        if ext == "pdf":
            try:
                with open(file_path, "rb") as f:
                    header = f.read(4)
                    if header != b"%PDF":
                        raise ValueError("Invalid PDF header")
                import fitz
                doc_check = fitz.open(file_path)
                _ = len(doc_check)
                doc_check.close()
            except Exception as e:
                logger.error(f"Selected PDF validation failed: {e}")
                QMessageBox.critical(self, "Corrupted PDF", f"The selected file is not a valid or readable PDF document:\n{e}")
                return
        else:
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    img.verify()
            except Exception as e:
                if ext not in ["dcm", "dicom"]:
                    logger.error(f"Selected image validation failed: {e}")
                    QMessageBox.critical(self, "Corrupted Image", f"The selected image file is corrupted or unreadable:\n{e}")
                    return

        # Auto-detect using UploadDetectionDialog
        from shared.components.upload_detection_dialog import UploadDetectionDialog
        dialog = UploadDetectionDialog(file_path, self)
        
        if dialog.exec() != QDialog.Accepted:
            return
            
        detected = dialog.detected_data
        category = detected.get("category", "Medical_Reports")
        file_type = ext

        # Save file into correct category folder under knowledge_base/
        base_kb = Path(self._settings.base_dir) / "knowledge_base"
        cat_folder = base_kb / category
        cat_folder.mkdir(parents=True, exist_ok=True)
        dest_path = cat_folder / path.name
        
        # Check for duplicates
        if dest_path.exists():
            reply = QMessageBox.question(
                self, "Duplicate Document",
                f"A document named '{path.name}' already exists in the {category} folder. Do you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Copy file
        try:
            import shutil
            logger.info(f"Saving file to repository path: {dest_path}")
            shutil.copy2(path, dest_path)
        except Exception as e:
            logger.error(f"Failed to copy file to repository: {e}")
            QMessageBox.critical(self, "Upload Failed", f"File permission or storage error:\n{e}")
            return
        
        # Save metadata into PostgreSQL
        try:
            with get_db_session() as session:
                repo = DocumentRepository(session)
                
                # Check if already registered in Postgres
                existing = session.query(repo._model_class).filter_by(file_path=str(dest_path)).first()
                if existing:
                    doc_id = existing.id
                    repo.update_embedding_status(doc_id, "pending", False)
                else:
                    doc_model = repo.add_document(
                        title=path.stem,
                        file_path=str(dest_path),
                        file_type=file_type,
                        file_size_bytes=dest_path.stat().st_size,
                        uploader_id=self._user.id,
                        category=category
                    )
                    doc_id = doc_model.id
                    logger.info(f"Document record added to PostgreSQL: {doc_id}")
        except Exception as e:
            logger.exception("Failed to insert document record into PostgreSQL")
            QMessageBox.critical(self, "Database Error", f"PostgreSQL connection or write failure:\n{e}")
            return
            
        self.refresh_data()
        self.document_indexed.emit() # Refresh dashboard counter
        
        # 6. Start Indexing
        from shared.components.progress_dialog import ProgressDialog
        self._progress = ProgressDialog("Indexing Document", self)
        self._progress.show()
        
        logger.info(f"Launching IndexingWorker for document: {doc_id}")
        self._worker = IndexingWorker(doc_id)
        self._worker.progress.connect(self._progress.set_progress)
        self._worker.finished.connect(self._on_indexing_finished)
        self._worker.error.connect(self._on_indexing_error)
        self._worker.start()

    def _on_indexing_finished(self):
        logger.info("Indexing worker finished successfully")
        self._progress.close()
        self.refresh_data()
        self.document_indexed.emit() # Refresh dashboard
        from shared.components.notification_toast import NotificationToast
        NotificationToast.show_message(self.window(), "Document Indexed Successfully", "success")

    def _on_indexing_error(self, error: str):
        logger.error(f"Indexing worker failed: {error}")
        self._progress.close()
        self.refresh_data()
        self.document_indexed.emit()
        QMessageBox.critical(self, "Indexing Error", f"Failed to process document:\n{error}")

    def _view_document(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists():
            QMessageBox.warning(self, "File Not Found", "The physical document file does not exist on disk.")
            return
        try:
            logger.info(f"Opening file: {file_path}")
            os.startfile(str(path))
        except Exception as e:
            logger.error(f"Error opening file: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open document:\n{e}")

    def _open_folder(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.parent.exists():
            QMessageBox.warning(self, "Directory Not Found", "The folder containing the document does not exist.")
            return
        try:
            logger.info(f"Opening folder: {path.parent}")
            os.startfile(str(path.parent))
        except Exception as e:
            logger.error(f"Error opening folder: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open directory:\n{e}")

    def _view_metadata(self, title: str, metadata: dict) -> None:
        dialog = MetadataViewDialog(title, metadata, self)
        dialog.exec()

    def _reindex_document(self, doc_id) -> None:
        logger.info(f"Re-indexing requested for document: {doc_id}")
        from shared.components.progress_dialog import ProgressDialog
        self._progress = ProgressDialog("Re-indexing Document", self)
        self._progress.show()
        
        self._worker = IndexingWorker(doc_id)
        self._worker.progress.connect(self._progress.set_progress)
        self._worker.finished.connect(self._on_indexing_finished)
        self._worker.error.connect(self._on_indexing_error)
        self._worker.start()

    def _delete_document(self, doc_id) -> None:
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to delete this document? All vectors and the physical file will be removed.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            logger.info(f"Starting deletion of document: {doc_id}")
            try:
                file_to_delete = None
                with get_db_session() as session:
                    repo = DocumentRepository(session)
                    doc = repo.get_by_id_or_none(doc_id)
                    if doc:
                        file_to_delete = doc.file_path
                    repo.delete_document(doc_id)
                    
                    # Delete from ChromaDB
                    from vector_db.collections import MedicalDocumentCollection
                    try:
                        MedicalDocumentCollection().delete_by_document_id(str(doc_id))
                        logger.info(f"Successfully deleted embeddings from ChromaDB for doc: {doc_id}")
                    except Exception as e:
                        logger.error(f"Failed to delete embeddings from ChromaDB for doc {doc_id}: {e}")
                
                # Delete physical file
                if file_to_delete:
                    path = Path(file_to_delete)
                    if path.exists():
                        path.unlink()
                        logger.info(f"Deleted physical file: {file_to_delete}")
            except Exception as e:
                logger.error(f"Error during document deletion: {e}")
                QMessageBox.critical(self, "Delete Error", f"Failed to completely delete the document:\n{e}")
            
            self.refresh_data()
            self.document_indexed.emit() # Refresh dashboard
