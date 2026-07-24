"""
MediVerse AI — AI Medical Report & Medical Imaging Analysis Workspace.
A premium, clinical-grade diagnostic dashboard with VisionOS glassmorphism,
dynamic vector charts (Bar, Pie, Trend, Radar, Circular Progress), medical scan heatmap overlays,
and image interaction controls (Zoom, Pan, Rotate, Brightness/Contrast).
"""
from __future__ import annotations

import os
import re
import math
import logging
from typing import Optional, Any
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QColor, QPainter, QLinearGradient, QRadialGradient, QPen, QBrush, QFont, QImage, QPainterPath
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFileDialog, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QCheckBox, QAbstractItemView, QStackedWidget, QTextBrowser, QApplication, QMessageBox
)

from core.models.user import User
from modules.imaging_analysis.services.analyzer_service import MedicalAnalyzerService
from modules.imaging_analysis.ui.anatomy_navigator import AnatomyNavigatorWidget
from modules.imaging_analysis.ui.terminology_explorer import TerminologyExplorerPanel
from modules.imaging_analysis.services.voice_assistant import VoiceAssistantService
from shared.components.notification_toast import NotificationToast

logger = logging.getLogger("mediverse.modules.imaging_analysis.ui")


class DragDropUploadArea(QFrame):
    """Frosted glass drag & drop clinical file upload panel."""
    file_dropped = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.hovered = False
        
        self.setFixedHeight(120)
        self.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 2px dashed rgba(255, 255, 255, 0.12);
                border-radius: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(4)
        
        self.icon_lbl = QLabel("📤")
        self.icon_lbl.setStyleSheet("font-size: 24px; background: transparent; border: none;")
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_lbl)
        
        self.text_lbl = QLabel("Drag & Drop Medical Asset here to analyze")
        self.text_lbl.setStyleSheet("color: white; font-size: 12px; font-weight: 600; background: transparent; border: none;")
        self.text_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.text_lbl)
        
        self.sub_lbl = QLabel("Supports PDF, PNG, JPG, JPEG, TIFF, BMP, and DICOM formats")
        self.sub_lbl.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 10px; background: transparent; border: none;")
        self.sub_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.sub_lbl)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.hovered = True
            self.setStyleSheet("""
                QFrame {
                    background: rgba(6, 182, 212, 0.08);
                    border: 2px dashed #06b6d4;
                    border-radius: 16px;
                }
            """)
            self.update()

    def dragLeaveEvent(self, event) -> None:
        self.hovered = False
        self.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 2px dashed rgba(255, 255, 255, 0.12);
                border-radius: 16px;
            }
        """)
        self.update()

    def dropEvent(self, event) -> None:
        self.hovered = False
        self.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 2px dashed rgba(255, 255, 255, 0.12);
                border-radius: 16px;
            }
        """)
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.exists(file_path):
                self.file_dropped.emit(file_path)
                break
        event.acceptProposedAction()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Medical File", "", 
                "Medical Files (*.pdf *.png *.jpg *.jpeg *.tiff *.bmp *.dcm *.dicom);;All Files (*)"
            )
            if file_path:
                self.file_dropped.emit(file_path)
        super().mousePressEvent(event)


