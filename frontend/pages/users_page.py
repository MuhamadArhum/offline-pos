from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QPushButton, QTableWidget, QHeaderView,
                             QLineEdit, QComboBox, QMessageBox, QTableWidgetItem,
                             QAbstractItemView, QSizePolicy)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont
import qtawesome as qta
from backend.services.user_service import create_user, get_users, toggle_user
from frontend.components.pagination import PaginationControl
from frontend.shared_ui import GLOBAL_STYLE, C

_P   = "#059669"
_P_LT= "#ECFDF5"
_BRD = "#E2E8F0"
_BG  = "#F8FAFC"
_TXT = "#1E293B"
_SEC = "#64748B"

TABLE_STYLE = f"""
QTableWidget {{
    background: white; alternate-background-color: {_P_LT};
    border: none; font-size: 13px; color: {_TXT};
    outline: none; gridline-color: transparent;
    selection-background-color: {_P_LT}; selection-color: {_P};
}}
QTableWidget::item {{ padding: 10px 14px; border: none; border-bottom: 1px solid #F1F5F9; }}
QTableWidget::item:selected {{ background: {_P_LT}; color: {_P}; }}
QHeaderView::section {{
    background: {_BG}; color: {_SEC};
    font-size: 10px; font-weight: 800; letter-spacing: 0.6px;
    padding: 10px 14px; border: none; border-bottom: 2px solid {_BRD};
    text-transform: uppercase;
}}
QHeaderView {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 5px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: {_BRD}; border-radius: 3px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {_P}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""

class UsersPage(QWidget):
    def __init__(self):
        super().__init__()
        self.users_cache = []
        self.setStyleSheet(GLOBAL_STYLE)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ── LEFT: FORM ────────────────────────────────────────────────────
        form_frame = QFrame()
        form_frame.setStyleSheet(
            f"QFrame {{ background: white; border-radius: 14px;"
            f" border: 1.5px solid {_BRD}; }}"
        )
        form_frame.setMinimumWidth(220)
        form_frame.setMaximumWidth(320)
        form_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        f_layout = QVBoxLayout(form_frame)
        f_layout.setContentsMargins(20, 20, 20, 20)
        f_layout.setSpacing(12)

        # Header
        h_row = QHBoxLayout(); h_row.setSpacing(10)
        ico = QLabel()
        ico.setFixedSize(36, 36)
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico.setPixmap(qta.icon('fa5s.user-plus', color='white').pixmap(16, 16))
        ico.setStyleSheet(f"background:{_P}; border-radius:10px; border:none;")
        lbl_title = QLabel("Add User")
        lbl_title.setStyleSheet(f"font-size:15px; font-weight:900; color:{_TXT}; border:none; background:transparent;")
        h_row.addWidget(ico); h_row.addWidget(lbl_title); h_row.addStretch()
        f_layout.addLayout(h_row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{_BRD}; max-height:1px; border:none;")
        f_layout.addWidget(sep)

        def _lbl(text):
            l = QLabel(text)
            l.setStyleSheet(f"font-size:10px; font-weight:800; color:{_SEC}; letter-spacing:0.5px; border:none; background:transparent;")
            return l

        f_layout.addWidget(_lbl("USERNAME"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("e.g. john_doe")
        f_layout.addWidget(self.username_input)

        f_layout.addWidget(_lbl("PASSWORD"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Min 6 characters")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        f_layout.addWidget(self.password_input)

        f_layout.addWidget(_lbl("ROLE"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Cashier", "Manager", "Admin", "Rider", "Waiter", "Kitchen Supervisor"])
        self.role_combo.currentTextChanged.connect(self.on_role_change)
        f_layout.addWidget(self.role_combo)

        self.lbl_phone = _lbl("PHONE (RIDER)")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("03XX-XXXXXXX")
        self.lbl_vehicle = _lbl("VEHICLE NO (RIDER)")
        self.vehicle_input = QLineEdit()
        self.vehicle_input.setPlaceholderText("ABC-123")
        for w in (self.lbl_phone, self.phone_input, self.lbl_vehicle, self.vehicle_input):
            f_layout.addWidget(w)
            w.hide()

        f_layout.addSpacing(6)
        btn_create = QPushButton("  Create User")
        btn_create.setIcon(qta.icon('fa5s.user-plus', color='white'))
        btn_create.setIconSize(QSize(14, 14))
        btn_create.setFixedHeight(42)
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.setStyleSheet(
            f"QPushButton {{ background:{_P}; color:white; border:none; border-radius:10px;"
            f" font-size:13px; font-weight:700; }}"
            f"QPushButton:hover {{ background:#047857; }}"
        )
        btn_create.clicked.connect(self.add_user)

        btn_clear = QPushButton("Clear Form")
        btn_clear.setFixedHeight(36)
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{_SEC}; border:1.5px solid {_BRD};"
            f" border-radius:9px; font-size:12px; font-weight:600; }}"
            f"QPushButton:hover {{ background:{_BG}; }}"
        )
        btn_clear.clicked.connect(self.clear_form)

        f_layout.addWidget(btn_create)
        f_layout.addWidget(btn_clear)
        f_layout.addStretch()
        layout.addWidget(form_frame)

        # ── RIGHT: TABLE ──────────────────────────────────────────────────
        table_frame = QFrame()
        table_frame.setStyleSheet(
            f"QFrame {{ background:white; border-radius:14px; border:1.5px solid {_BRD}; }}"
        )
        t_layout = QVBoxLayout(table_frame)
        t_layout.setContentsMargins(0, 0, 0, 0)
        t_layout.setSpacing(0)

        # Toolbar inside table card
        toolbar = QWidget()
        toolbar.setStyleSheet(f"background: {_BG}; border-bottom: 1px solid {_BRD};")
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(16, 12, 16, 12)
        tb_lay.setSpacing(10)

        tbl_title = QLabel("All Users")
        tbl_title.setStyleSheet(f"font-size:14px; font-weight:900; color:{_TXT}; background:transparent; border:none;")
        tb_lay.addWidget(tbl_title)
        tb_lay.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search users...")
        self.search_input.setFixedHeight(34)
        self.search_input.setMaximumWidth(220)
        self.search_input.setStyleSheet(
            f"QLineEdit {{ background:white; border:1.5px solid {_BRD}; border-radius:8px;"
            f" padding:0 10px; font-size:12px; color:{_TXT}; }}"
            f"QLineEdit:focus {{ border-color:{_P}; }}"
        )
        self.search_input.textChanged.connect(lambda: (self.pagination.reset(), self.load_users()))
        tb_lay.addWidget(self.search_input)

        btn_refresh = QPushButton()
        btn_refresh.setIcon(qta.icon('fa5s.sync-alt', color=_P))
        btn_refresh.setIconSize(QSize(14, 14))
        btn_refresh.setFixedSize(34, 34)
        btn_refresh.setToolTip("Refresh")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(
            f"QPushButton {{ background:white; border:1.5px solid {_BRD}; border-radius:8px; }}"
            f"QPushButton:hover {{ background:{_P_LT}; border-color:{_P}; }}"
        )
        btn_refresh.clicked.connect(self.load_users)
        tb_lay.addWidget(btn_refresh)
        t_layout.addWidget(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Username", "Role", "Status", "Actions"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 130)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 110)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 130)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setStyleSheet(TABLE_STYLE)
        t_layout.addWidget(self.table)

        # Pagination
        pag_wrap = QWidget()
        pag_wrap.setStyleSheet(f"background:{_BG}; border-top:1px solid {_BRD};")
        pw_lay = QHBoxLayout(pag_wrap)
        pw_lay.setContentsMargins(16, 8, 16, 8)
        self.pagination = PaginationControl()
        self.pagination.page_changed.connect(self.load_users)
        self.pagination.limit_changed.connect(self.load_users)
        pw_lay.addWidget(self.pagination)
        t_layout.addWidget(pag_wrap)

        layout.addWidget(table_frame, stretch=1)
        self.load_users()
        
    def load_users(self, *args):
        self.table.setRowCount(0)
        search = self.search_input.text().lower()
        skip = (self.pagination.current_page - 1) * self.pagination.page_size
        limit = self.pagination.page_size
        
        # NOTE: If search is active, we might want to filter FIRST then paginate.
        # But get_users() doesn't support search query yet.
        # For simplicity with search, I will load all then filter then paginate manually if search is present.
        # Or I can update get_users to support search.
        # Given the "Users" list is small, I will implement smart logic:
        
        if search:
            # Client side filtering
            all_users = get_users() # Original behavior returns list
            filtered = [u for u in all_users if search in u['username'].lower()]
            total = len(filtered)
            self.pagination.set_total_records(total)
            
            # Slice
            start = skip
            end = start + limit
            users = filtered[start:end]
        else:
            # Server side pagination
            users, total = get_users(skip=skip, limit=limit)
            self.pagination.set_total_records(total)
        
        for user in users:
                
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(user['username']))
            self.table.setItem(row, 1, QTableWidgetItem(user['role']))
            
            # Status badge
            active = user.get('active', True)
            badge = QLabel("● Active" if active else "● Inactive")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background:{'#DCFCE7' if active else '#FEE2E2'};"
                f" color:{'#16A34A' if active else '#DC2626'};"
                f" font-size:11px; font-weight:800; padding:4px 12px;"
                f" border-radius:20px; border:none;"
            )
            bw = QWidget(); bw.setStyleSheet("background:transparent;")
            bl = QHBoxLayout(bw); bl.setContentsMargins(8,4,8,4); bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bl.addWidget(badge)
            self.table.setCellWidget(row, 2, bw)

            # Toggle button
            btn_toggle = QPushButton("Deactivate" if active else "Activate")
            btn_toggle.setFixedHeight(30)
            btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            if active:
                btn_toggle.setStyleSheet(
                    "QPushButton { background:#FEF2F2; color:#DC2626; border:1.5px solid #FECACA;"
                    " border-radius:8px; font-size:11px; font-weight:700; padding:0 10px; }"
                    "QPushButton:hover { background:#FEE2E2; }"
                )
            else:
                btn_toggle.setStyleSheet(
                    f"QPushButton {{ background:{_P_LT}; color:{_P}; border:1.5px solid #A7F3D0;"
                    f" border-radius:8px; font-size:11px; font-weight:700; padding:0 10px; }}"
                    f"QPushButton:hover {{ background:#D1FAE5; }}"
                )
            btn_toggle.clicked.connect(lambda ch, u=user: self.toggle_user_status(u))
            cw = QWidget(); cw.setStyleSheet("background:transparent;")
            cl = QHBoxLayout(cw); cl.setContentsMargins(8,4,8,4)
            cl.addWidget(btn_toggle)
            self.table.setCellWidget(row, 3, cw)

            self.table.setRowHeight(row, 48)
            
    def on_role_change(self, text):
        is_rider = (text == "Rider")
        for w in (self.lbl_phone, self.phone_input, self.lbl_vehicle, self.vehicle_input):
            w.setVisible(is_rider)

    def add_user(self):
        user = self.username_input.text().strip()
        pwd = self.password_input.text().strip()
        role = self.role_combo.currentText()
        phone = self.phone_input.text().strip()
        vehicle = self.vehicle_input.text().strip()
        
        if not user or not pwd:
            QMessageBox.warning(self, "Error", "Username and Password are required!")
            return
            
        try:
            create_user(user, pwd, role, phone, vehicle)
            QMessageBox.information(self, "Success", f"User {user} created successfully!")
            self.clear_form()
            self.load_users()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def toggle_user_status(self, user):
        try:
            new_status = not user.get('active', True)
            toggle_user(user['_id'], new_status)
            self.load_users()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def clear_form(self):
        self.username_input.clear()
        self.password_input.clear()
        self.role_combo.setCurrentIndex(0)
        self.phone_input.clear()
        self.vehicle_input.clear()
        for w in (self.lbl_phone, self.phone_input, self.lbl_vehicle, self.vehicle_input):
            w.hide()
