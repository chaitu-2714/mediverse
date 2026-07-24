"""
MediVerse AI — Interactive Human Anatomy Navigator.
A high-fidelity glassmorphic interactive anatomy visualizer drawn with QPainter,
supporting custom organ hover states, highlights, and click actions.
"""
from __future__ import annotations

import logging
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QRadialGradient, QPainterPath
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout

logger = logging.getLogger("mediverse.modules.imaging_analysis.ui.anatomy")


class AnatomyNavigatorWidget(QFrame):
    """Visual vector human anatomy interactive selection panel."""
    organ_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(350)
        self.setStyleSheet("""
            QFrame {
                background: #060810;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
            }
        """)

        # Organ coordinate mappings (assumed canvas size: width x height)
        # Coordinates will scale dynamically during paintEvent
        self.organs = {
            "Brain": {"cx": 150, "cy": 45, "rad": 16, "icon": "🧠", "label": "Brain & Nervous System"},
            "Lungs": {"cx": 150, "cy": 105, "rad": 20, "icon": "🫁", "label": "Lungs & Respiratory"},
            "Heart": {"cx": 140, "cy": 115, "rad": 15, "icon": "🫀", "label": "Cardiovascular Heart"},
            "Liver": {"cx": 135, "cy": 145, "rad": 16, "icon": "🥩", "label": "Liver & Hepatic Node"},
            "Kidneys": {"cx": 150, "cy": 165, "rad": 15, "icon": "🍢", "label": "Kidneys & Urinary"},
            "Spine": {"cx": 150, "cy": 200, "rad": 14, "icon": "🦴", "label": "Spine & Skeletal Joint"},
            "Knee": {"cx": 150, "cy": 275, "rad": 14, "icon": "🦵", "label": "Knee Joint & Ligament"},
            "Blood": {"cx": 150, "cy": 220, "rad": 16, "icon": "🧪", "label": "Blood Biomarkers"}
        }

        self.highlighted_organ: Optional[str] = None
        self.hovered_organ: Optional[str] = None
        
        # Glow pulse timer
        self.glow_val = 120
        self.glow_dir = 5
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._update_pulse)
        self.pulse_timer.start(50)

    def _update_pulse(self) -> None:
        self.glow_val += self.glow_dir
        if self.glow_val >= 230 or self.glow_val <= 110:
            self.glow_dir = -self.glow_dir
        if self.highlighted_organ:
            self.update()

    def highlight_organ(self, organ_name: str) -> None:
        """Highlights the corresponding organ programmatically after AI analysis."""
        normalized = organ_name.title()
        if normalized in self.organs:
            self.highlighted_organ = normalized
            logger.info(f"Anatomy Navigator auto-highlighting: {normalized}")
        else:
            self.highlighted_organ = None
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        w, h = rect.width(), rect.height()
        
        # Draw background coordinate grid
        painter.setPen(QPen(QColor(255,255,255,6), 1))
        for gx in range(0, w, 40):
            painter.drawLine(gx, 0, gx, h)
        for gy in range(0, h, 40):
            painter.drawLine(0, gy, w, gy)

        # Scale elements
        scale_x = w / 300.0
        scale_y = h / 350.0

        # Draw a premium vector Human Body Outline
        painter.setPen(QPen(QColor(255, 255, 255, 20), 2))
        painter.setBrush(QBrush(QColor(255, 255, 255, 3)))
        
        # Draw stylized head, torso, limbs
        body_path = QPainterPath()
        # Head
        body_path.addEllipse(QPointF(150 * scale_x, 45 * scale_y), 24 * scale_x, 24 * scale_y)
        # Neck
        body_path.moveTo(142 * scale_x, 69 * scale_y)
        body_path.lineTo(142 * scale_x, 80 * scale_y)
        body_path.lineTo(158 * scale_x, 80 * scale_y)
        body_path.lineTo(158 * scale_x, 69 * scale_y)
        # Torso / Chest
        body_path.addRoundedRect(115 * scale_x, 80 * scale_y, 70 * scale_x, 110 * scale_y, 10, 10)
        # Legs
        body_path.addRoundedRect(120 * scale_x, 190 * scale_y, 22 * scale_x, 120 * scale_y, 8, 8)
        body_path.addRoundedRect(158 * scale_x, 190 * scale_y, 22 * scale_x, 120 * scale_y, 8, 8)
        # Arms
        body_path.addRoundedRect(92 * scale_x, 82 * scale_y, 20 * scale_x, 90 * scale_y, 8, 8)
        body_path.addRoundedRect(188 * scale_x, 82 * scale_y, 20 * scale_x, 90 * scale_y, 8, 8)
        
        painter.drawPath(body_path)

        # Draw Organ Hotspot Nodes
        for name, data in self.organs.items():
            cx = data["cx"] * scale_x
            cy = data["cy"] * scale_y
            rad = data["rad"] * min(scale_x, scale_y)

            # Node glow background if highlighted
            if self.highlighted_organ == name:
                grad = QRadialGradient(cx, cy, rad * 2.0)
                grad.setColorAt(0.0, QColor(6, 182, 212, self.glow_val))
                grad.setColorAt(0.6, QColor(6, 182, 212, 60))
                grad.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(grad))
                painter.drawEllipse(QPointF(cx, cy), rad * 2.2, rad * 2.2)

                # Outer ring line
                painter.setPen(QPen(QColor(6, 182, 212), 2))
            elif self.hovered_organ == name:
                painter.setPen(QPen(QColor(139, 92, 246), 2)) # Purple for hover
            else:
                painter.setPen(QPen(QColor(255, 255, 255, 60), 1.5))
            
            # Draw core circle
            painter.setBrush(QBrush(QColor(10, 15, 26, 230)))
            painter.drawEllipse(QPointF(cx, cy), rad, rad)

            # Draw icon/character center
            painter.setPen(QColor(255, 255, 255, 220))
            painter.setFont(QFont("Segoe UI", int(rad * 0.95)))
            painter.drawText(QRectF(cx - rad, cy - rad, rad * 2, rad * 2), Qt.AlignCenter, data["icon"])

        # Draw Hover Card/Tooltip if hovering
        if self.hovered_organ:
            data = self.organs[self.hovered_organ]
            painter.setPen(QPen(QColor(139, 92, 246, 120), 1))
            painter.setBrush(QBrush(QColor(15, 12, 26, 240)))
            
            card_rect = QRectF(w * 0.05, h * 0.88, w * 0.9, h * 0.09)
            painter.drawRoundedRect(card_rect, 6, 6)
            
            painter.setPen(QColor(255,255,255,220))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(card_rect, Qt.AlignCenter, f"{data['icon']} {data['label']} (Click to Inspect)")
            
        elif self.highlighted_organ:
            # Show highlighted organ card
            data = self.organs[self.highlighted_organ]
            painter.setPen(QPen(QColor(6, 182, 212, 120), 1))
            painter.setBrush(QBrush(QColor(6, 20, 26, 240)))
            
            card_rect = QRectF(w * 0.05, h * 0.88, w * 0.9, h * 0.09)
            painter.drawRoundedRect(card_rect, 6, 6)
            
            painter.setPen(QColor(6, 182, 212))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(card_rect, Qt.AlignCenter, f"AUTO-DETECTED FINDING: {data['label']}")

        painter.end()

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        w, h = self.width(), self.height()
        scale_x = w / 300.0
        scale_y = h / 350.0
        
        found = None
        for name, data in self.organs.items():
            cx = data["cx"] * scale_x
            cy = data["cy"] * scale_y
            rad = data["rad"] * min(scale_x, scale_y)
            
            dist = ((pos.x() - cx)**2 + (pos.y() - cy)**2)**0.5
            if dist <= rad:
                found = name
                break
                
        if found != self.hovered_organ:
            self.hovered_organ = found
            self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.hovered_organ:
            self.highlighted_organ = self.hovered_organ
            self.organ_selected.emit(self.hovered_organ)
            self.update()
        super().mousePressEvent(event)
