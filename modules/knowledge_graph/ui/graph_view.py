"""
MediVerse AI — Knowledge Graph Workspace.
Visualizes interconnected clinical entities (Guidelines, Symptoms, Pathogens, Treatments) using custom interactive 2D canvas drawing.
"""
from __future__ import annotations

import logging
import math
import random
from typing import Optional, List
from PySide6.QtCore import Qt, QPointF, QTimer, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient, QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSplitter
)

logger = logging.getLogger("mediverse.modules.graph")


class Node:
    def __init__(self, label: str, category: str, x: float, y: float, description: str):
        self.label = label
        self.category = category
        self.x = x
        self.y = y
        self.description = description
        
        # Physics / Animation vectors
        self.vx = random.uniform(-0.15, 0.15)
        self.vy = random.uniform(-0.15, 0.15)
        self.radius = 18.0
        self.glow_pulse = 0.0
        self.glow_dir = 1
        
        # Color mapping
        colors = {
            "pathogen": "#ef4444",   # red
            "guideline": "#06b6d4",  # cyan
            "symptom": "#fbbf24",    # yellow
            "treatment": "#10b981",  # green
        }
        self.color = QColor(colors.get(category, "#8b5cf6"))

    def update(self, width: int, height: int):
        self.x += self.vx
        self.y += self.vy

        # Limit node movements within borders
        margin = 40
        if self.x < margin or self.x > width - margin:
            self.vx *= -1
        if self.y < margin or self.y > height - margin:
            self.vy *= -1

        # Pulse glow aura
        self.glow_pulse += 0.03 * self.glow_dir
        if self.glow_pulse > 1.0:
            self.glow_pulse = 1.0
            self.glow_dir = -1
        elif self.glow_pulse < 0.0:
            self.glow_pulse = 0.0
            self.glow_dir = 1


class GraphCanvas(QWidget):
    """Custom interactive 2D canvas drawing medical node hierarchies."""
    node_selected = Signal(object) # Node

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(450)
        self.setMouseTracking(True)
        
        # Generate custom mock nodes
        self.nodes = [
            Node("Tuberculosis", "pathogen", 150, 150, "Infectious disease caused by Mycobacterium tuberculosis."),
            Node("ICMR Guidelines", "guideline", 250, 100, "Indian Council of Medical Research screening protocols."),
            Node("Rifampicin", "treatment", 180, 260, "Bactericidal antibiotic drug targeting RNA polymerase."),
            Node("Chronic Cough", "symptom", 70, 200, "Persistent cough symptom lasting more than 8 weeks."),
            Node("Hemoptysis", "symptom", 70, 90, "Coughing up blood originating from the respiratory tract."),
            
            Node("Sepsis Core", "pathogen", 450, 250, "Life-threatening organ dysfunction caused by a dysregulated host response to infection."),
            Node("Early IV Fluids", "treatment", 550, 310, "Rapid administration of crystalloid fluids to restore tissue perfusion."),
            Node("Lactate Test", "guideline", 350, 310, "Diagnostic measure of blood lactate levels to assess hypoperfusion.")
        ]
        
        # Node linkages (indices)
        self.edges = [
            (0, 1), (0, 2), (0, 3), (0, 4), # TB linkings
            (5, 6), (5, 7), (1, 7) # Sepsis linkings
        ]

        self.selected_node: Optional[Node] = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(30)

    def _animate(self) -> None:
        for node in self.nodes:
            node.update(self.width(), self.height())
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        self.selected_node = None
        
        for node in self.nodes:
            dist = math.hypot(node.x - pos.x(), node.y - pos.y())
            if dist <= node.radius + 5:
                self.selected_node = node
                self.node_selected.emit(node)
                break
        
        self.update()
        event.accept()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw connections (edges)
        for u, v in self.edges:
            n1 = self.nodes[u]
            n2 = self.nodes[v]
            
            painter.setPen(QPen(QColor(255, 255, 255, 25), 1.2))
            # Glowing connection indicator
            if n1 == self.selected_node or n2 == self.selected_node:
                painter.setPen(QPen(QColor(6, 182, 212, 160), 2.0))
            painter.drawLine(QPointF(n1.x, n1.y), QPointF(n2.x, n2.y))

        # Draw nodes
        for node in self.nodes:
            # Pulsing outer glow aura
            glow_radius = node.radius + 6.0 + int(node.glow_pulse * 4)
            radial = QRadialGradient(node.x, node.y, glow_radius)
            radial.setColorAt(0.0, QColor(node.color.red(), node.color.green(), node.color.blue(), 100))
            radial.setColorAt(0.8, QColor(node.color.red(), node.color.green(), node.color.blue(), 20))
            radial.setColorAt(1.0, QColor(0, 0, 0, 0))
            
            painter.setBrush(QBrush(radial))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(node.x, node.y), glow_radius, glow_radius)

            # Node inner base circle
            painter.setBrush(QBrush(node.color))
            if node == self.selected_node:
                painter.setPen(QPen(QColor(255, 255, 255), 2.5))
            else:
                painter.setPen(QPen(QColor(255, 255, 255, 120), 1.0))
            painter.drawEllipse(QPointF(node.x, node.y), node.radius, node.radius)

            # Draw initials
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(
                QRectF(node.x - node.radius, node.y - node.radius, node.radius * 2, node.radius * 2),
                Qt.AlignCenter, node.label[:2].upper()
            )

            # Draw labels under node
            painter.setPen(QColor(255, 255, 255, 150))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(node.x - 60, node.y + node.radius + 14, 120, 20, Qt.AlignCenter, node.label)


