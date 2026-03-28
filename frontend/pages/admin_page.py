from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QPushButton, QTableWidget, QHeaderView,
                             QLineEdit, QComboBox, QMessageBox, QTabWidget, QCheckBox,
                             QGroupBox, QRadioButton, QFormLayout, QSpinBox, QScrollArea,
                             QTableWidgetItem, QAbstractItemView, QSizePolicy)
from PyQt6.QtPrintSupport import QPrinterInfo
import json
import os
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont
import qtawesome as qta
from backend.services.user_service import get_users, create_user, toggle_user
from backend.core.permissions import ROLE_PERMISSIONS, MODULE_NAMES, get_all_roles
from backend.core.audit import get_logs
from frontend.theme import Theme
from frontend.components.flow_layout import FlowLayout
from frontend.pages.users_page import UsersPage
from frontend.components.pagination import PaginationControl
from frontend.shared_ui import GLOBAL_STYLE, C, page_header

# ─────────────────────────────────────────────────────────────────────────────
#  DESIGN TOKENS  ── Emerald Green primary theme
# ─────────────────────────────────────────────────────────────────────────────
_PRIMARY    = "#059669"   # Emerald 600
_PRIMARY_DK = "#047857"   # Emerald 700
_PRIMARY_LT = "#D1FAE5"   # Emerald 100
_PRIMARY_XL = "#ECFDF5"   # Emerald 50  (very light tint)
_SUCCESS    = "#10B981"
_SUCCESS_LT = "#D1FAE5"
_DANGER     = "#EF4444"
_DANGER_LT  = "#FEE2E2"
_WARNING    = "#F59E0B"
_WARNING_LT = "#FEF3C7"
_INFO       = "#0EA5E9"
_INFO_LT    = "#E0F2FE"
_DARK1      = "#022C22"   # Deep forest green  (dialog headers)
_DARK2      = "#064E3B"   # Emerald 900
_TEXT_PRI   = "#1E293B"
_TEXT_SEC   = "#64748B"
_TEXT_HINT  = "#94A3B8"
_BG         = "#F0FDF9"   # Green-tinted page bg
_SURFACE    = "#FFFFFF"
_BORDER     = "#A7F3D0"   # Light green border
_BORDER2    = "#E2E8F0"   # Neutral border for tables
_DIVIDER    = "#ECFDF5"   # Divider tint

# ─────────────────────────────────────────────────────────────────────────────
#  PAGE-LEVEL STYLESHEET
# ─────────────────────────────────────────────────────────────────────────────
ADMIN_STYLE = f"""
* {{ font-family: 'Segoe UI', 'SF Pro Display', system-ui, sans-serif; }}

/* ── TABS ── */
QTabWidget::pane {{ border: none; background: {_BG}; }}
QTabBar::tab {{
    background: transparent;
    color: {_TEXT_SEC};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 11px 26px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.2px;
    min-width: 110px;
}}
QTabBar::tab:hover:!selected {{
    color: {_PRIMARY};
    background: {_PRIMARY_LT}60;
    border-radius: 6px 6px 0 0;
}}
QTabBar::tab:selected {{
    color: {_PRIMARY};
    border-bottom: 2px solid {_PRIMARY};
}}

/* ── SCROLLBARS ── */
QScrollBar:vertical {{
    background: transparent; width: 6px; border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER}; border-radius: 3px; min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{ background: {_PRIMARY}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent; height: 6px; border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {_BORDER}; border-radius: 3px; min-width: 28px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QToolTip {{
    background: {_DARK2}; color: white; border: none;
    border-radius: 6px; padding: 5px 10px; font-size: 11px;
}}
"""

