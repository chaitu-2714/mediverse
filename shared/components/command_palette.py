"""
MediVerse AI — Command Palette Component (Ctrl+K).
A spotlight-like search overlay for quick navigation and actions.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QKeyEvent
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QWidget
)


class CommandPalette(QDialog):
    """Ctrl+K style command palette overlay."""
    
    command_selected = Signal(str, str) # (command_id, data)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._commands = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Search input
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command or search... (Esc to close)")
        self._input.setFixedHeight(60)
        self._input.setStyleSheet("""
            QLineEdit {
                background: transparent; border: none;
                color: white; font-size: 18px; padding: 0 20px;
            }
        """)
        self._input.textChanged.connect(self._filter_commands)
        self._input.returnPressed.connect(self._execute_selected)
        layout.addWidget(self._input)
        
        # Divider
        div = QWidget()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255,255,255,0.1);")
        layout.addWidget(div)
        
        # List
        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background: transparent; border: none; outline: none;
                padding: 10px;
            }
            QListWidget::item {
                color: rgba(255,255,255,0.8); padding: 12px;
                border-radius: 8px; font-size: 14px;
            }
            QListWidget::item:selected {
                background: rgba(59, 130, 246, 0.2);
                color: white;
            }
        """)
        self._list.itemClicked.connect(self._execute_selected)
        layout.addWidget(self._list)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 12, 12)
        
        painter.fillPath(path, QColor(20, 25, 35, 245)) # Blur/transparent dark
        painter.setPen(QColor(255, 255, 255, 30))
        painter.drawPath(path)

    def set_commands(self, commands: list[dict[str, str]]) -> None:
        """commands format: [{"id": "nav_home", "title": "Go to Dashboard", "icon": "🏠", "data": ""}]"""
        self._commands = commands
        self._filter_commands("")

    def _filter_commands(self, text: str) -> None:
        self._list.clear()
        text = text.lower()
        for cmd in self._commands:
            if text in cmd["title"].lower() or not text:
                item = QListWidgetItem(f"{cmd.get('icon', '🔹')}  {cmd['title']}")
                item.setData(Qt.UserRole, cmd)
                self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _execute_selected(self) -> None:
        item = self._list.currentItem()
        if item:
            cmd = item.data(Qt.UserRole)
            self.command_selected.emit(cmd["id"], cmd.get("data", ""))
            self.accept()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Center on parent
        if self.parentWidget():
            parent_rect = self.parentWidget().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 3
            self.move(x, y)
        self._input.clear()
        self._input.setFocus()