class KnowledgeGraphView(QWidget):
    """Relational knowledge graph mapping workspace."""
    
    def __init__(self, current_user: User) -> None:
        super().__init__()
        self._user = current_user
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        # Header Area
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Knowledge Relation Graph")
        title.setStyleSheet("color: white; font-size: 26px; font-weight: 800; letter-spacing: 0.5px;")
        sub = QLabel("Explore the visual entity connections between pathogens, guidelines, drug options, and patient symptoms.")
        sub.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        layout.addLayout(header)

        # Splitter Layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: rgba(255, 255, 255, 0.05);
                width: 2px;
            }
        """)

        # Canvas Widget (Left)
        canvas_box = QFrame()
        canvas_box.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 16px;
            }
        """)
        canvas_layout = QVBoxLayout(canvas_box)
        canvas_layout.setContentsMargins(10, 10, 10, 10)
        
        self.canvas = GraphCanvas(self)
        self.canvas.node_selected.connect(self._on_node_selected)
        canvas_layout.addWidget(self.canvas, 1)
        splitter.addWidget(canvas_box)

        # Details Panel Widget (Right)
        self.details_box = QFrame()
        self.details_box.setFixedWidth(280)
        self.details_box.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 16px;
            }
        """)
        details_layout = QVBoxLayout(self.details_box)
        details_layout.setContentsMargins(20, 20, 20, 20)
        details_layout.setSpacing(15)

        self.node_lbl = QLabel("Select a Node")
        self.node_lbl.setStyleSheet("color: white; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        details_layout.addWidget(self.node_lbl)

        self.cat_badge = QLabel("CATEGORY: IDLE")
        self.cat_badge.setStyleSheet("""
            background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.6);
            border-radius: 4px; padding: 3px 8px; font-size: 9px; font-weight: bold;
        """)
        self.cat_badge.setWordWrap(True)
        details_layout.addWidget(self.cat_badge)

        self.desc_lbl = QLabel("Click on any node in the graph relation canvas to inspect details, links, and clinical summaries.")
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 12px; border: none; line-height: 1.5;")
        details_layout.addWidget(self.desc_lbl)

        details_layout.addStretch()
        splitter.addWidget(self.details_box)

        splitter.setSizes([720, 280])
        layout.addWidget(splitter, 1)

    def _on_node_selected(self, node: Node) -> None:
        self.node_lbl.setText(node.label)
        self.cat_badge.setText(f"CATEGORY: {node.category.upper()}")
        self.cat_badge.setStyleSheet(f"""
            background: rgba({node.color.red()}, {node.color.green()}, {node.color.blue()}, 0.12);
            color: {node.color.name()};
            border: 1px solid rgba({node.color.red()}, {node.color.green()}, {node.color.blue()}, 0.3);
            border-radius: 4px; padding: 4px 8px; font-size: 9px; font-weight: bold;
        """)
        self.desc_lbl.setText(node.description)