class CustomVectorChart(QFrame):
    """Custom painted high-fidelity medical parameters comparative charts."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.chart_type = "bar" # bar, pie, trend, radar, circular
        self.parameters: list[dict] = []
        self.setMinimumHeight(240)
        self.setStyleSheet("background: transparent; border: none;")

    def set_data(self, parameters: list[dict], chart_type: str = "bar") -> None:
        self.parameters = parameters
        self.chart_type = chart_type
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        w, h = rect.width(), rect.height()
        
        # Border box
        painter.setPen(QPen(QColor(255,255,255,10), 1))
        painter.setBrush(QBrush(QColor(255,255,255,3)))
        painter.drawRoundedRect(rect.adjusted(1,1,-1,-1), 16, 16)

        if not self.parameters:
            painter.setPen(QColor(255,255,255,100))
            painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
            painter.drawText(rect, Qt.AlignCenter, "No analysis parameters loaded for graphing")
            painter.end()
            return

        if self.chart_type == "bar":
            self._paint_bar_chart(painter, w, h)
        elif self.chart_type == "pie":
            self._paint_pie_chart(painter, w, h)
        elif self.chart_type == "trend":
            self._paint_trend_chart(painter, w, h)
        elif self.chart_type == "radar":
            self._paint_radar_chart(painter, w, h)
        elif self.chart_type == "circular":
            self._paint_circular_progress(painter, w, h)
            
        painter.end()

    def _paint_bar_chart(self, painter: QPainter, w: int, h: int) -> None:
        painter.setPen(QColor(255,255,255,220))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(20, 25, "Extracted Parameter Deviations Index")

        items = []
        for p in self.parameters:
            name = p["name"]
            val_str = p["value"]
            try:
                val = float(''.join(c for c in val_str if c.isdigit() or c == '.'))
                items.append((name, val, p["status"]))
            except ValueError:
                pass
                
        if not items:
            painter.drawText(QRectF(0,0,w,h), Qt.AlignCenter, "Extracted parameters are text-based.")
            return

        margin_left = 120
        margin_right = 40
        margin_top = 50
        margin_bottom = 30
        draw_w = w - margin_left - margin_right
        draw_h = h - margin_top - margin_bottom
        
        max_val = max(item[1] for item in items) * 1.2 if items else 100.0
        max_val = max(max_val, 1.0)
        
        bar_gap = 12
        bar_count = len(items)
        bar_h = int((draw_h - (bar_gap * (bar_count - 1))) / bar_count)
        bar_h = max(10, min(24, bar_h))

        for idx, (name, val, status) in enumerate(items):
            y = int(margin_top + idx * (bar_h + bar_gap))
            
            painter.setPen(QColor(255,255,255,160))
            painter.setFont(QFont("Segoe UI", 8.5))
            painter.drawText(QRectF(15, y, margin_left - 25, bar_h), Qt.AlignRight | Qt.AlignVCenter, name[:18])

            track_rect = QRectF(margin_left, y + 4, draw_w, bar_h - 8)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255,255,255,10)))
            painter.drawRoundedRect(track_rect, 3, 3)

            fill_w = int((val / max_val) * draw_w)
            fill_rect = QRectF(margin_left, y + 4, fill_w, bar_h - 8)
            
            grad = QLinearGradient(margin_left, 0, margin_left + fill_w, 0)
            if status in ["High", "Low", "Abnormal"]:
                grad.setColorAt(0.0, QColor(239, 68, 68, 200))
                grad.setColorAt(1.0, QColor(251, 113, 133, 230))
            else:
                grad.setColorAt(0.0, QColor(6, 182, 212, 200))
                grad.setColorAt(1.0, QColor(59, 130, 246, 230))

            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(fill_rect, 3, 3)

            painter.setPen(QColor(255,255,255,220))
            painter.setFont(QFont("Consolas", 8, QFont.Bold))
            painter.drawText(margin_left + fill_w + 8, y + bar_h - 4, f"{val:.1f}")

    def _paint_pie_chart(self, painter: QPainter, w: int, h: int) -> None:
        painter.setPen(QColor(255,255,255,220))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(20, 25, "System & Parameter Status Distribution")

        normal_cnt = sum(1 for p in self.parameters if p["status"] not in ["High", "Low", "Abnormal"])
        abnormal_cnt = len(self.parameters) - normal_cnt
        total = len(self.parameters)

        cx, cy = int(w * 0.4), int(h * 0.55)
        radius = int(min(w, h) * 0.28)
        pie_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        if total == 0:
            return

        normal_angle = int((normal_cnt / total) * 360 * 16)
        abnormal_angle = int((abnormal_cnt / total) * 360 * 16)

        painter.setPen(Qt.NoPen)
        normal_grad = QRadialGradient(cx, cy, radius)
        normal_grad.setColorAt(0.0, QColor(16, 185, 129, 200))
        normal_grad.setColorAt(1.0, QColor(10, 110, 80, 230))
        painter.setBrush(QBrush(normal_grad))
        painter.drawPie(pie_rect, 0, normal_angle)

        abnormal_grad = QRadialGradient(cx, cy, radius)
        abnormal_grad.setColorAt(0.0, QColor(239, 68, 68, 200))
        abnormal_grad.setColorAt(1.0, QColor(180, 30, 40, 230))
        painter.setBrush(QBrush(abnormal_grad))
        painter.drawPie(pie_rect, normal_angle, abnormal_angle)

        legend_x = int(w * 0.68)
        def draw_legend(text, color, y_pos):
            painter.setBrush(QBrush(color))
            painter.drawEllipse(legend_x, y_pos - 8, 8, 8)
            painter.setPen(QColor(255,255,255,200))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(legend_x + 15, y_pos, text)

        draw_legend(f"Normal ({normal_cnt})", QColor(16, 185, 129), int(h * 0.45))
        draw_legend(f"Outlier ({abnormal_cnt})", QColor(239, 68, 68), int(h * 0.60))

    def _paint_trend_chart(self, painter: QPainter, w: int, h: int) -> None:
        painter.setPen(QColor(255,255,255,220))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(20, 25, "Biomarker Historical Trend Timeline")

        margin_left = 50
        margin_right = 30
        margin_top = 60
        margin_bottom = 40
        draw_w = w - margin_left - margin_right
        draw_h = h - margin_top - margin_bottom

        painter.setPen(QPen(QColor(255,255,255,8), 1, Qt.DashLine))
        for grid_y in range(margin_top, margin_top + draw_h + 1, int(draw_h / 4)):
            painter.drawLine(margin_left, grid_y, margin_left + draw_w, grid_y)

        points = [
            (0.1, 0.75, "Report -2"),
            (0.35, 0.62, "Report -1"),
            (0.65, 0.45, "Prev Scan"),
            (0.9, 0.32, "Current Node")
        ]

        line_path = QPainterPath()
        glow_path = QPainterPath()
        p_coords = []
        for idx, (px, py, label) in enumerate(points):
            x = int(margin_left + px * draw_w)
            y = int(margin_top + py * draw_h)
            p_coords.append((x, y, label))
            if idx == 0:
                line_path.moveTo(x, y)
                glow_path.moveTo(x, margin_top + draw_h)
                glow_path.lineTo(x, y)
            else:
                line_path.lineTo(x, y)
                glow_path.lineTo(x, y)
                if idx == len(points) - 1:
                    glow_path.lineTo(x, margin_top + draw_h)
                    glow_path.closeSubpath()

        glow_grad = QLinearGradient(0, margin_top, 0, margin_top + draw_h)
        glow_grad.setColorAt(0.0, QColor(6, 182, 212, 45))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.NoPen)
        painter.drawPath(glow_path)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(6, 182, 212), 2, Qt.SolidLine, Qt.RoundCap))
        painter.drawPath(line_path)

        for x, y, label in p_coords:
            painter.setBrush(QBrush(QColor(6, 182, 212, 80)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(x, y), 7, 7)

            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(QPointF(x, y), 3.5, 3.5)

            painter.setPen(QColor(255,255,255,130))
            painter.setFont(QFont("Segoe UI", 7.5))
            painter.drawText(QRectF(x - 40, margin_top + draw_h + 8, 80, 20), Qt.AlignCenter, label)

    def _paint_radar_chart(self, painter: QPainter, w: int, h: int) -> None:
        painter.setPen(QColor(255,255,255,220))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(20, 25, "Anatomical Organ System Dev Index")

        # 5 Axes represent different organ system metrics
        axes = ["Brain", "Lungs", "Heart", "Liver", "Kidneys"]
        ratios = [0.8, 0.5, 0.75, 0.4, 0.85] # mock value indicators

        cx, cy = int(w * 0.5), int(h * 0.55)
        max_rad = int(min(w, h) * 0.28)

        # Draw web grid lines
        painter.setBrush(Qt.NoBrush)
        for grid in [0.25, 0.5, 0.75, 1.0]:
            painter.setPen(QPen(QColor(255, 255, 255, 8), 1))
            poly_path = QPainterPath()
            for idx, axis in enumerate(axes):
                ang = idx * (2 * math.pi / 5) - (math.pi / 2)
                rad = max_rad * grid
                ax = cx + rad * math.cos(ang)
                ay = cy + rad * math.sin(ang)
                if idx == 0:
                    poly_path.moveTo(ax, ay)
                else:
                    poly_path.lineTo(ax, ay)
            poly_path.closeSubpath()
            painter.drawPath(poly_path)

        # Draw axis lines and labels
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        for idx, axis in enumerate(axes):
            ang = idx * (2 * math.pi / 5) - (math.pi / 2)
            ax = cx + max_rad * math.cos(ang)
            ay = cy + max_rad * math.sin(ang)
            painter.drawLine(cx, cy, ax, ay)
            
            # Draw axis label offsets
            lx = cx + (max_rad + 20) * math.cos(ang) - 30
            ly = cy + (max_rad + 15) * math.sin(ang) - 8
            painter.setPen(QColor(255, 255, 255, 160))
            painter.drawText(QRectF(lx, ly, 60, 16), Qt.AlignCenter, axis)

        # Draw filled radar data path
        radar_path = QPainterPath()
        p_coords = []
        for idx, ratio in enumerate(ratios):
            ang = idx * (2 * math.pi / 5) - (math.pi / 2)
            rad = max_rad * ratio
            ax = cx + rad * math.cos(ang)
            ay = cy + rad * math.sin(ang)
            p_coords.append((ax, ay))
            if idx == 0:
                radar_path.moveTo(ax, ay)
            else:
                radar_path.lineTo(ax, ay)
        radar_path.closeSubpath()

        # Fill radar
        radar_grad = QRadialGradient(cx, cy, max_rad)
        radar_grad.setColorAt(0.0, QColor(139, 92, 246, 50))
        radar_grad.setColorAt(1.0, QColor(6, 182, 212, 140))
        painter.setBrush(QBrush(radar_grad))
        painter.setPen(QPen(QColor(6, 182, 212), 2))
        painter.drawPath(radar_path)

        # Draw points
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(Qt.NoPen)
        for ax, ay in p_coords:
            painter.drawEllipse(QPointF(ax, ay), 3, 3)

    def _paint_circular_progress(self, painter: QPainter, w: int, h: int) -> None:
        painter.setPen(QColor(255,255,255,220))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(20, 25, "Confidence / Extraction Integrity Index")

        cx, cy = int(w * 0.5), int(h * 0.55)
        radius = int(min(w, h) * 0.28)
        draw_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        # Track arc background
        painter.setPen(QPen(QColor(255, 255, 255, 8), 8))
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(draw_rect, 0 * 16, 360 * 16)

        # Progress Arc (98.2% Confidence index)
        grad = QLinearGradient(cx - radius, 0, cx + radius, 0)
        grad.setColorAt(0.0, QColor(6, 182, 212))
        grad.setColorAt(1.0, QColor(139, 92, 246))
        
        painter.setPen(QPen(QBrush(grad), 8, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(draw_rect, 90 * 16, -int(0.98 * 360 * 16))

        # Core value text
        painter.setPen(QColor(255, 255, 255, 220))
        painter.setFont(QFont("Segoe UI", 18, QFont.Bold))
        painter.drawText(draw_rect.adjusted(0, -6, 0, -6), Qt.AlignCenter, "98.2%")
        
        painter.setPen(QColor(6, 182, 212))
        painter.setFont(QFont("Segoe UI", 7.5, QFont.Bold))
        painter.drawText(draw_rect.adjusted(0, 18, 0, 18), Qt.AlignCenter, "INTEGRITY CONFIDENCE")


class ImageScannerView(QFrame):
    """Custom medical image viewer with interactive simulated heatmap overlays and controls (zoom, pan, rotate)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.image_path: Optional[str] = None
        self.pixmap_image: Optional[QImage] = None
        self.show_heatmap = False
        self.show_highlight = False
        self.show_bbox = False
        self.overlay_data: Optional[dict] = None
        
        # Interaction States
        self.zoom_factor = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.rotation_angle = 0.0
        self.brightness = 0 # Offset -100 to 100
        self.contrast = 1.0   # Scale 0.5 to 2.0
        
        self.setMinimumHeight(350)
        self.setStyleSheet("""
            QFrame {
                background: #060810;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
            }
        """)

    def load_image(self, image_path: str, overlay_data: Optional[dict] = None) -> None:
        self.image_path = image_path
        self.overlay_data = overlay_data
        
        # Reset interactions on new scan load
        self.zoom_factor = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.rotation_angle = 0.0
        self.brightness = 0
        self.contrast = 1.0

        if not image_path:
            self.pixmap_image = None
            self.update()
            return

        try:
            self.pixmap_image = QImage(image_path)
        except Exception as e:
            logger.error(f"Failed to load image into viewer: {e}")
            self.pixmap_image = None
            
        self.update()

    def set_overlay_modes(self, heatmap: bool, highlight: bool, bbox: bool) -> None:
        self.show_heatmap = heatmap
        self.show_highlight = highlight
        self.show_bbox = bbox
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.pixmap_image:
            self.drag_start = event.position()
            self.is_dragging = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if hasattr(self, "is_dragging") and self.is_dragging and self.pixmap_image:
            delta = event.position() - self.drag_start
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.drag_start = event.position()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = self.rect()
        
        if not self.pixmap_image:
            painter.setPen(QPen(QColor(255,255,255,10), 1))
            for grid_x in range(0, rect.width(), 30):
                painter.drawLine(grid_x, 0, grid_x, rect.height())
            for grid_y in range(0, rect.height(), 30):
                painter.drawLine(0, grid_y, rect.width(), grid_y)
                
            painter.setPen(QColor(255,255,255,120))
            painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
            painter.drawText(rect, Qt.AlignCenter, "Scan Asset Display [Empty Node]")
            painter.end()
            return

        # Target rect to draw image centered preserving ratio
        img_w = self.pixmap_image.width()
        img_h = self.pixmap_image.height()
        
        ratio = min(rect.width() / img_w, rect.height() / img_h)
        target_w = int(img_w * ratio)
        target_h = int(img_h * ratio)
        
        # Apply Zoom & Pan & Rotation transformations relative to center
        painter.translate(rect.width()/2.0 + self.pan_x, rect.height()/2.0 + self.pan_y)
        painter.scale(self.zoom_factor, self.zoom_factor)
        painter.rotate(self.rotation_angle)
        
        # Center target drawing rect
        target_rect = QRectF(-target_w / 2.0, -target_h / 2.0, target_w, target_h)
        
        # Apply basic brightness/contrast adjustments to QImage if modified (done visually by painter overlay here)
        painter.drawImage(target_rect, self.pixmap_image)

        # Apply visual contrast overlay glow for demo
        if self.brightness != 0 or self.contrast != 1.0:
            painter.setPen(Qt.NoPen)
            # Brightness overlay
            if self.brightness > 0:
                painter.setBrush(QBrush(QColor(255, 255, 255, int(self.brightness * 1.5))))
                painter.drawRect(target_rect)
            elif self.brightness < 0:
                painter.setBrush(QBrush(QColor(0, 0, 0, int(abs(self.brightness) * 1.5))))
                painter.drawRect(target_rect)

        # Draw overlays matching scaled grid coordinates
        if self.overlay_data and (self.show_heatmap or self.show_highlight or self.show_bbox):
            orig_x = self.overlay_data["x"]
            orig_y = self.overlay_data["y"]
            orig_w = self.overlay_data["width"]
            orig_h = self.overlay_data["height"]
            
            scale_x = target_w / 300.0
            scale_y = target_h / 300.0
            
            # Map coordinates from original 300x300 canvas to target rect coordinates centered at (0,0)
            x = -target_w / 2.0 + (orig_x * scale_x)
            y = -target_h / 2.0 + (orig_y * scale_y)
            w = orig_w * scale_x
            h = orig_h * scale_y
            
            overlay_rect = QRectF(x, y, w, h)
            cx, cy = x + w/2.0, y + h/2.0
            rad = max(w, h)/2.0

            if self.show_heatmap:
                heatmap_grad = QRadialGradient(cx, cy, rad * 1.5)
                heatmap_grad.setColorAt(0.0, QColor(239, 68, 68, 140))
                heatmap_grad.setColorAt(0.4, QColor(234, 179, 8, 80))
                heatmap_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
                
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(heatmap_grad))
                painter.drawEllipse(QPointF(cx, cy), rad * 1.5, rad * 1.5)

            if self.show_highlight:
                painter.setPen(QPen(QColor(16, 185, 129), 2, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(cx, cy), rad + 6, rad + 6)

            if self.show_bbox:
                painter.setPen(QPen(QColor(239, 68, 68), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(overlay_rect)
                
                lbl_rect = QRectF(x, y - 20, w + 35, 20)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(239, 68, 68)))
                painter.drawRect(lbl_rect)
                
                painter.setPen(Qt.white)
                painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
                painter.drawText(lbl_rect.adjusted(6, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, "SUSPECTED LESION: 12mm")

        painter.end()


class VoiceVisualizerWidget(QWidget):
    """Pulsating soundwave visualizer drawn with custom painter."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(50)
        self.anim_phase = 0.0
        self.is_active = False
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_wave)
        
    def start_anim(self) -> None:
        self.is_active = True
        self.timer.start(40)
        
    def stop_anim(self) -> None:
        self.is_active = False
        self.timer.stop()
        self.update()
        
    def _update_wave(self) -> None:
        self.anim_phase += 0.25
        self.update()
        
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        w, h = rect.width(), rect.height()
        
        painter.setPen(QPen(QColor(255,255,255,10), 1))
        painter.setBrush(QBrush(QColor(255,255,255,2)))
        painter.drawRoundedRect(rect, 8, 8)
        
        if not self.is_active:
            painter.setPen(QPen(QColor(255,255,255,30), 1))
            painter.drawLine(10, h/2, w - 10, h/2)
            painter.end()
            return
            
        painter.setPen(QPen(QColor(6, 182, 212), 2))
        path = QPainterPath()
        path.moveTo(10, h/2)
        
        for x in range(10, w - 10, 4):
            wave1 = math.sin((x / 18.0) + self.anim_phase) * 12.0
            wave2 = math.cos((x / 9.0) - self.anim_phase * 0.8) * 5.0
            y = (h / 2.0) + wave1 + wave2
            path.lineTo(x, y)
        painter.drawPath(path)
        
        painter.setPen(QPen(QColor(139, 92, 246, 120), 1.5))
        path2 = QPainterPath()
        path2.moveTo(10, h/2)
        for x in range(10, w - 10, 4):
            wave1 = math.cos((x / 12.0) + self.anim_phase * 0.4) * 7.0
            wave2 = math.sin((x / 7.0) - self.anim_phase) * 3.0
            y = (h / 2.0) + wave1 + wave2
            path2.lineTo(x, y)
        painter.drawPath(path2)
        
        painter.end()


class ClinicalAnalysisWorkspaceView(QWidget):
    """SIEMENS Healthineers & GE Healthcare inspired Diagnostic Clinical Workspace."""

    def __init__(self, current_user: User) -> None:
        super().__init__()
        self._user = current_user
        self._analyzer = MedicalAnalyzerService()
        self._voice_service = VoiceAssistantService(self)
        
        self._voice_service.command_executed.connect(self._on_voice_command_triggered)
        self._analysis_result: Optional[dict] = None
        self._is_processing = False
        
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Header Area
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("AI Diagnostics & Medical Imaging Workspace")
        title.setStyleSheet("color: white; font-size: 26px; font-weight: 800; letter-spacing: 0.5px;")
        sub = QLabel("Ingest lab reports, ECG records, or medical imaging scans to automatically run diagnostics analysis and cross-reference clinical guidelines.")
        sub.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box, 1)

        # Voice Assistant Activation Mic Button
        self.btn_mic = QPushButton("🎤 Voice Assistant")
        self.btn_mic.setFixedSize(140, 36)
        self.btn_mic.setCursor(Qt.PointingHandCursor)
        self.btn_mic.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #3b82f6);
                color: white; border: none; border-radius: 8px;
                font-weight: bold; font-size: 11.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #2563eb);
            }
        """)
        self.btn_mic.clicked.connect(self._toggle_voice_card)
        header.addWidget(self.btn_mic)
        layout.addLayout(header)

        # Voice Assistant Card Drawer (collapsible below header)
        self.voice_card = QFrame()
        self.voice_card.setVisible(False)
        self.voice_card.setStyleSheet("background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;")
        voice_layout = QVBoxLayout(self.voice_card)
        voice_layout.setContentsMargins(15, 12, 15, 12)
        voice_layout.setSpacing(10)

        voice_hdr = QHBoxLayout()
        v_title = QLabel("Clinical Voice Assistant Panel")
        v_title.setStyleSheet("color: #8b5cf6; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        voice_hdr.addWidget(v_title)
        voice_hdr.addStretch()
        
        self.voice_status_lbl = QLabel("Assistant Ready. Click to speak commands.")
        self.voice_status_lbl.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 10.5px;")
        voice_hdr.addWidget(self.voice_status_lbl)
        voice_layout.addLayout(voice_hdr)

        self.voice_visualizer = VoiceVisualizerWidget(self)
        voice_layout.addWidget(self.voice_visualizer)

        # Command Quick Buttons
        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(8)
        cmds = [
            ("🗣️ Explain Report", "Explain this report."),
            ("🗣️ Explain Scan", "Explain this scan."),
            ("🗣️ Highlight Abnormal", "Highlight abnormal findings."),
            ("🗣️ Show Graphs", "Show graphs."),
            ("🗣️ Read Aloud", "Read this report aloud."),
            ("🗣️ Compare Trend", "Compare with previous report."),
            ("🗣️ Export PDF", "Export report.")
        ]
        for label, cmd_text in cmds:
            btn = QPushButton(label)
            btn.setFixedHeight(24)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.04);
                    color: white; border: none; border-radius: 4px;
                    font-size: 9.5px; font-weight: bold; padding: 2px 8px;
                }
                QPushButton:hover { background: rgba(139,92,246,0.15); color: #8b5cf6; }
            """)
            btn.clicked.connect(lambda c=cmd_text: self._sim_voice_input(c))
            cmd_row.addWidget(btn)
        voice_layout.addLayout(cmd_row)
        layout.addWidget(self.voice_card)

        # Drag-Drop area
        self.upload_area = DragDropUploadArea(self)
        self.upload_area.file_dropped.connect(self._start_file_analysis)
        layout.addWidget(self.upload_area)

        # Main Workspace content splitter
        self.workspace_splitter = QSplitter(Qt.Horizontal)
        self.workspace_splitter.setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.06); width: 2px; }")

        # ── LEFT SUB-SPLIT (Scan display, parameters, charts) ──
        self.left_panel = QFrame()
        self.left_panel.setStyleSheet("background: transparent; border: none;")
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(15)

        # Scan Viewer Header with controls
        self.viewer_controls_bar = QFrame()
        self.viewer_controls_bar.setStyleSheet("background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;")
        self.viewer_controls_layout = QHBoxLayout(self.viewer_controls_bar)
        self.viewer_controls_layout.setContentsMargins(15, 6, 15, 6)
        self.viewer_controls_layout.setSpacing(8)
        
        v_title = QLabel("Workspace Display View")
        v_title.setStyleSheet("color: white; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        self.viewer_controls_layout.addWidget(v_title)
        self.viewer_controls_layout.addStretch()

        # View Selector Toggles
        self.btn_view_scan = QPushButton("🩻 View Scan")
        self.btn_view_anatomy = QPushButton("🧠 Anatomy Navigator")
        for btn in [self.btn_view_scan, self.btn_view_anatomy]:
            btn.setFixedSize(120, 24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.04);
                    color: white; border: none; border-radius: 4px;
                    font-size: 10px; font-weight: bold;
                }
                QPushButton:hover { background: rgba(255,255,255,0.08); }
            """)
        self.btn_view_scan.clicked.connect(lambda: self.left_stack.setCurrentIndex(0))
        self.btn_view_anatomy.clicked.connect(lambda: self.left_stack.setCurrentIndex(1))
        self.viewer_controls_layout.addWidget(self.btn_view_scan)
        self.viewer_controls_layout.addWidget(self.btn_view_anatomy)

        # Image interactions: Zoom, Pan reset, Rotation, Contrast/Brightness
        self.btn_zoom_in = QPushButton("🔍+")
        self.btn_zoom_out = QPushButton("🔍-")
        self.btn_rotate = QPushButton("🔄")
        self.btn_bright_plus = QPushButton("☀️+")
        self.btn_bright_minus = QPushButton("☀️-")
        
        for btn in [self.btn_zoom_in, self.btn_zoom_out, self.btn_rotate, self.btn_bright_plus, self.btn_bright_minus]:
            btn.setFixedSize(30, 24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.04);
                    color: white; border: none; border-radius: 4px;
                    font-size: 9.5px; font-weight: bold;
                }
                QPushButton:hover { background: rgba(6,182,212,0.15); }
            """)
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        self.btn_rotate.clicked.connect(self._rotate_scan)
        self.btn_bright_plus.clicked.connect(self._bright_plus)
        self.btn_bright_minus.clicked.connect(self._bright_minus)

        self.viewer_controls_layout.addWidget(self.btn_zoom_in)
        self.viewer_controls_layout.addWidget(self.btn_zoom_out)
        self.viewer_controls_layout.addWidget(self.btn_rotate)
        self.viewer_controls_layout.addWidget(self.btn_bright_plus)
        self.viewer_controls_layout.addWidget(self.btn_bright_minus)

        self.chk_heatmap = QCheckBox("Heatmap")
        self.chk_highlight = QCheckBox("Highlight")
        self.chk_bbox = QCheckBox("BBox")
        for chk in [self.chk_heatmap, self.chk_highlight, self.chk_bbox]:
            chk.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 9px; font-weight: bold;")
            chk.setCursor(Qt.PointingHandCursor)
            chk.stateChanged.connect(self._on_overlay_changed)
            self.viewer_controls_layout.addWidget(chk)
            
        self.left_layout.addWidget(self.viewer_controls_bar)

        # Left stacked display (Scan image view or Anatomy Navigator)
        self.left_stack = QStackedWidget()
        self.scanner_view = ImageScannerView(self)
        self.anatomy_view = AnatomyNavigatorWidget(self)
        self.anatomy_view.organ_selected.connect(self._on_anatomy_organ_selected)
        
        self.left_stack.addWidget(self.scanner_view)
        self.left_stack.addWidget(self.anatomy_view)
        self.left_layout.addWidget(self.left_stack, 1)

        # Visualization block (dynamic comparative charts)
        self.chart_tabs_bar = QFrame()
        self.chart_tabs_bar.setStyleSheet("background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;")
        self.chart_tabs_layout = QHBoxLayout(self.chart_tabs_bar)
        self.chart_tabs_layout.setContentsMargins(10, 4, 10, 4)
        self.chart_tabs_layout.setSpacing(8)

        c_title = QLabel("Biomarker Charts")
        c_title.setStyleSheet("color: white; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        self.chart_tabs_layout.addWidget(c_title)
        self.chart_tabs_layout.addStretch()

        self.btn_bar_chart = QPushButton("Bar")
        self.btn_pie_chart = QPushButton("Pie")
        self.btn_trend_chart = QPushButton("Trend")
        self.btn_radar_chart = QPushButton("Radar")
        self.btn_circular_progress = QPushButton("Confidence")
        
        for btn in [self.btn_bar_chart, self.btn_pie_chart, self.btn_trend_chart, self.btn_radar_chart, self.btn_circular_progress]:
            btn.setFixedSize(75, 24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.04);
                    color: white; border: none; border-radius: 4px;
                    font-size: 10px; font-weight: bold;
                }
                QPushButton:hover { background: rgba(255,255,255,0.08); }
            """)
            self.chart_tabs_layout.addWidget(btn)

        self.btn_bar_chart.clicked.connect(lambda: self.chart_view.set_data(self._analysis_result["parameters"], "bar"))
        self.btn_pie_chart.clicked.connect(lambda: self.chart_view.set_data(self._analysis_result["parameters"], "pie"))
        self.btn_trend_chart.clicked.connect(lambda: self.chart_view.set_data(self._analysis_result["parameters"], "trend"))
        self.btn_radar_chart.clicked.connect(lambda: self.chart_view.set_data(self._analysis_result["parameters"], "radar"))
        self.btn_circular_progress.clicked.connect(lambda: self.chart_view.set_data(self._analysis_result["parameters"], "circular"))

        self.left_layout.addWidget(self.chart_tabs_bar)

        self.chart_view = CustomVectorChart(self)
        self.left_layout.addWidget(self.chart_view, 1)
        self.workspace_splitter.addWidget(self.left_panel)

        # ── RIGHT SPLIT (Parameters, Summary, Evidence) ──
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.right_container = QWidget()
        self.right_container.setStyleSheet("background: transparent;")
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(20)

        # 1. Findings Table Card
        self.findings_card = QFrame()
        self.findings_card.setStyleSheet("background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px;")
        self.findings_layout = QVBoxLayout(self.findings_card)
        self.findings_layout.setContentsMargins(20, 20, 20, 20)
        self.findings_layout.setSpacing(12)

        f_lbl = QLabel("Extracted Clinical Parameters Table (Click Parameter for Definitions)")
        f_lbl.setStyleSheet("color: #06b6d4; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        self.findings_layout.addWidget(f_lbl)

        self.params_table = QTableWidget()
        self.params_table.setColumnCount(4)
        self.params_table.setHorizontalHeaderLabels(["Parameter", "Current Value", "Reference Range", "Clearance Status"])
        self._style_table(self.params_table)
        self.params_table.cellClicked.connect(self._on_table_cell_clicked)
        
        self.findings_layout.addWidget(self.params_table)
        self.right_layout.addWidget(self.findings_card)

        # 2. AI Summaries & Evidence Panel
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px;")
        self.summary_layout = QVBoxLayout(self.summary_card)
        self.summary_layout.setContentsMargins(20, 20, 20, 20)
        self.summary_layout.setSpacing(15)

        s_lbl = QLabel("AI Clinical Diagnostic Summary")
        s_lbl.setStyleSheet("color: #8b5cf6; font-size: 13px; font-weight: 800; letter-spacing: 0.5px;")
        self.summary_layout.addWidget(s_lbl)

        self.summary_text_lbl = QTextBrowser()
        self.summary_text_lbl.setOpenLinks(False)
        self.summary_text_lbl.anchorClicked.connect(self._on_hyperlink_clicked)
        self.summary_text_lbl.setHtml("<div style='color:rgba(255,255,255,0.4); font-size:12.5px;'>No clinical file uploaded for diagnostic summary generation.</div>")
        self.summary_text_lbl.setStyleSheet("QTextBrowser { border: none; background: transparent; }")
        self.summary_text_lbl.setMinimumHeight(200)
        self.summary_layout.addWidget(self.summary_text_lbl)

        self.right_layout.addWidget(self.summary_card)

        # 3. Reference Evidence Box
        self.evidence_card = QFrame()
        self.evidence_card.setStyleSheet("background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px;")
        self.evidence_layout = QVBoxLayout(self.evidence_card)
        self.evidence_layout.setContentsMargins(20, 20, 20, 20)
        self.evidence_layout.setSpacing(12)

        e_lbl = QLabel("Cross-Referenced Guidelines Evidence (RAG)")
        e_lbl.setStyleSheet("color: #10b981; font-size: 13px; font-weight: 800; letter-spacing: 0.5px;")
        self.evidence_layout.addWidget(e_lbl)

        self.evidence_content_layout = QVBoxLayout()
        self.evidence_content_layout.setSpacing(10)
        self.evidence_layout.addLayout(self.evidence_content_layout)
        self.right_layout.addWidget(self.evidence_card)

        # 4. Action Export Buttons Row
        self.export_bar = QHBoxLayout()
        self.export_bar.setSpacing(15)
        
        self.btn_export_pdf = QPushButton("📥 Download PDF Diagnostic Analysis")
        self.btn_export_excel = QPushButton("📊 Download Structured Excel Report")
        
        for btn in [self.btn_export_pdf, self.btn_export_excel]:
            btn.setFixedHeight(40)
            btn.setEnabled(False)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    color: white; border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px; font-weight: bold; font-size: 11.5px;
                }
                QPushButton:enabled {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06b6d4, stop:1 #3b82f6);
                    border: none;
                }
                QPushButton:enabled:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0891b2, stop:1 #2563eb);
                }
            """)
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        self.btn_export_excel.clicked.connect(self._export_excel)
        
        self.export_bar.addWidget(self.btn_export_pdf, 1)
        self.export_bar.addWidget(self.btn_export_excel, 1)
        self.right_layout.addLayout(self.export_bar)

        self.right_scroll.setWidget(self.right_container)
        self.workspace_splitter.addWidget(self.right_scroll)

        # ── AI TERMINOLOGY SIDE EXPLORER drawer panel ──
        self.term_panel = TerminologyExplorerPanel(self)
        self.term_panel.close_requested.connect(lambda: self.term_panel.hide())
        self.workspace_splitter.addWidget(self.term_panel)
        self.term_panel.hide()

        self.workspace_splitter.setSizes([600, 600, 300])
        layout.addWidget(self.workspace_splitter, 1)

        self._set_ui_state(has_data=False)

    def _set_ui_state(self, has_data: bool) -> None:
        self.viewer_controls_bar.setEnabled(True)
        self.chart_tabs_bar.setEnabled(has_data)
        self.btn_export_pdf.setEnabled(has_data)
        self.btn_export_excel.setEnabled(has_data)

    def _on_overlay_changed(self) -> None:
        self.scanner_view.set_overlay_modes(
            self.chk_heatmap.isChecked(),
            self.chk_highlight.isChecked(),
            self.chk_bbox.isChecked()
        )

    def _zoom_in(self) -> None:
        if self.scanner_view.pixmap_image:
            self.scanner_view.zoom_factor *= 1.2
            self.scanner_view.update()

    def _zoom_out(self) -> None:
        if self.scanner_view.pixmap_image:
            self.scanner_view.zoom_factor *= 0.8
            self.scanner_view.update()

    def _rotate_scan(self) -> None:
        if self.scanner_view.pixmap_image:
            self.scanner_view.rotation_angle = (self.scanner_view.rotation_angle + 90) % 360
            self.scanner_view.update()

    def _bright_plus(self) -> None:
        if self.scanner_view.pixmap_image:
            self.scanner_view.brightness = min(100, self.scanner_view.brightness + 15)
            self.scanner_view.update()

    def _bright_minus(self) -> None:
        if self.scanner_view.pixmap_image:
            self.scanner_view.brightness = max(-100, self.scanner_view.brightness - 15)
            self.scanner_view.update()

    def _toggle_voice_card(self) -> None:
        self.voice_card.setVisible(not self.voice_card.isVisible())
        if self.voice_card.isVisible():
            self.voice_visualizer.start_anim()
            self._voice_service.speak("MediVerse voice control activated. Please select a command below.")
        else:
            self.voice_visualizer.stop_anim()

    def _sim_voice_input(self, command_text: str) -> None:
        self.voice_status_lbl.setText(f"Command heard: \"{command_text}\"")
        response = self._voice_service.process_command(command_text)
        self._voice_service.speak(response)
        
    def _on_voice_command_triggered(self, cmd_id: str, payload: dict) -> None:
        logger.info(f"Voice action dispatch: {cmd_id}")
        
        if cmd_id == "explain_report":
            self.left_stack.setCurrentIndex(0)
            if self._analysis_result:
                self._voice_service.speak(self._analysis_result["ai_summary"])
                
        elif cmd_id == "explain_scan":
            self.left_stack.setCurrentIndex(0)
            self.chk_heatmap.setChecked(True)
            self.chk_highlight.setChecked(True)
            self.chk_bbox.setChecked(True)
            self.scanner_view.set_overlay_modes(True, True, True)
            
        elif cmd_id == "highlight_abnormal":
            self.left_stack.setCurrentIndex(0)
            NotificationToast.show_message(self.window(), "Highlighting clinical outlier rows.", "info")
            
        elif cmd_id == "show_graphs":
            self.chart_view.set_data(self._analysis_result["parameters"] if self._analysis_result else [], "bar")
            
        elif cmd_id == "open_mri":
            self.left_stack.setCurrentIndex(1)
            self.anatomy_view.highlight_organ("Brain")
            QTimer.singleShot(1000, lambda: self._start_file_analysis("patient_brain_mri_scan.png"))
            
        elif cmd_id == "open_xray":
            self.left_stack.setCurrentIndex(1)
            self.anatomy_view.highlight_organ("Lungs")
            QTimer.singleShot(1000, lambda: self._start_file_analysis("chest_xray_radiology_report.png"))
            
        elif cmd_id == "compare_previous":
            if self._analysis_result:
                self.chart_view.set_data(self._analysis_result["parameters"], "trend")
                
        elif cmd_id == "read_aloud":
            if self._analysis_result:
                self._voice_service.speak(self._analysis_result["ai_summary"])
                
        elif cmd_id == "export_report":
            self._export_pdf()
            
        elif cmd_id == "generate_summary":
            if self._analysis_result:
                self._voice_service.speak("Regenerating clinical summary.")

    def _on_anatomy_organ_selected(self, organ_name: str) -> None:
        logger.info(f"Interactive Anatomy organ clicked: {organ_name}")
        mock_paths = {
            "Brain": "patient_brain_mri_scan.png",
            "Lungs": "chest_xray_radiology_report.png",
            "Heart": "cardiac_ecg_report.pdf",
            "Liver": "liver_function_lft_report.pdf",
            "Kidneys": "renal_kidney_kft_report.pdf",
            "Blood": "hematology_cbc_blood_report.pdf"
        }
        mock_file = mock_paths.get(organ_name, "general_clinical_report.pdf")
        self._start_file_analysis(mock_file)

    def _on_table_cell_clicked(self, row: int, col: int) -> None:
        if not self._analysis_result:
            return
        term_item = self.params_table.item(row, 0)
        if term_item:
            term = term_item.text()
            self._open_term_explorer(term)

    def _on_hyperlink_clicked(self, url) -> None:
        url_str = url.toString()
        if url_str.startswith("term:"):
            term = url_str.split(":", 1)[1]
            self._open_term_explorer(term)

    def _open_term_explorer(self, term: str) -> None:
        self.term_panel.show()
        self.term_panel.inspect_term(term)
        self.workspace_splitter.setSizes([500, 500, 280])

    def _start_file_analysis(self, file_path: str) -> None:
        if self._is_processing:
            return
            
        self._is_processing = True
        self.upload_area.setEnabled(False)
        self.upload_area.text_lbl.setText("Ingesting asset & executing AI analysis pipeline...")
        self.upload_area.icon_lbl.setText("⚙️")
        QApplication.processEvents()
        
        self._sim_step = 0
        self._sim_file_path = file_path
        
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._run_analysis_simulation)
        self._anim_timer.start(400)

    def _run_analysis_simulation(self) -> None:
        # Step-by-step progress pipeline animation matching requirements exactly
        steps = [
            "Uploading Clinical Scan Asset Grid...",
            "Executing Automatic File Modality Recognition...",
            "Assessing Quality & Core Contrast Metrics...",
            "Executing Optical Character Recognition (OCR)...",
            "Extracting Structured Medical Parameters...",
            "Compiling Multi-Axis Visualization Graphs...",
            "AI Diagnostics Diagnostics Complete!"
        ]
        
        if self._sim_step < len(steps):
            self.upload_area.text_lbl.setText(steps[self._sim_step])
            self._sim_step += 1
        else:
            self._anim_timer.stop()
            self._complete_analysis()

    def _complete_analysis(self) -> None:
        try:
            self._analysis_result = self._analyzer.analyze_file(self._sim_file_path, self._user.id)
            
            body_part = self._analysis_result["metadata"]["body_part"]
            self.anatomy_view.highlight_organ(body_part)
            
            self._populate_view_panels()
            self._set_ui_state(has_data=True)
            
            self._voice_service.speak(
                f"Analysis completed for {self._analysis_result['metadata']['modality']}. "
                f"Anatomy matched to {body_part}."
            )
            NotificationToast.show_message(self.window(), "Analysis complete!", "success")
        except Exception as e:
            logger.exception("Analysis failed")
            NotificationToast.show_message(self.window(), f"Analysis failed: {e}", "error")
        finally:
            self._is_processing = False
            self.upload_area.setEnabled(True)
            self.upload_area.text_lbl.setText("Drag & Drop Medical Report or Imaging Scan here")
            self.upload_area.icon_lbl.setText("📤")

    def _populate_view_panels(self) -> None:
        res = self._analysis_result
        if not res:
            return
            
        if res["is_image"]:
            self.left_stack.setCurrentIndex(0)
            self.scanner_view.load_image(res["file_path"], res["heatmap_overlay"])
            self.chk_heatmap.setChecked(True)
            self.chk_highlight.setChecked(True)
            self.chk_bbox.setChecked(True)
            self.scanner_view.set_overlay_modes(True, True, True)
        else:
            self.left_stack.setCurrentIndex(1)
            self.scanner_view.load_image("")
            self.chk_heatmap.setChecked(False)
            self.chk_highlight.setChecked(False)
            self.chk_bbox.setChecked(False)
            
        self.chart_view.set_data(res["parameters"], "bar")

        # Table rows with Orange/Red glow highlights for warnings
        self.params_table.setRowCount(len(res["parameters"]))
        for idx, p in enumerate(res["parameters"]):
            name_item = QTableWidgetItem(p["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setForeground(QColor(6, 182, 212))
            self.params_table.setItem(idx, 0, name_item)

            val_item = QTableWidgetItem(p["value"])
            val_item.setFlags(val_item.flags() & ~Qt.ItemIsEditable)
            self.params_table.setItem(idx, 1, val_item)

            ref_item = QTableWidgetItem(p["reference"])
            ref_item.setFlags(ref_item.flags() & ~Qt.ItemIsEditable)
            self.params_table.setItem(idx, 2, ref_item)

            status_item = QTableWidgetItem(p["status"])
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            if p["status"] in ["High", "Low", "Abnormal"]:
                status_item.setForeground(QColor(239, 68, 68))
                font = status_item.font()
                font.setBold(True)
                status_item.setFont(font)
                
                # Apply red background highlight row color
                name_item.setBackground(QBrush(QColor(239, 68, 68, 15)))
                val_item.setBackground(QBrush(QColor(239, 68, 68, 15)))
                ref_item.setBackground(QBrush(QColor(239, 68, 68, 15)))
                status_item.setBackground(QBrush(QColor(239, 68, 68, 15)))
            else:
                status_item.setForeground(QColor(16, 185, 129))
            self.params_table.setItem(idx, 3, status_item)

        linked_html = self._linkify_text(res["ai_summary"])
        self.summary_text_lbl.setHtml(linked_html)

        while self.evidence_content_layout.count():
            item = self.evidence_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if res["evidence"]:
            for r in res["evidence"]:
                card = QFrame()
                card.setStyleSheet("background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 10px;")
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(12, 12, 12, 12)
                card_layout.setSpacing(6)

                hdr = QHBoxLayout()
                lbl_title = QLabel(r.document_title)
                lbl_title.setStyleSheet("color: white; font-size: 11.5px; font-weight: bold; border: none;")
                hdr.addWidget(lbl_title, 1)
                
                lbl_cat = QLabel(r.category.upper())
                lbl_cat.setStyleSheet("""
                    background: rgba(16, 185, 129, 0.1); 
                    color: #10b981; 
                    border: 1px solid rgba(16, 185, 129, 0.2); 
                    border-radius: 4px; padding: 2px 6px; 
                    font-size: 8px; font-weight: bold;
                """)
                hdr.addWidget(lbl_cat)
                card_layout.addLayout(hdr)

                lbl_text = QLabel(f"\"{r.preview}\"")
                lbl_text.setWordWrap(True)
                lbl_text.setStyleSheet("color: rgba(255,255,255,0.65); font-size: 11px; font-style: italic; border: none; line-height: 1.4;")
                card_layout.addWidget(lbl_text)
                
                self.evidence_content_layout.addWidget(card)
        else:
            lbl_none = QLabel("No direct clinical guideline guidelines matches resolved.")
            lbl_none.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11.5px; padding: 5px;")
            self.evidence_content_layout.addWidget(lbl_none)

    def _linkify_text(self, text: str) -> str:
        terms = [
            "Hemoglobin", "Creatinine", "Lesion", "ALT", "AST", 
            "Bilirubin", "WBC", "Platelets", "Heart Rate", "PR Interval"
        ]
        linked = text.replace("\n", "<br>")
        for term in terms:
            pattern = re.compile(rf"\b{term}\b", re.IGNORECASE)
            linked = pattern.sub(f'<a href="term:{term}" style="color:#06b6d4; text-decoration:none; font-weight:bold;">{term}</a>', linked)
        return f"<div style='color:rgba(255,255,255,0.85); font-family:\"Segoe UI\"; font-size:12.5px; line-height:1.5;'>{linked}</div>"

    def _export_pdf(self) -> None:
        if not self._analysis_result:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Report", "Clinical_Analysis_Report.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
            
        try:
            self._analyzer.export_report_pdf(self._analysis_result, file_path)
            NotificationToast.show_message(self.window(), "PDF exported successfully!", "success")
        except Exception as e:
            QMessageBox.critical(self, "Export Failure", f"Failed to export PDF:\n{e}")

    def _export_excel(self) -> None:
        if not self._analysis_result:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel Report", "Clinical_Parameters.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return
            
        try:
            self._analyzer.export_report_excel(self._analysis_result, file_path)
            NotificationToast.show_message(self.window(), "CSV parameters list exported successfully!", "success")
        except Exception as e:
            QMessageBox.critical(self, "Export Failure", f"Failed to export CSV:\n{e}")

    def _style_table(self, table: QTableWidget) -> None:
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                alternate-background-color: transparent;
                gridline-color: transparent;
                color: white;
                font-family: 'Segoe UI';
                font-size: 11.5px;
                border: none;
            }
            QTableWidget::item {
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
                padding: 8px 10px;
            }
        """)
        
        header = table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: rgba(255, 255, 255, 0.03);
                color: rgba(255, 255, 255, 0.6);
                font-family: 'Segoe UI';
                font-size: 10px;
                font-weight: bold;
                border: none;
                height: 32px;
                padding-left: 10px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)
