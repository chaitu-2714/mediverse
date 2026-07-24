"""
MediVerse AI — Redesigned Sidebar & Diagnostics Panel.
Contains expanded navigation nodes and the circular diagnostics status rings.
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal, QRectF, QPointF
from PySide6.QtGui import QCursor, QIcon, QPainter, QColor, QFont, QConicalGradient, QPen, QBrush, QRadialGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QGridLayout
)

from config.constants import SIDEBAR_WIDTH_EXPANDED, SIDEBAR_WIDTH_COLLAPSED


class CircularProgressIndicator(QWidget):
    """Draws a premium glowing circular progress or connection status widget."""
    
    def __init__(self, label: str, value: float = 0.0, is_status: bool = False, status_color: str = "#06b6d4", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.label = label
        self.value = value
        self.is_status = is_status
        self.status_color = QColor(status_color)
        self.setFixedSize(65, 80)

    def set_value(self, val: float) -> None:
        self.value = max(0.0, min(100.0, val))
        self.update()

    def set_status_color(self, hex_color: str) -> None:
        self.status_color = QColor(hex_color)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        cx = rect.width() / 2.0
        cy = 30.0
        radius = 20.0
        draw_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        # Track line
        painter.setPen(QPen(QColor(255, 255, 255, 8), 3.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(draw_rect)

        if self.is_status:
            # Full glowing dot represent core connections
            glow = QRadialGradient(cx, cy, radius)
            glow.setColorAt(0.0, QColor(self.status_color.red(), self.status_color.green(), self.status_color.blue(), 60))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(draw_rect)

            painter.setBrush(QBrush(self.status_color))
            painter.drawEllipse(QPointF(cx, cy), 5.5, 5.5)
        else:
            # Draw progress ring
            glow_grad = QConicalGradient(cx, cy, 90)
            glow_grad.setColorAt(0.0, self.status_color)
            glow_grad.setColorAt(self.value / 100.0, QColor(self.status_color.red(), self.status_color.green(), self.status_color.blue(), 30))
            glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            
            painter.setPen(QPen(QBrush(glow_grad), 3.5, Qt.SolidLine, Qt.RoundCap))
            span_angle = -int((self.value / 100.0) * 360 * 16)
            painter.drawArc(draw_rect, 90 * 16, span_angle)

            # Center text percentage
            painter.setPen(QColor(255, 255, 255, 220))
            painter.setFont(QFont("Consolas", 8, QFont.Bold))
            painter.drawText(draw_rect, Qt.AlignCenter, f"{int(self.value)}")

        # Label drawing
        painter.setPen(QColor(255, 255, 255, 120))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        lbl_rect = QRectF(0, 56, rect.width(), 20)
        painter.drawText(lbl_rect, Qt.AlignCenter, self.label)
        painter.end()


class SidebarButton(QPushButton):
    """A single navigation item in the sidebar."""
    def __init__(self, icon_str: str, text: str, module_id: str, is_active: bool = False):
        super().__init__()
        self.module_id = module_id
        self._text = text
        self._icon_str = icon_str
        self._is_active = is_active
        self._expanded = True
        
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(38)
        self._update_style()

    def set_active(self, active: bool) -> None:
        if self._is_active != active:
            self._is_active = active
            self._update_style()

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._update_style()

    def _update_style(self) -> None:
        if self._expanded:
            self.setText(f"   {self._icon_str}     {self._text}")
            self.setStyleSheet(self._get_expanded_style())
        else:
            self.setText(self._icon_str)
            self.setStyleSheet(self._get_collapsed_style())

    def _get_expanded_style(self) -> str:
        bg = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(59, 130, 246, 0.15), stop:1 rgba(99, 102, 241, 0.02))" if self._is_active else "transparent"
        border = "border-left: 3px solid #06b6d4;" if self._is_active else "border-left: 3px solid transparent;"
        color = "#06b6d4" if self._is_active else "rgba(255,255,255,0.65)"
        weight = "bold" if self._is_active else "500"
        
        return f"""
            QPushButton {{
                background: {bg};
                color: {color};
                {border}
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: {weight};
                text-align: left;
                padding-left: 12px;
                border-radius: 6px;
                margin: 1px 8px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.04);
                color: white;
            }}
        """

    def _get_collapsed_style(self) -> str:
        bg = "rgba(59, 130, 246, 0.15)" if self._is_active else "transparent"
        border = "border-left: 3px solid #06b6d4;" if self._is_active else "border-left: 3px solid transparent;"
        color = "#06b6d4" if self._is_active else "rgba(255,255,255,0.6)"
        
        return f"""
            QPushButton {{
                background: {bg};
                color: {color};
                {border}
                font-size: 15px;
                text-align: center;
                padding: 0;
                border-radius: 6px;
                margin: 2px 6px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.04);
                color: white;
            }}
        """


class AnimatedSidebar(QFrame):
    """Sidebar containing navigation buttons and diagnostic stats panel."""
    
    module_selected = Signal(str)  # module_id

    def __init__(self) -> None:
        super().__init__()
        self._expanded = True
        self._buttons: dict[str, SidebarButton] = {}
        self._setup_ui()
        self._setup_animation()

    def _setup_ui(self) -> None:
        self.setFixedWidth(260) # Expanded width fits rings perfectly
        self.setStyleSheet("""
            QFrame {
                background: rgba(8, 12, 28, 0.6); 
                border-right: 1px solid rgba(255,255,255,0.06);
            }
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 15, 0, 15)
        self.main_layout.setSpacing(4)

        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(12, 0, 12, 0)
        
        self.logo_title = QLabel("⚕ MEDIVERSE")
        self.logo_title.setStyleSheet("color: white; font-size: 14px; font-weight: 900; letter-spacing: 1px;")
        header_layout.addWidget(self.logo_title)
        header_layout.addStretch()

        self._toggle_btn = QPushButton("≡")
        self._toggle_btn.setFixedSize(32, 32)
        self._toggle_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: rgba(255,255,255,0.6);
                font-size: 20px; border: none;
            }
            QPushButton:hover { color: white; }
        """)
        self._toggle_btn.clicked.connect(self.toggle)
        header_layout.addWidget(self._toggle_btn)
        
        self.main_layout.addLayout(header_layout)
        self.main_layout.addSpacing(10)

        # Navigation Area Container
        self.nav_widget = QWidget()
        self.nav_widget.setStyleSheet("background: transparent; border: none;")
        self.nav_layout = QVBoxLayout(self.nav_widget)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(2)
        self.main_layout.addWidget(self.nav_widget)

        self.main_layout.addStretch(1)

        # ── Left Information Panel: Diagnostics Widget ──
        self.info_panel = None

    def _setup_animation(self) -> None:
        self._anim = QPropertyAnimation(self, b"minimumWidth")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        self._anim_max = QPropertyAnimation(self, b"maximumWidth")
        self._anim_max.setDuration(220)
        self._anim_max.setEasingCurve(QEasingCurve.InOutQuad)

    def add_module(self, module_id: str, icon: str, text: str, is_active: bool = False) -> None:
        btn = SidebarButton(icon, text, module_id, is_active)
        btn.clicked.connect(lambda: self._on_btn_clicked(module_id))
        self._buttons[module_id] = btn
        self.nav_layout.addWidget(btn)

    def add_spacer(self) -> None:
        self.nav_layout.addStretch(1)

    def _on_btn_clicked(self, module_id: str) -> None:
        self.set_active(module_id)
        self.module_selected.emit(module_id)

    def set_active(self, module_id: str) -> None:
        for mid, btn in self._buttons.items():
            btn.set_active(mid == module_id)

    def update_diagnostics(self, db_ok: bool, chroma_ok: bool, ollama_ok: bool, embed_pct: float, storage_pct: float, docs_cnt: int, chunks_cnt: int, storage_mb: float):
        """Update diagnostics widgets from parent MainWindow checks."""
        pass

    def toggle(self) -> None:
        self._expanded = not self._expanded
        target_w = 260 if self._expanded else 60
        
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(target_w)
        self._anim.start()
        
        self._anim_max.setStartValue(self.width())
        self._anim_max.setEndValue(target_w)
        self._anim_max.start()
        
        for btn in self._buttons.values():
            btn.set_expanded(self._expanded)

        if self._expanded:
            self.logo_title.show()
            if self.info_panel:
                self.info_panel.show()
        else:
            self.logo_title.hide()
            if self.info_panel:
                self.info_panel.hide()
