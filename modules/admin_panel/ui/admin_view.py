"""
MediVerse AI — Admin Panel Workspace.
Enables management of operator accounts, credentials assignments, active statuses,
and system-wide security audit inspection.
"""
from __future__ import annotations

import logging
from uuid import UUID
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QPushButton, QTabWidget, QAbstractItemView
)

from core.models.user import User
from config.constants import UserRole, ROLE_DISPLAY_NAMES
from database.connection import get_db_session
from database.repositories.user_repository import UserRepository
from database.repositories.chunk_repository import AuditRepository
from shared.components.notification_toast import NotificationToast

logger = logging.getLogger("mediverse.modules.admin")


class AdminPanelView(QWidget):
    """Administrator Management Panel Workspace."""

    def __init__(self, current_user: User) -> None:
        super().__init__()
        self._user = current_user
        self._setup_ui()
        self.load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        # Header Area
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Admin Control Center")
        title.setStyleSheet("color: white; font-size: 26px; font-weight: 800; letter-spacing: 0.5px;")
        sub = QLabel("Manage system operators, assign credentials clearance levels, and review security audit registries.")
        sub.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        layout.addLayout(header)

        # Tabs Container
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self._tabs_style())
        layout.addWidget(self.tabs, 1)

        # Tab 1: Operator Credentials Registry
        self.operators_tab = QWidget()
        self.operators_layout = QVBoxLayout(self.operators_tab)
        self.operators_layout.setContentsMargins(15, 20, 15, 15)
        self.operators_layout.setSpacing(15)

        # Operators Table Header Row
        ops_header = QHBoxLayout()
        ops_title = QLabel("Operator Credentials Registry")
        ops_title.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        ops_header.addWidget(ops_title)
        ops_header.addStretch()

        self.btn_refresh_ops = QPushButton("↻ Refresh Registry")
        self.btn_refresh_ops.setFixedSize(140, 32)
        self.btn_refresh_ops.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_ops.setStyleSheet(self._btn_secondary_style())
        self.btn_refresh_ops.clicked.connect(self._refresh_operators)
        ops_header.addWidget(self.btn_refresh_ops)
        self.operators_layout.addLayout(ops_header)

        # Operators Table
        self.ops_table = QTableWidget()
        self._style_table(self.ops_table)
        self.ops_table.setColumnCount(6)
        self.ops_table.setHorizontalHeaderLabels([
            "Display Name", "Email Node", "Credentials Role", "Active Status", "Onboarded", "Registered Date"
        ])
        self.operators_layout.addWidget(self.ops_table)
        self.tabs.addTab(self.operators_tab, "🛡️ Credentials Clearance")

        # Tab 2: Security Audit Registry
        self.audit_tab = QWidget()
        self.audit_layout = QVBoxLayout(self.audit_tab)
        self.audit_layout.setContentsMargins(15, 20, 15, 15)
        self.audit_layout.setSpacing(15)

        # Audit Table Header Row
        audit_header = QHBoxLayout()
        audit_title = QLabel("System Security Audit Logs")
        audit_title.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        audit_header.addWidget(audit_title)
        audit_header.addStretch()

        self.btn_refresh_audit = QPushButton("↻ Refresh Audit Logs")
        self.btn_refresh_audit.setFixedSize(150, 32)
        self.btn_refresh_audit.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_audit.setStyleSheet(self._btn_secondary_style())
        self.btn_refresh_audit.clicked.connect(self._refresh_audit)
        audit_header.addWidget(self.btn_refresh_audit)
        self.audit_layout.addLayout(audit_header)

        # Audit Table
        self.audit_table = QTableWidget()
        self._style_table(self.audit_table)
        self.audit_table.setColumnCount(4)
        self.audit_table.setHorizontalHeaderLabels([
            "Timestamp", "Action", "Operator Email", "Security Context / Details"
        ])
        self.audit_layout.addWidget(self.audit_table)
        self.tabs.addTab(self.audit_tab, "📝 Security Audit Logs")

    def load_data(self) -> None:
        self._refresh_operators()
        self._refresh_audit()

    def _refresh_operators(self) -> None:
        try:
            with get_db_session() as session:
                repo = UserRepository(session)
                users = repo.get_all(limit=500)
                
                self.ops_table.setRowCount(len(users))
                for row_idx, user_model in enumerate(users):
                    # Display Name
                    name_item = QTableWidgetItem(user_model.full_name or user_model.username)
                    name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                    self.ops_table.setItem(row_idx, 0, name_item)

                    # Email Node
                    email_item = QTableWidgetItem(user_model.email)
                    email_item.setFlags(email_item.flags() & ~Qt.ItemIsEditable)
                    self.ops_table.setItem(row_idx, 1, email_item)

                    # Credentials Role (Dropdown QComboBox)
                    role_combo = QComboBox()
                    role_combo.addItems([UserRole.DOCTOR, UserRole.RESEARCHER, UserRole.MEDICAL_STUDENT, UserRole.ADMIN])
                    role_combo.setCurrentText(user_model.role)
                    role_combo.setStyleSheet(self._combo_style())
                    role_combo.currentTextChanged.connect(
                        lambda text, u_id=user_model.id: self._on_role_changed(u_id, text)
                    )
                    self.ops_table.setCellWidget(row_idx, 2, role_combo)

                    # Active Status Toggle Button
                    status_btn = QPushButton("Active" if user_model.is_active else "Suspended")
                    status_btn.setCursor(Qt.PointingHandCursor)
                    status_btn.setStyleSheet(self._status_btn_style(user_model.is_active))
                    status_btn.clicked.connect(
                        lambda checked=False, u_id=user_model.id, btn=status_btn: self._on_status_toggled(u_id, btn)
                    )
                    self.ops_table.setCellWidget(row_idx, 3, status_btn)

                    # Onboarded status
                    onb_item = QTableWidgetItem("Yes" if user_model.is_onboarded else "No")
                    onb_item.setFlags(onb_item.flags() & ~Qt.ItemIsEditable)
                    onb_item.setTextAlignment(Qt.AlignCenter)
                    self.ops_table.setItem(row_idx, 4, onb_item)

                    # Registered Date
                    date_str = user_model.created_at.strftime("%Y-%m-%d %H:%M") if user_model.created_at else "N/A"
                    date_item = QTableWidgetItem(date_str)
                    date_item.setFlags(date_item.flags() & ~Qt.ItemIsEditable)
                    self.ops_table.setItem(row_idx, 5, date_item)

        except Exception as e:
            logger.exception("Failed to load users")
            NotificationToast.show_message(self.window(), f"Error loading registry: {e}", "error")

    def _refresh_audit(self) -> None:
        try:
            with get_db_session() as session:
                repo = AuditRepository(session)
                logs = repo.get_recent(limit=100)

                self.audit_table.setRowCount(len(logs))
                for row_idx, log_model in enumerate(logs):
                    # Timestamp
                    ts_str = log_model.created_at.strftime("%Y-%m-%d %H:%M:%S") if log_model.created_at else "N/A"
                    ts_item = QTableWidgetItem(ts_str)
                    ts_item.setFlags(ts_item.flags() & ~Qt.ItemIsEditable)
                    self.audit_table.setItem(row_idx, 0, ts_item)

                    # Action
                    act_item = QTableWidgetItem(log_model.action.upper())
                    act_item.setFlags(act_item.flags() & ~Qt.ItemIsEditable)
                    self.audit_table.setItem(row_idx, 1, act_item)

                    # Operator Email
                    email_str = log_model.user.email if log_model.user else "System / Guest"
                    email_item = QTableWidgetItem(email_str)
                    email_item.setFlags(email_item.flags() & ~Qt.ItemIsEditable)
                    self.audit_table.setItem(row_idx, 2, email_item)

                    # Security Context / Details
                    details_str = str(log_model.details or "")
                    details_item = QTableWidgetItem(details_str)
                    details_item.setFlags(details_item.flags() & ~Qt.ItemIsEditable)
                    self.audit_table.setItem(row_idx, 3, details_item)

        except Exception as e:
            logger.exception("Failed to load audit logs")
            NotificationToast.show_message(self.window(), f"Error loading audit: {e}", "error")

    def _on_role_changed(self, user_id: UUID, new_role: str) -> None:
        try:
            with get_db_session() as session:
                repo = UserRepository(session)
                user = repo.get_by_id(user_id)
                
                # Check that we don't accidentally de-elevate the last admin
                if user.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
                    admins_count = session.query(repo._model_class).filter_by(role=UserRole.ADMIN, is_active=True).count()
                    if admins_count <= 1:
                        NotificationToast.show_message(self.window(), "Cannot change role: At least one active Admin is required.", "warning")
                        self._refresh_operators()
                        return

                user.role = new_role
                session.flush()
                
                # Log action
                audit = AuditRepository(session)
                audit.log_action(
                    action="admin_changed_role",
                    user_id=self._user.id,
                    details={"target_user_id": str(user_id), "new_role": new_role}
                )
                
            NotificationToast.show_message(self.window(), f"Clearance role updated to {new_role}.", "success")
        except Exception as e:
            logger.exception("Error changing user role")
            NotificationToast.show_message(self.window(), f"Role change failed: {e}", "error")
            self._refresh_operators()

    def _on_status_toggled(self, user_id: UUID, btn: QPushButton) -> None:
        try:
            with get_db_session() as session:
                repo = UserRepository(session)
                user = repo.get_by_id(user_id)
                
                # Do not suspend oneself
                if user.id == self._user.id:
                    NotificationToast.show_message(self.window(), "You cannot suspend your own credentials.", "warning")
                    return

                new_state = not user.is_active
                
                if not new_state and user.role == UserRole.ADMIN:
                    admins_count = session.query(repo._model_class).filter_by(role=UserRole.ADMIN, is_active=True).count()
                    if admins_count <= 1:
                        NotificationToast.show_message(self.window(), "Cannot suspend the only remaining active Administrator.", "warning")
                        return

                user.is_active = new_state
                session.flush()

                # Log action
                audit = AuditRepository(session)
                audit.log_action(
                    action="admin_toggled_active",
                    user_id=self._user.id,
                    details={"target_user_id": str(user_id), "is_active": new_state}
                )

            btn.setText("Active" if new_state else "Suspended")
            btn.setStyleSheet(self._status_btn_style(new_state))
            NotificationToast.show_message(
                self.window(), 
                f"Operator status set to {'ACTIVE' if new_state else 'SUSPENDED'}.", 
                "success" if new_state else "warning"
            )
        except Exception as e:
            logger.exception("Error toggling user active state")
            NotificationToast.show_message(self.window(), f"Status toggle failed: {e}", "error")
            self._refresh_operators()

    def _style_table(self, table: QTableWidget) -> None:
        table.setStyleSheet(self._table_style())
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        
        # Header sizing
        header = table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: rgba(255, 255, 255, 0.03);
                color: rgba(255, 255, 255, 0.6);
                font-family: 'Segoe UI';
                font-size: 11px;
                font-weight: bold;
                border: none;
                height: 38px;
                padding-left: 10px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)

    def _tabs_style(self) -> str:
        return """
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.06);
                background: rgba(255, 255, 255, 0.01);
                border-radius: 12px;
            }
            QTabBar::tab {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 10px 18px;
                color: rgba(255, 255, 255, 0.6);
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: bold;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: rgba(6, 182, 212, 0.12);
                border-color: rgba(6, 182, 212, 0.25);
                color: #06b6d4;
                padding-bottom: 10px;
            }
            QTabBar::tab:hover:!selected {
                background: rgba(255, 255, 255, 0.05);
                color: white;
            }
        """

    def _table_style(self) -> str:
        return """
            QTableWidget {
                background-color: transparent;
                alternate-background-color: transparent;
                gridline-color: transparent;
                color: white;
                font-family: 'Segoe UI';
                font-size: 12px;
                border: none;
            }
            QTableWidget::item {
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
                padding: 10px;
            }
            QTableWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.04);
                color: white;
            }
        """

    def _combo_style(self) -> str:
        return """
            QComboBox {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                color: white; 
                font-size: 11px;
                padding: 0 8px;
                margin: 4px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #0d0e1b; color: white;
                selection-background-color: #06b6d4;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """

    def _btn_secondary_style(self) -> str:
        return """
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
            }
        """

    def _status_btn_style(self, active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background: rgba(16, 185, 129, 0.12);
                    color: #10b981;
                    border: 1px solid rgba(16, 185, 129, 0.25);
                    border-radius: 6px;
                    font-size: 10px;
                    font-weight: bold;
                    margin: 4px;
                }
                QPushButton:hover {
                    background: rgba(16, 185, 129, 0.2);
                }
            """
        else:
            return """
                QPushButton {
                    background: rgba(239, 68, 68, 0.12);
                    color: #ef4444;
                    border: 1px solid rgba(239, 68, 68, 0.25);
                    border-radius: 6px;
                    font-size: 10px;
                    font-weight: bold;
                    margin: 4px;
                }
                QPushButton:hover {
                    background: rgba(239, 68, 68, 0.2);
                }
            """