# ─────────────────────────────────────────────────────────────────────────────
#  TABLE STYLESHEET  ── used inside table card frames
# ─────────────────────────────────────────────────────────────────────────────
TABLE_STYLE = f"""
QTableWidget {{
    background: {_SURFACE};
    alternate-background-color: {_PRIMARY_XL};
    border: none;
    font-size: 13px;
    color: {_TEXT_PRI};
    outline: none;
    gridline-color: transparent;
    selection-background-color: {_PRIMARY_LT};
    selection-color: {_PRIMARY_DK};
}}
QTableWidget::item {{
    padding: 9px 14px;
    border: none;
    border-bottom: 1px solid {_DIVIDER};
}}
QTableWidget::item:selected {{
    background: {_PRIMARY_LT};
    color: {_PRIMARY_DK};
}}
QHeaderView::section {{
    background: {_BG};
    color: {_TEXT_SEC};
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.7px;
    padding: 11px 14px;
    border: none;
    border-bottom: 2px solid {_BORDER};
    text-transform: uppercase;
}}
QHeaderView::section:hover {{
    background: {_PRIMARY_LT};
    color: {_PRIMARY};
}}
QHeaderView {{ border: none; }}
QScrollBar:vertical {{
    background: transparent; width: 6px; border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER}; border-radius: 3px; min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{ background: {_PRIMARY}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent; height: 6px; border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {_BORDER}; border-radius: 3px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _divider():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: {_BORDER}; border: none;")
    return f

def _badge(text, bg, fg="white", radius=8):
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(
        f"background: {bg}; color: {fg}; font-size: 10px; font-weight: 800;"
        f" padding: 3px 10px; border-radius: {radius}px; border: none;"
        f" letter-spacing: 0.3px;"
    )
    return lbl

def _action_btn(text, icon_name, bg, hover_bg, fg="white", height=38):
    """Full-width action button — icon + label, consistent height."""
    btn = QPushButton(f"  {text}")
    btn.setIcon(qta.icon(icon_name, color=fg))
    btn.setIconSize(QSize(15, 15))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
    btn.setStyleSheet(
        f"QPushButton {{"
        f"  background: {bg}; color: {fg};"
        f"  border: none; border-radius: 9px;"
        f"  font-size: 12px; font-weight: 700;"
        f"  padding: 0 18px; text-align: left;"
        f"}}"
        f"QPushButton:hover {{ background: {hover_bg}; }}"
        f"QPushButton:pressed {{ background: {hover_bg}; }}"
    )
    return btn

def _icon_btn(icon_name, icon_color, tooltip="", size=32):
    """Square icon-only row-action button."""
    btn = QPushButton()
    btn.setIcon(qta.icon(icon_name, color=icon_color))
    btn.setIconSize(QSize(14, 14))
    btn.setFixedSize(size, size)
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"QPushButton {{"
        f"  background: transparent;"
        f"  border: 1.5px solid {_BORDER2};"
        f"  border-radius: 7px;"
        f"}}"
        f"QPushButton:hover {{"
        f"  background: {icon_color}1A;"
        f"  border-color: {icon_color};"
        f"}}"
        f"QPushButton:pressed {{ background: {icon_color}30; }}"
    )
    return btn

def _text_btn(text, color, hover_bg, height=32, border=True):
    """Outlined text-only row-action button."""
    border_style = f"border: 1.5px solid {color};" if border else "border: none;"
    btn = QPushButton(text)
    btn.setFixedHeight(height)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"QPushButton {{"
        f"  background: transparent; color: {color};"
        f"  {border_style} border-radius: 7px;"
        f"  font-size: 11px; font-weight: 700; padding: 0 12px;"
        f"}}"
        f"QPushButton:hover {{ background: {hover_bg}; }}"
    )
    return btn

def _field_lbl(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size: 10px; font-weight: 800; color: {_TEXT_HINT};"
        f" letter-spacing: 0.5px; border: none; background: transparent;"
    )
    return lbl

def _card(radius=14, border=None):
    f = QFrame()
    bc = border or _BORDER2
    f.setStyleSheet(
        f"QFrame {{ background: {_SURFACE}; border-radius: {radius}px;"
        f" border: 1.5px solid {bc}; }}"
    )
    return f


# ─────────────────────────────────────────────────────────────────────────────
#  AUDIT TAB  ── green theme · responsive columns · polished badges
# ─────────────────────────────────────────────────────────────────────────────
class AuditTab(QWidget):
    def __init__(self):
        super().__init__()
        self._logs_cache = []
        self.setStyleSheet(f"background: {_BG};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # ── Header control bar ───────────────────────────────────────────
        ctrl = QFrame()
        ctrl.setStyleSheet(
            f"QFrame {{ background: {_SURFACE}; border-radius: 12px;"
            f" border: 1.5px solid {_BORDER}; }}"
        )
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(12)

        ico_wrap = QLabel()
        ico_wrap.setFixedSize(42, 42)
        ico_wrap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico_wrap.setPixmap(qta.icon('fa5s.clipboard-list', color=_INFO).pixmap(20, 20))
        ico_wrap.setStyleSheet(
            f"background: {_INFO_LT}; border-radius: 10px; border: none;"
        )

        t_col = QVBoxLayout(); t_col.setSpacing(2)
        t1 = QLabel("Audit Logs")
        t1.setStyleSheet(
            f"font-size: 15px; font-weight: 900; color: {_TEXT_PRI};"
            f" border: none; background: transparent;"
        )
        t2 = QLabel("Complete record of all system activity")
        t2.setStyleSheet(
            f"font-size: 11px; color: {_TEXT_HINT}; border: none; background: transparent;"
        )
        t_col.addWidget(t1); t_col.addWidget(t2)

        cl.addWidget(ico_wrap)
        cl.addSpacing(8)
        cl.addLayout(t_col)
        cl.addStretch()

        # Search filter
        self.search_audit = QLineEdit()
        self.search_audit.setPlaceholderText("Filter by user or action…")
        self.search_audit.setFixedHeight(36)
        self.search_audit.setMaximumWidth(220)
        self.search_audit.setStyleSheet(
            f"QLineEdit {{ background: {_PRIMARY_XL}; border: 1.5px solid {_BORDER};"
            f" border-radius: 8px; padding: 0 10px; font-size: 12px; color: {_TEXT_PRI}; }}"
            f"QLineEdit:focus {{ border-color: {_PRIMARY}; background: white; }}"
        )
        self.search_audit.textChanged.connect(self._filter_logs)
        cl.addWidget(self.search_audit)

        btn_refresh = _action_btn("Refresh", "fa5s.sync-alt", _PRIMARY, _PRIMARY_DK, height=40)
        btn_refresh.clicked.connect(self.load_data)
        cl.addWidget(btn_refresh)
        layout.addWidget(ctrl)

        # ── Action-type legend ───────────────────────────────────────────
        leg_row = QHBoxLayout(); leg_row.setSpacing(6)
        lbl_leg = QLabel("Action Types:")
        lbl_leg.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {_TEXT_HINT};"
            f" border: none; background: transparent;"
        )
        leg_row.addWidget(lbl_leg)
        for label, color in [
            ("Login / Logout", _PRIMARY),
            ("Create / Add",   _INFO),
            ("Update / Edit",  _WARNING),
            ("Delete / Remove",_DANGER),
            ("Error",          _DANGER),
        ]:
            chip = QLabel(f"  ●  {label}  ")
            chip.setStyleSheet(
                f"color: {color}; font-size: 11px; font-weight: 700;"
                f" background: {color}18; padding: 3px 6px;"
                f" border-radius: 12px; border: none;"
            )
            leg_row.addWidget(chip)
        leg_row.addStretch()
        layout.addLayout(leg_row)

        # ── Responsive table card ────────────────────────────────────────
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {_SURFACE}; border-radius: 14px;"
            f" border: 1.5px solid {_BORDER2}; }}"
        )
        tcl = QVBoxLayout(card)
        tcl.setContentsMargins(0, 0, 0, 0)
        tcl.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "User", "Action", "Details"])

        hh = self.table.horizontalHeader()
        # Timestamp — fits content, min 165px
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 175)
        # User — fits content, min 130px
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 140)
        # Action badge — fixed 160px
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 165)
        # Details — stretch to fill remaining space
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        hh.setMinimumSectionSize(100)
        hh.setStretchLastSection(True)

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
        tcl.addWidget(self.table)
        layout.addWidget(card, stretch=1)

        # ── Pagination card ──────────────────────────────────────────────
        pag_card = QFrame()
        pag_card.setStyleSheet(
            f"QFrame {{ background: {_SURFACE}; border-radius: 10px;"
            f" border: 1.5px solid {_BORDER}; }}"
        )
        pl = QHBoxLayout(pag_card)
        pl.setContentsMargins(14, 8, 14, 8)
        self.pagination = PaginationControl()
        self.pagination.page_changed.connect(self.load_data)
        self.pagination.limit_changed.connect(self.load_data)
        pl.addWidget(self.pagination)
        layout.addWidget(pag_card)

        self.load_data()

    _ACTION_MAP = {
        "login":  (_PRIMARY,  _PRIMARY_LT),
        "logout": (_PRIMARY,  _PRIMARY_LT),
        "create": (_INFO,     _INFO_LT),
        "add":    (_INFO,     _INFO_LT),
        "delete": (_DANGER,   _DANGER_LT),
        "remove": (_DANGER,   _DANGER_LT),
        "update": (_WARNING,  _WARNING_LT),
        "edit":   (_WARNING,  _WARNING_LT),
        "error":  (_DANGER,   _DANGER_LT),
    }

    def load_data(self, *args):
        skip  = (self.pagination.current_page - 1) * self.pagination.page_size
        limit = self.pagination.page_size
        logs, total = get_logs(skip=skip, limit=limit)
        self.pagination.set_total_records(total)
        self._logs_cache = list(logs)
        # Re-apply any active filter
        q = self.search_audit.text().strip().lower()
        if q:
            filtered = [
                l for l in self._logs_cache
                if q in l.get('username', '').lower() or q in l.get('action', '').lower()
            ]
            self._render_logs(filtered)
        else:
            self._render_logs(self._logs_cache)

    def _filter_logs(self):
        q = self.search_audit.text().strip().lower()
        if not q:
            self._render_logs(self._logs_cache)
        else:
            filtered = [
                l for l in self._logs_cache
                if q in l.get('username', '').lower() or q in l.get('action', '').lower()
            ]
            self._render_logs(filtered)

    def _render_logs(self, logs):
        self.table.setRowCount(0)

        for log in logs:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # ── Col 0: Timestamp ─────────────────────────────────────────
            ts = log.get('timestamp')
            ts_str = ts.strftime("%Y-%m-%d  %H:%M:%S") if ts else "—"
            ts_item = QTableWidgetItem(ts_str)
            ts_item.setFont(QFont("Consolas", 10))
            ts_item.setForeground(QColor(_TEXT_HINT))
            self.table.setItem(row, 0, ts_item)

            # ── Col 1: Username ──────────────────────────────────────────
            user_item = QTableWidgetItem(f"  {log.get('username', 'Unknown')}")
            user_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            user_item.setForeground(QColor(_PRIMARY))
            self.table.setItem(row, 1, user_item)

            # ── Col 2: Action badge (color-coded) ────────────────────────
            action_text = log.get('action', '')
            fg_c, bg_c = _TEXT_PRI, _BG
            for kw, (fg, bg) in self._ACTION_MAP.items():
                if kw in action_text.lower():
                    fg_c, bg_c = fg, bg
                    break

            badge = _badge(action_text, bg_c, fg_c)
            bw = QWidget()
            bw.setStyleSheet("background: transparent;")
            bl = QHBoxLayout(bw)
            bl.setContentsMargins(8, 3, 8, 3)
            bl.setSpacing(0)
            bl.addWidget(badge)
            bl.addStretch()
            self.table.setCellWidget(row, 2, bw)

            # ── Col 3: Details ───────────────────────────────────────────
            det_item = QTableWidgetItem(log.get('details', ''))
            det_item.setForeground(QColor(_TEXT_SEC))
            self.table.setItem(row, 3, det_item)

            self.table.setRowHeight(row, 50)

        # Empty state
        if self.table.rowCount() == 0:
            self.table.setRowCount(1)
            self.table.setSpan(0, 0, 1, 4)
            empty = QTableWidgetItem("No logs found")
            empty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setForeground(QColor(_TEXT_HINT))
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.table.setItem(0, 0, empty)
            self.table.setRowHeight(0, 80)


# ─────────────────────────────────────────────────────────────────────────────
#  ADMIN PAGE  ── green header chip, fixed tab icons
# ─────────────────────────────────────────────────────────────────────────────
class AdminPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet(GLOBAL_STYLE + ADMIN_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_tabs())

    # ── HEADER ────────────────────────────────────────────────────────────────
    def _build_header(self):
        uname = self.user.get('username', 'Admin') if isinstance(self.user, dict) else str(self.user)
        role  = self.user.get('role', 'admin')     if isinstance(self.user, dict) else 'admin'

        # Green identity chip
        chip = QFrame()
        chip.setStyleSheet(
            f"QFrame {{ background: {_PRIMARY_LT}; border-radius: 22px;"
            f" border: 1.5px solid {_PRIMARY}60; }}"
        )
        chl = QHBoxLayout(chip)
        chl.setContentsMargins(10, 6, 16, 6)
        chl.setSpacing(8)

        avatar = QLabel()
        avatar.setFixedSize(30, 30)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setPixmap(qta.icon('fa5s.user-shield', color='white').pixmap(14, 14))
        avatar.setStyleSheet(
            f"background: {_PRIMARY}; border-radius: 15px; border: none;"
        )

        name_col = QVBoxLayout(); name_col.setSpacing(0)
        n_lbl = QLabel(uname)
        n_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 800; color: {_PRIMARY};"
            f" border: none; background: transparent;"
        )
        r_lbl = QLabel(role.capitalize())
        r_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {_TEXT_SEC};"
            f" border: none; background: transparent;"
        )
        name_col.addWidget(n_lbl)
        name_col.addWidget(r_lbl)

        chl.addWidget(avatar)
        chl.addLayout(name_col)

        return page_header(
            "Admin & Users",
            subtitle="Manage users  ·  Audit trail  ·  Access control",
            right_widget=chip
        )

    # ── TABS ──────────────────────────────────────────────────────────────────
    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet(ADMIN_STYLE)

        self.users_tab = UsersPage()
        self.audit_tab = AuditTab()

        self.tabs.addTab(
            self.users_tab,
            qta.icon('fa5s.users',          color=_PRIMARY),
            "  User Management  "
        )
        self.tabs.addTab(
            self.audit_tab,
            qta.icon('fa5s.clipboard-list', color=_INFO),
            "  Audit Logs  "
        )
        return self.tabs