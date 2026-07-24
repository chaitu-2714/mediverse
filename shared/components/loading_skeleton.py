"""
MediVerse AI — Loading Skeleton Component.
Animated shimmer effect for loading states (like Notion/Facebook).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QPropertyAnimation, QVariantAnimation, QRect
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QPainterPath
from PySide6.QtWidgets import QWidget


class LoadingSkeleton(QWidget):
    """Animated shimmer skeleton."""
    
    def __init__(self, parent: QWidget = None, border_radius: int = 8) -> None:
        super().__init__(parent)
        self.border_radius = border_radius
        self._offset = 0.0
        
        # Base colors (dark theme)
        self.color_bg = QColor("#1e2532")
        self.color_highlight = QColor("#2a3441")
        
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(1500)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(2.0) # Move gradient across
        self._anim.setLoopCount(-1) # Infinite
        self._anim.valueChanged.connect(self._on_anim_value)
        
    def start(self) -> None:
        self.show()
        self._anim.start()
        
    def stop(self) -> None:
        self._anim.stop()
        self.hide()
        
    def _on_anim_value(self, val: float) -> None:
        self._offset = val
        self.update()
        
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(self.rect(), self.border_radius, self.border_radius)
        painter.setClipPath(path)
        
        # Calculate gradient position based on offset
        # Offset goes 0.0 -> 2.0
        x1 = self.width() * (self._offset - 1.0)
        x2 = self.width() * self._offset
        
        gradient = QLinearGradient(x1, 0, x2, 0)
        gradient.setColorAt(0.0, self.color_bg)
        gradient.setColorAt(0.5, self.color_highlight)
        gradient.setColorAt(1.0, self.color_bg)
        
        painter.fillPath(path, gradient)
