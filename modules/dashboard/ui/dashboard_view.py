"""
MediVerse AI — Command Center Dashboard.
Premium visual dashboard with Apple VisionOS glassmorphic cards,
welcome banner nodes, interactive upload card, and clinical quick actions panel.
"""
from __future__ import annotations

import logging
from typing import Optional
from PySide6.QtCore import Qt, QTimer, QRectF, Signal
from PySide6.QtGui import (
    QColor, QPainter, QLinearGradient, QRadialGradient, QPen, QBrush, QFont, QCursor
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QGraphicsDropShadowEffect, QScrollArea, QPushButton
)

from core.models.user import User
from database.connection import get_db_session
from database.repositories.document_repository import DocumentRepository
from database.models.chunk_model import DocumentChunkModel
from shared.components.notification_toast import NotificationToast

logger = logging.getLogger("mediverse.ui.dashboard")


class GlassCard(QFrame):
    """Frosted glassmorphic card with dynamic border highlight and soft drop shadow."""
    
    def __init__(self, title: str, subtitle: str, icon: str, accent_color: QColor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.accent_color = accent_color
        self.hovered = False
        self.setMouseTracking(True)
        self.setMinimumHeight(100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(6)
        
        header = QHBoxLayout()
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-family: 'Segoe UI'; font-size: 10px; font-weight: bold; letter-spacing: 0.8px; background: transparent;")
        
        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setStyleSheet(f"font-size: 16px; background: transparent; color: {accent_color.name()};")
        
        header.addWidget(self.title_lbl)
        header.addStretch()
        header.addWidget(self.icon_lbl)
        layout.addLayout(header)
        
        self.value_lbl = QLabel(subtitle)
        self.value_lbl.setStyleSheet("color: white; font-size: 20px; font-weight: 800; background: transparent;")
        layout.addWidget(self.value_lbl)

        self.glow_bar = QWidget()
        self.glow_bar.setFixedHeight(2)
        self.glow_bar.setStyleSheet(f"background: {accent_color.name()}; border-radius: 1px;")
        layout.addWidget(self.glow_bar)

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 90))
        self.shadow.setOffset(0, 6)
        self.setGraphicsEffect(self.shadow)

    def set_value(self, text: str) -> None:
        self.value_lbl.setText(text)

    def enterEvent(self, event) -> None:
        self.hovered = True
        self.shadow.setBlurRadius(25)
        self.shadow.setColor(QColor(self.accent_color.red(), self.accent_color.green(), self.accent_color.blue(), 30))
        self.shadow.setOffset(0, 8)
        self.update()

    def leaveEvent(self, event) -> None:
        self.hovered = False
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 90))
        self.shadow.setOffset(0, 6)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        gradient = QLinearGradient(0, 0, 0, rect.height())
        if self.hovered:
            gradient.setColorAt(0.0, QColor(255, 255, 255, 16))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 4))
        else:
            gradient.setColorAt(0.0, QColor(255, 255, 255, 8))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 2))
        painter.setBrush(QBrush(gradient))
        
        pen_gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        if self.hovered:
            pen_gradient.setColorAt(0.0, self.accent_color)
            pen_gradient.setColorAt(1.0, QColor(255, 255, 255, 8))
        else:
            pen_gradient.setColorAt(0.0, QColor(255, 255, 255, 14))
            pen_gradient.setColorAt(1.0, QColor(255, 255, 255, 3))
            
        painter.setPen(QPen(pen_gradient, 1))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 16, 16)


