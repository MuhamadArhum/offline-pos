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

# ── Design tokens ──────────────────────────────────────────────────────────
_P    = "#059669"
_P_DK = "#047857"
_P_LT = "#ECFDF5"
_P_MD = "#D1FAE5"
_BRD  = "#E2E8F0"
_BG   = "#F0F2F5"
_SURF = "#FFFFFF"
_TXT  = "#1E293B"
_SEC  = "#64748B"
_HINT = "#94A3B8"

# ── Role badge colors {role_lower: (fg, bg)} ───────────────────────────────
_ROLE_COLORS = {
    "admin":              ("#7C3AED", "#EDE9FE"),
    "manager":            ("#4338CA", "#EEF2FF"),
    "cashier":            ("#059669", "#D1FAE5"),
    "kitchen supervisor": ("#D97706", "#FEF3C7"),
    "kitchen_supervisor": ("#D97706", "#FEF3C7"),
    "waiter":             ("#0284C7", "#E0F2FE"),
    "rider":              ("#0D9488", "#CCFBF1"),
}

TABLE_STYLE = f"""
QTableWidget {{
    background: white; alternate-background-color: {_P_LT};
    border: none; font-size: 13px; color: {_TXT};
    outline: none; gridline-color: transparent;
    selection-background-color: {_P_MD}; selection-color: {_P_DK};
}}
QTableWidget::item {{ padding: 10px 14px; border: none; border-bottom: 1px solid #F1F5F9; }}
QTableWidget::item:selected {{ background: {_P_MD}; color: {_P_DK}; }}
QHeaderView::section {{
    background: {_BG}; color: {_SEC};
    font-size: 10px; font-weight: 800; letter-spacing: 0.6px;
    padding: 10px 14px; border: none; border-bottom: 2px solid {_BRD};
}}
QHeaderView {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 5px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: {_BRD}; border-radius: 3px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {_P}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


def _mk_input(placeholder="", echo=None):
    """Consistently styled QLineEdit."""
    le = QLineEdit()
    le.setPlaceholderText(placeholder)
    le.setMinimumHeight(36)
    le.setStyleSheet(
        f"QLineEdit {{ background: white; border: 1.5px solid {_BRD}; border-radius: 8px;"
        f" padding: 0 10px; font-size: 12px; color: {_TXT}; }}"
        f"QLineEdit:focus {{ border-color: {_P}; background: #FAFFFD; }}"
    )
    if echo:
        le.setEchoMode(echo)
    return le


def _mk_combo(items):
    """Consistently styled QComboBox."""
    cb = QComboBox()
    cb.addItems(items)
    cb.setMinimumHeight(36)
    cb.setStyleSheet(
        f"QComboBox {{ background: white; border: 1.5px solid {_BRD}; border-radius: 8px;"
        f" padding: 0 10px; font-size: 12px; color: {_TXT}; }}"
        f"QComboBox:focus {{ border-color: {_P}; }}"
        f"QComboBox::drop-down {{ border: none; padding-right: 8px; }}"
        f"QComboBox QAbstractItemView {{"
        f"  background: white; border: 1.5px solid {_BRD}; border-radius: 6px;"
        f"  selection-background-color: {_P_LT}; selection-color: {_P};"
        f"  font-size: 12px; padding: 2px; outline: 0;"
        f"}}"
    )
    return cb


def _field_lbl(text):
    l = QLabel(text)
    l.setStyleSheet(
        f"font-size: 10px; font-weight: 800; color: {_HINT}; letter-spacing: 0.5px;"
        f" border: none; background: transparent;"
    )
    return l


class UsersPage(QWidget):
    def __init__(self):
        super().__init__()
        self.users_cache = []
        self._pwd_visible = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(self._build_form(), 0)
        layout.addWidget(self._build_table_panel(), 1)

        self.load_users()
        self._load_stats()

    # ── FORM PANEL ─────────────────────────────────────────────────────────
    def _build_form(self):
        form_frame = QFrame()
        form_frame.setStyleSheet(
            f"QFrame {{ background: white; border-radius: 14px; border: 1.5px solid {_BRD}; }}"
        )
        form_frame.setMinimumWidth(240)
        form_frame.setMaximumWidth(300)
        form_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        fl = QVBoxLayout(form_frame)
        fl.setContentsMargins(20, 20, 20, 20)
        fl.setSpacing(10)

        # Header
        h_row = QHBoxLayout(); h_row.setSpacing(10)
        ico = QLabel()
        ico.setFixedSize(38, 38)
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico.setPixmap(qta.icon('fa5s.user-plus', color='white').pixmap(16, 16))
        ico.setStyleSheet(f"background: {_P}; border-radius: 10px; border: none;")
        lbl_title = QLabel("Add User")
        lbl_title.setStyleSheet(
            f"font-size: 15px; font-weight: 900; color: {_TXT}; border: none; background: transparent;"
        )
        h_row.addWidget(ico); h_row.addWidget(lbl_title); h_row.addStretch()
        fl.addLayout(h_row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_BRD}; border: none;")
        fl.addWidget(sep)
        fl.addSpacing(2)

        # Username
        fl.addWidget(_field_lbl("USERNAME"))
        self.username_input = _mk_input("e.g. john_doe")
        fl.addWidget(self.username_input)

        fl.addSpacing(4)

        # Password with eye toggle
        fl.addWidget(_field_lbl("PASSWORD"))
        self.password_input = _mk_input("Min 6 characters", echo=QLineEdit.EchoMode.Password)
        self._eye_action = self.password_input.addAction(
            qta.icon('fa5s.eye', color=_HINT),
            QLineEdit.ActionPosition.TrailingPosition
        )
        self._eye_action.triggered.connect(self._toggle_password)
        fl.addWidget(self.password_input)

        fl.addSpacing(4)

        # Role
        fl.addWidget(_field_lbl("ROLE"))
        self.role_combo = _mk_combo(
            ["Cashier", "Manager", "Admin", "Rider", "Waiter", "Kitchen Supervisor"]
        )
        self.role_combo.currentTextChanged.connect(self.on_role_change)
        fl.addWidget(self.role_combo)

        # Rider-only fields
        fl.addSpacing(4)
        self.lbl_phone   = _field_lbl("PHONE (RIDER)")
        self.phone_input = _mk_input("03XX-XXXXXXX")
        self.lbl_vehicle   = _field_lbl("VEHICLE NO (RIDER)")
        self.vehicle_input = _mk_input("ABC-123")
        for w in (self.lbl_phone, self.phone_input, self.lbl_vehicle, self.vehicle_input):
            fl.addWidget(w)
            w.hide()

        fl.addSpacing(8)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background: {_BRD}; border: none;")
        fl.addWidget(sep2)
        fl.addSpacing(4)

        # Buttons
        btn_create = QPushButton("  Create User")
        btn_create.setIcon(qta.icon('fa5s.user-plus', color='white'))
        btn_create.setIconSize(QSize(14, 14))
        btn_create.setFixedHeight(40)
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.setStyleSheet(
            f"QPushButton {{ background: {_P}; color: white; border: none; border-radius: 9px;"
            f" font-size: 12px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: {_P_DK}; }}"
            f"QPushButton:pressed {{ background: {_P_DK}; }}"
        )
        btn_create.clicked.connect(self.add_user)

        btn_clear = QPushButton("Clear Form")
        btn_clear.setFixedHeight(34)
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_SEC}; border: 1.5px solid {_BRD};"
            f" border-radius: 8px; font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {_BG}; color: {_TXT}; }}"
        )
        btn_clear.clicked.connect(self.clear_form)

        fl.addWidget(btn_create)
        fl.addSpacing(4)
        fl.addWidget(btn_clear)
        fl.addStretch()

        return form_frame

    # ── TABLE PANEL ────────────────────────────────────────────────────────
    def _build_table_panel(self):
        table_frame = QFrame()
        table_frame.setStyleSheet(
            f"QFrame {{ background: white; border-radius: 14px; border: 1.5px solid {_BRD}; }}"
        )
        tl = QVBoxLayout(table_frame)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(0)

        # ── Toolbar ────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setStyleSheet(
            f"background: {_BG}; border-bottom: 1px solid {_BRD};"
            f" border-top-left-radius: 14px; border-top-right-radius: 14px;"
        )
        toolbar.setFixedHeight(52)
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(16, 0, 16, 0)
        tb.setSpacing(10)

        tbl_title = QLabel("All Users")
        tbl_title.setStyleSheet(
            f"font-size: 14px; font-weight: 900; color: {_TXT}; background: transparent; border: none;"
        )
        tb.addWidget(tbl_title)

        self.count_badge = QLabel("")
        self.count_badge.setStyleSheet(
            f"background: {_P_LT}; color: {_P}; font-size: 11px; font-weight: 800;"
            f" padding: 2px 10px; border-radius: 10px; border: none;"
        )
        self.count_badge.hide()
        tb.addWidget(self.count_badge)
        tb.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search users...")
        self.search_input.setFixedHeight(32)
        self.search_input.setMaximumWidth(200)
        self.search_input.setStyleSheet(
            f"QLineEdit {{ background: white; border: 1.5px solid {_BRD}; border-radius: 7px;"
            f" padding: 0 10px; font-size: 12px; color: {_TXT}; }}"
            f"QLineEdit:focus {{ border-color: {_P}; }}"
        )
        self.search_input.textChanged.connect(lambda: (self.pagination.reset(), self.load_users()))
        tb.addWidget(self.search_input)

        btn_refresh = QPushButton()
        btn_refresh.setIcon(qta.icon('fa5s.sync-alt', color=_P))
        btn_refresh.setIconSize(QSize(14, 14))
        btn_refresh.setFixedSize(32, 32)
        btn_refresh.setToolTip("Refresh")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(
            f"QPushButton {{ background: white; border: 1.5px solid {_BRD}; border-radius: 7px; }}"
            f"QPushButton:hover {{ background: {_P_LT}; border-color: {_P}; }}"
        )
        btn_refresh.clicked.connect(lambda: (self.load_users(), self._load_stats()))
        tb.addWidget(btn_refresh)
        tl.addWidget(toolbar)

        # ── Stats strip ────────────────────────────────────────────────────
        stats_strip = QWidget()
        stats_strip.setStyleSheet(f"background: white; border-bottom: 1px solid #F1F5F9;")
        stats_strip.setFixedHeight(46)
        ss = QHBoxLayout(stats_strip)
        ss.setContentsMargins(20, 0, 20, 0)
        ss.setSpacing(0)

        def _stat_chip(label, val_attr, val_color=_TXT):
            col = QHBoxLayout(); col.setSpacing(6)
            val_lbl = QLabel("—")
            val_lbl.setStyleSheet(
                f"font-size: 18px; font-weight: 900; color: {val_color};"
                f" background: transparent; border: none;"
            )
            txt_lbl = QLabel(label)
            txt_lbl.setStyleSheet(
                f"font-size: 10px; font-weight: 600; color: {_HINT};"
                f" background: transparent; border: none;"
            )
            col.addWidget(val_lbl); col.addWidget(txt_lbl)
            setattr(self, val_attr, val_lbl)
            return col

        ss.addLayout(_stat_chip("Total", "_stat_total"))

        for _ in range(2):
            vsep = QFrame(); vsep.setFrameShape(QFrame.Shape.VLine)
            vsep.setStyleSheet(f"background: {_BRD}; border: none; max-width: 1px;")
            vsep.setFixedWidth(1)
            ss.addSpacing(20); ss.addWidget(vsep); ss.addSpacing(20)
            if _ == 0:
                ss.addLayout(_stat_chip("Active", "_stat_active"))
            else:
                ss.addLayout(_stat_chip("Inactive", "_stat_inactive"))

        ss.addStretch()
        tl.addWidget(stats_strip)

        # ── Table ──────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Username", "Role", "Status", "Actions"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 140)
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
        tl.addWidget(self.table)

        # ── Pagination ─────────────────────────────────────────────────────
        pag_wrap = QWidget()
        pag_wrap.setStyleSheet(
            f"background: {_BG}; border-top: 1px solid {_BRD};"
            f" border-bottom-left-radius: 14px; border-bottom-right-radius: 14px;"
        )
        pw = QHBoxLayout(pag_wrap)
        pw.setContentsMargins(16, 8, 16, 8)
        self.pagination = PaginationControl()
        self.pagination.page_changed.connect(self.load_users)
        self.pagination.limit_changed.connect(self.load_users)
        pw.addWidget(self.pagination)
        tl.addWidget(pag_wrap)

        return table_frame

    # ── SLOTS ──────────────────────────────────────────────────────────────
    def _toggle_password(self):
        self._pwd_visible = not self._pwd_visible
        if self._pwd_visible:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._eye_action.setIcon(qta.icon('fa5s.eye-slash', color=_P))
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._eye_action.setIcon(qta.icon('fa5s.eye', color=_HINT))

    def _load_stats(self):
        """Fetch all users once to compute aggregate counts."""
        try:
            result = get_users()
            all_users = result[0] if isinstance(result, tuple) else result
            total    = len(all_users)
            active   = sum(1 for u in all_users if u.get('active', True))
            inactive = total - active

            self._stat_total.setText(str(total))
            self._stat_total.setStyleSheet(
                f"font-size: 18px; font-weight: 900; color: {_TXT};"
                f" background: transparent; border: none;"
            )
            self._stat_active.setText(str(active))
            self._stat_active.setStyleSheet(
                f"font-size: 18px; font-weight: 900; color: #16A34A;"
                f" background: transparent; border: none;"
            )
            self._stat_inactive.setText(str(inactive))
            self._stat_inactive.setStyleSheet(
                f"font-size: 18px; font-weight: 900; color: #DC2626;"
                f" background: transparent; border: none;"
            )
            self.count_badge.setText(f"  {total} users  ")
            self.count_badge.show()
        except Exception:
            pass

    def load_users(self, *args):
        self.table.setRowCount(0)
        search = self.search_input.text().lower()
        skip  = (self.pagination.current_page - 1) * self.pagination.page_size
        limit = self.pagination.page_size

        if search:
            result = get_users()
            all_users = result[0] if isinstance(result, tuple) else result
            filtered  = [u for u in all_users if search in u['username'].lower()]
            total     = len(filtered)
            self.pagination.set_total_records(total)
            users = filtered[skip:skip + limit]
        else:
            users, total = get_users(skip=skip, limit=limit)
            self.pagination.set_total_records(total)

        for user in users:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Col 0: Username
            uname_item = QTableWidgetItem(f"  {user['username']}")
            uname_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
            self.table.setItem(row, 0, uname_item)

            # Col 1: Role badge (color-coded)
            role_raw = user.get('role', '')
            fg_c, bg_c = _ROLE_COLORS.get(role_raw.lower(), (_SEC, "#F1F5F9"))
            role_badge = QLabel(role_raw.replace("_", " ").title())
            role_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            role_badge.setStyleSheet(
                f"background: {bg_c}; color: {fg_c}; font-size: 10px; font-weight: 800;"
                f" padding: 3px 10px; border-radius: 10px; border: none; letter-spacing: 0.3px;"
            )
            rw = QWidget(); rw.setStyleSheet("background: transparent;")
            rl = QHBoxLayout(rw); rl.setContentsMargins(8, 4, 8, 4)
            rl.addWidget(role_badge); rl.addStretch()
            self.table.setCellWidget(row, 1, rw)

            # Col 2: Status badge
            active = user.get('active', True)
            status_badge = QLabel("● Active" if active else "● Inactive")
            status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_badge.setStyleSheet(
                f"background: {'#DCFCE7' if active else '#FEE2E2'};"
                f" color: {'#16A34A' if active else '#DC2626'};"
                f" font-size: 11px; font-weight: 800; padding: 4px 12px;"
                f" border-radius: 20px; border: none;"
            )
            bw = QWidget(); bw.setStyleSheet("background: transparent;")
            bl = QHBoxLayout(bw); bl.setContentsMargins(8, 4, 8, 4)
            bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bl.addWidget(status_badge)
            self.table.setCellWidget(row, 2, bw)

            # Col 3: Toggle button
            btn_toggle = QPushButton("Deactivate" if active else "Activate")
            btn_toggle.setFixedHeight(30)
            btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            if active:
                btn_toggle.setStyleSheet(
                    "QPushButton { background: #FEF2F2; color: #DC2626; border: 1.5px solid #FECACA;"
                    " border-radius: 8px; font-size: 11px; font-weight: 700; padding: 0 10px; }"
                    "QPushButton:hover { background: #FEE2E2; }"
                )
            else:
                btn_toggle.setStyleSheet(
                    f"QPushButton {{ background: {_P_LT}; color: {_P}; border: 1.5px solid #A7F3D0;"
                    f" border-radius: 8px; font-size: 11px; font-weight: 700; padding: 0 10px; }}"
                    f"QPushButton:hover {{ background: #D1FAE5; }}"
                )
            btn_toggle.clicked.connect(lambda ch, u=user: self.toggle_user_status(u))
            cw = QWidget(); cw.setStyleSheet("background: transparent;")
            cl = QHBoxLayout(cw); cl.setContentsMargins(8, 4, 8, 4)
            cl.addWidget(btn_toggle)
            self.table.setCellWidget(row, 3, cw)

            self.table.setRowHeight(row, 50)

        # Empty state
        if self.table.rowCount() == 0:
            self.table.setRowCount(1)
            self.table.setSpan(0, 0, 1, 4)
            empty = QTableWidgetItem("No users found")
            empty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setForeground(QColor(_HINT))
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.table.setItem(0, 0, empty)
            self.table.setRowHeight(0, 80)

    def on_role_change(self, text):
        is_rider = (text == "Rider")
        for w in (self.lbl_phone, self.phone_input, self.lbl_vehicle, self.vehicle_input):
            w.setVisible(is_rider)

    def add_user(self):
        user    = self.username_input.text().strip()
        pwd     = self.password_input.text().strip()
        role    = self.role_combo.currentText()
        phone   = self.phone_input.text().strip()
        vehicle = self.vehicle_input.text().strip()

        if not user or not pwd:
            QMessageBox.warning(self, "Error", "Username and Password are required!")
            return

        try:
            create_user(user, pwd, role, phone, vehicle)
            QMessageBox.information(self, "Success", f"User '{user}' created successfully!")
            self.clear_form()
            self.load_users()
            self._load_stats()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def toggle_user_status(self, user):
        try:
            new_status = not user.get('active', True)
            toggle_user(user['_id'], new_status)
            self.load_users()
            self._load_stats()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def clear_form(self):
        self.username_input.clear()
        self.password_input.clear()
        # Reset eye icon
        self._pwd_visible = False
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._eye_action.setIcon(qta.icon('fa5s.eye', color=_HINT))
        self.role_combo.setCurrentIndex(0)
        self.phone_input.clear()
        self.vehicle_input.clear()
        for w in (self.lbl_phone, self.phone_input, self.lbl_vehicle, self.vehicle_input):
            w.hide()
