"""
MediVerse AI — Theme Toggle Component.
Switch for toggling between dark and light modes.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget


class ThemeToggle(QWidget):
    """Animated toggle switch for Dark/Light mode."""
    
    toggled = Signal(bool) # True = Dark Mode

    def __init__(self, is_dark: bool = True) -> None:
        super().__init__()
        self._is_dark = is_dark
        self._thumb_pos = 0.0
        
        self.setFixedSize(50, 26)
        self.setCursor(Qt.PointingHandCursor)
        
        self._anim = QPropertyAnimation(self, b"thumb_pos")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.valueChanged.connect(self.update)
        
        self.set_state(is_dark, animated=False)

    @property
    def thumb_pos(self) -> float:
        return self._thumb_pos

    @thumb_pos.setter
    def thumb_pos(self, pos: float) -> None:
        self._thumb_pos = pos

    def set_state(self, is_dark: bool, animated: bool = True) -> None:
        self._is_dark = is_dark
        target = 24.0 if is_dark else 2.0
        
        if animated:
            self._anim.setStartValue(self._thumb_pos)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._thumb_pos = target
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.set_state(not self._is_dark)
            self.toggled.emit(self._is_dark)
            
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Track
        track_path = QPainterPath()
        track_path.addRoundedRect(self.rect(), 13, 13)
        bg_color = QColor("#3b82f6") if self._is_dark else QColor("#cbd5e1")
        painter.fillPath(track_path, bg_color)
        
        # Icons inside track
        painter.setPen(QColor(255, 255, 255, 180))
        font = painter.font()
        font.setPixelSize(10)
        painter.setFont(font)
        painter.drawText(QRect(6, 0, 16, 26), Qt.AlignCenter, "☀")
        painter.drawText(QRect(28, 0, 16, 26), Qt.AlignCenter, "🌙")
        
        # Thumb
        thumb_rect = QRect(int(self._thumb_pos), 2, 22, 22)
        thumb_path = QPainterPath()
        thumb_path.addEllipse(thumb_rect)
        painter.fillPath(thumb_path, QColor("white"))