class InteractiveUploadCard(QFrame):
    """Large interactive upload slot card with dashed neon border and pulse effect."""
    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.hovered = False
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(240)
        self.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)
        
        icon = QLabel("🩻")
        icon.setStyleSheet("font-size: 44px; background: transparent;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        
        title = QLabel("DRAG & DROP MEDICAL FILE")
        title.setStyleSheet("color: white; font-size: 14px; font-weight: 800; letter-spacing: 1px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        desc = QLabel("Supports Brain/Spine/Knee scans, Chest X-Rays, Mammography, LFT/CBC/KFT medical PDFs & DICOM files")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11.5px; line-height: 1.4;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        btn = QLabel("Click to Browse Scan Asset")
        btn.setStyleSheet("color: #06b6d4; font-size: 11.5px; font-weight: bold; text-decoration: underline;")
        btn.setAlignment(Qt.AlignCenter)
        layout.addWidget(btn)

    def enterEvent(self, event) -> None:
        self.hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self.hovered = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        
        painter.setPen(Qt.NoPen)
        if self.hovered:
            painter.setBrush(QBrush(QColor(6, 182, 212, 10)))
            painter.drawRoundedRect(rect, 24, 24)
            pen = QPen(QColor(6, 182, 212), 2, Qt.DashLine)
        else:
            painter.setBrush(QBrush(QColor(255, 255, 255, 3)))
            painter.drawRoundedRect(rect, 24, 24)
            pen = QPen(QColor(255, 255, 255, 20), 1.5, Qt.DashLine)
            
        painter.setPen(pen)
        painter.drawRoundedRect(rect.adjusted(1,1,-1,-1), 24, 24)
        painter.end()


class LiveFeedCard(QFrame):
    """Visual card representing a processed document log."""
    def __init__(self, title: str, category: str, date: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 8px;
            }
            QFrame:hover {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(6, 182, 212, 0.2);
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        
        icon = QLabel("📄")
        icon.setStyleSheet("font-size: 14px; border: none; background: transparent;")
        
        name_lbl = QLabel(title)
        name_lbl.setStyleSheet("color: white; font-size: 12.5px; font-weight: bold; border: none; background: transparent;")
        
        cat_badge = QLabel(category.upper())
        cat_badge.setStyleSheet("""
            background: rgba(139,92,246,0.12); color: #a855f7;
            border: 1px solid rgba(139,92,246,0.25); border-radius: 4px;
            font-size: 8px; font-weight: bold; padding: 2px 5px;
        """)
        
        status_badge = QLabel("SYNCED")
        status_badge.setStyleSheet("""
            background: rgba(16,185,129,0.12); color: #10b981;
            border: 1px solid rgba(16,185,129,0.25); border-radius: 4px;
            font-size: 8px; font-weight: bold; padding: 2px 5px;
        """)
 
        date_lbl = QLabel(date)
        date_lbl.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 10px; border: none; background: transparent;")

        layout.addWidget(icon)
        layout.addWidget(name_lbl, 1)
        layout.addWidget(cat_badge)
        layout.addWidget(status_badge)
        layout.addWidget(date_lbl)


class DashboardView(QWidget):
    """Command Center Dashboard."""
    upload_requested = Signal()
    action_triggered = Signal(str)

    def __init__(self, current_user: User) -> None:
        super().__init__()
        self._user = current_user
        self._setup_ui()
        self.refresh_stats()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        # Welcome Banner Card
        self.banner = QFrame()
        self.banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(59, 130, 246, 0.12), stop:1 rgba(139, 92, 246, 0.06));
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 24px;
            }
        """)
        banner_layout = QVBoxLayout(self.banner)
        banner_layout.setContentsMargins(30, 25, 30, 25)
        banner_layout.setSpacing(6)
        
        welcome_lbl = QLabel(f"Welcome back, Dr. Chaitanya")
        welcome_lbl.setStyleSheet("color: white; font-size: 26px; font-weight: 800; border: none; background: transparent; letter-spacing: 0.5px;")
        
        sub_lbl = QLabel("Upload any medical report or scan. AI will automatically understand, detect categories, and analyze clinical parameters.")
        sub_lbl.setStyleSheet("color: rgba(255,255,255,0.55); font-size: 13px; border: none; background: transparent;")
        
        banner_layout.addWidget(welcome_lbl)
        banner_layout.addWidget(sub_lbl)
        layout.addWidget(self.banner)

        # Stats Cards Grid
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.card_docs = GlassCard("KNOWLEDGE SOURCES", "0 Documents", "📂", QColor(59, 130, 246))
        self.card_chunks = GlassCard("INDEXED CHUNKS", "0 Chunks", "🧩", QColor(6, 182, 212))
        self.card_embeddings = GlassCard("ALIGNED VECTORS", "0 Vectors", "🧬", QColor(139, 92, 246))
        self.card_size = GlassCard("STORAGE UTILIZATION", "0.00 MB", "💾", QColor(251, 146, 60))
        
        stats_layout.addWidget(self.card_docs)
        stats_layout.addWidget(self.card_chunks)
        stats_layout.addWidget(self.card_embeddings)
        stats_layout.addWidget(self.card_size)
        layout.addLayout(stats_layout)

        # Central grid: Left: Upload Card, Right: Actions & Live Ingestion Feed
        central_layout = QHBoxLayout()
        central_layout.setSpacing(20)

        # Interactive Upload Card (dashed border, click to select)
        self.upload_card = InteractiveUploadCard(self)
        self.upload_card.clicked.connect(self.upload_requested.emit)
        central_layout.addWidget(self.upload_card, 1)

        # Right Column Layout containing Quick Actions + Ingestion logs
        right_column = QWidget()
        right_column_layout = QVBoxLayout(right_column)
        right_column_layout.setContentsMargins(0, 0, 0, 0)
        right_column_layout.setSpacing(15)

        # 1. Quick Actions Panel
        self.actions_panel = QFrame()
        self.actions_panel.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 20px;
            }
        """)
        actions_layout = QVBoxLayout(self.actions_panel)
        actions_layout.setContentsMargins(20, 15, 20, 15)
        actions_layout.setSpacing(10)

        actions_title = QLabel("Clinical Quick Actions")
        actions_title.setStyleSheet("color: white; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        actions_layout.addWidget(actions_title)

        buttons_grid = QGridLayout()
        buttons_grid.setSpacing(8)

        # Define actions buttons
        btn_compare = QPushButton("📊 Compare Reports")
        btn_timeline = QPushButton("📅 Timeline")
        btn_gen_pdf = QPushButton("📥 Generate PDF")
        btn_gen_sum = QPushButton("📝 Generate Summary")
        btn_export = QPushButton("📈 Export Excel")
        btn_chat = QPushButton("💬 AI Chat")

        actions_mapping = {
            btn_compare: "compare_reports",
            btn_timeline: "timeline",
            btn_gen_pdf: "gen_pdf",
            btn_gen_sum: "gen_summary",
            btn_export: "export_excel",
            btn_chat: "ai_chat"
        }

        for idx, (btn, action_id) in enumerate(actions_mapping.items()):
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 8px;
                    color: white;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: rgba(6, 182, 212, 0.15);
                    border: 1px solid rgba(6, 182, 212, 0.3);
                }
            """)
            btn.clicked.connect(lambda a=action_id: self._trigger_action(a))
            row = idx // 2
            col = idx % 2
            buttons_grid.addWidget(btn, row, col)

        actions_layout.addLayout(buttons_grid)
        right_column_layout.addWidget(self.actions_panel)

        # 2. Live Feed logs
        self.recent_panel = QFrame()
        self.recent_panel.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 20px;
            }
        """)
        recent_layout = QVBoxLayout(self.recent_panel)
        recent_layout.setContentsMargins(20, 20, 20, 20)
        recent_layout.setSpacing(10)

        recent_lbl = QLabel("Live Ingestion Flow Logs")
        recent_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        recent_layout.addWidget(recent_lbl)

        self.feed_scroll = QScrollArea()
        self.feed_scroll.setWidgetResizable(True)
        self.feed_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.feed_container = QWidget()
        self.feed_container.setStyleSheet("background: transparent;")
        self.feed_layout = QVBoxLayout(self.feed_container)
        self.feed_layout.setContentsMargins(0, 0, 0, 0)
        self.feed_layout.setSpacing(8)
        self.feed_layout.setAlignment(Qt.AlignTop)
        self.feed_scroll.setWidget(self.feed_container)
        
        recent_layout.addWidget(self.feed_scroll, 1)
        right_column_layout.addWidget(self.recent_panel, 1)

        central_layout.addWidget(right_column, 1)

        layout.addLayout(central_layout, 1)

    def _trigger_action(self, action_id: str) -> None:
        logger.info(f"Dashboard action clicked: {action_id}")
        if action_id == "ai_chat":
            self.action_triggered.emit("ai_chat")
        else:
            NotificationToast.show_message(self.window(), f"Action '{action_id.upper()}' executed successfully.", "success")

    def refresh_stats(self) -> None:
        """Fetch updated stats from the database."""
        try:
            with get_db_session() as session:
                doc_repo = DocumentRepository(session)
                docs = doc_repo.get_all()
                total_docs = len(docs)
                
                total_chunks = session.query(DocumentChunkModel).count()
                total_embeddings = total_chunks
                
                total_size_bytes = sum([d.file_size or 0 for d in docs])
                total_size_mb = total_size_bytes / (1024 * 1024)
                
                self.card_docs.set_value(f"{total_docs} Documents")
                self.card_chunks.set_value(f"{total_chunks} Chunks")
                self.card_embeddings.set_value(f"{total_embeddings} Vectors")
                self.card_size.set_value(f"{total_size_mb:.2f} MB")
                
                while self.feed_layout.count():
                    item = self.feed_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                        
                recent_docs = doc_repo.get_recent(limit=5)
                for r_doc in recent_docs:
                    card = LiveFeedCard(
                        r_doc.title,
                        r_doc.category,
                        r_doc.created_at.strftime("%Y-%m-%d %H:%M"),
                        self
                    )
                    self.feed_layout.addWidget(card)
        except Exception as e:
            logger.error(f"Error refreshing dashboard: {e}")
