from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QPushButton, QScrollArea, QGridLayout,
                             QComboBox, QMessageBox, QDialog, QListWidget, QListWidgetItem,
                             QSizePolicy, QAbstractItemView, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont, QPixmap, QLinearGradient, QPainter
import qtawesome as qta
from datetime import datetime
from backend.services.rider_service import get_riders, assign_rider_to_order, update_delivery_status, get_delivery_orders
from frontend.theme import Theme
from frontend.shared_ui import GLOBAL_STYLE, C, page_header, make_ghost_btn

# ─────────────────────────────────────────────────────────────────────────────
#  DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────
_PRIMARY    = "#6366F1"
_PRIMARY_DK = "#4F46E5"
_PRIMARY_LT = "#EEF2FF"
_SUCCESS    = "#059669"
_SUCCESS_LT = "#D1FAE5"
_SUCCESS_MD = "#10B981"
_DANGER     = "#EF4444"
_DANGER_LT  = "#FEE2E2"
_WARNING    = "#D97706"
_WARNING_LT = "#FEF3C7"
_WARNING_BR = "#F59E0B"
_INFO       = "#0284C7"
_INFO_LT    = "#E0F2FE"
_INFO_BR    = "#0EA5E9"
_DARK1      = "#0F172A"
_DARK2      = "#1E293B"
_DARK3      = "#334155"
_TEXT_PRI   = "#0F172A"
_TEXT_SEC   = "#475569"
_TEXT_HINT  = "#94A3B8"
_BG         = "#F1F5F9"
_SURFACE    = "#FFFFFF"
_BORDER     = "#E2E8F0"
_DIVIDER    = "#F8FAFC"

DEL_STYLE = f"""
* {{ font-family: 'Segoe UI', 'SF Pro Display', system-ui, sans-serif; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{
    background: transparent; width: 6px; border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: #CBD5E1; border-radius: 3px; min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: #94A3B8; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QListWidget {{
    background: {_SURFACE}; border: 1.5px solid {_BORDER};
    border-radius: 12px; padding: 6px; outline: none;
}}
QListWidget::item {{
    border-radius: 10px; padding: 12px 16px; border: none;
    color: {_TEXT_PRI}; font-size: 13px; font-weight: 600;
    margin: 2px 0;
}}
QListWidget::item:selected {{
    background: {_PRIMARY_LT}; color: {_PRIMARY};
    border: 1px solid {_PRIMARY}22;
}}
QListWidget::item:hover:!selected {{ background: {_BG}; }}

QDialog {{ background: {_BG}; }}
QMessageBox {{ background: {_SURFACE}; }}
QMessageBox QPushButton {{
    background: {_PRIMARY}; color: white; border: none; border-radius: 8px;
    padding: 8px 22px; font-weight: 700; min-width: 90px;
}}
QMessageBox QPushButton:hover {{ background: {_PRIMARY_DK}; }}
QToolTip {{
    background: {_DARK2}; color: white; border: none;
    border-radius: 6px; padding: 5px 10px; font-size: 11px;
}}
"""

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _divider():
    f = QFrame(); f.setFrameShape(QFrame.Shape.HLine); f.setFixedHeight(1)
    f.setStyleSheet(f"background:{_BORDER}; border:none;")
    return f

def _badge(text, bg, fg="white", radius=6):
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(
        f"background:{bg}; color:{fg}; font-size:10px; font-weight:800;"
        f" padding:3px 10px; border-radius:{radius}px; border:none; letter-spacing:0.5px;"
    )
    return lbl

def _pill_btn(text, icon_name, bg, hover_bg, fg="white", height=36):
    btn = QPushButton(f"  {text}")
    if icon_name:
        btn.setIcon(qta.icon(icon_name, color=fg))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    btn.setStyleSheet(
        f"QPushButton {{ background:{bg}; color:{fg}; border:none; border-radius:{height//2}px;"
        f" font-size:12px; font-weight:700; padding:0 16px; }}"
        f"QPushButton:hover {{ background:{hover_bg}; }}"
        f"QPushButton:pressed {{ opacity: 0.85; }}"
    )
    return btn

def _ghost_pill(text, icon_name, color, hover_bg, height=36):
    btn = QPushButton(f"  {text}")
    if icon_name:
        btn.setIcon(qta.icon(icon_name, color=color))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    btn.setStyleSheet(
        f"QPushButton {{ background:transparent; color:{color}; border:1.5px solid {color}40;"
        f" border-radius:{height//2}px; font-size:12px; font-weight:700; padding:0 14px; }}"
        f"QPushButton:hover {{ background:{hover_bg}; border-color:{color}80; }}"
    )
    return btn

def _elapsed_text(dt_value):
    """Return human-readable elapsed time string from a datetime or ISO string."""
    if not dt_value:
        return ""
    try:
        if isinstance(dt_value, str):
            dt_value = datetime.fromisoformat(dt_value)
        delta = datetime.now() - dt_value
        mins = int(delta.total_seconds() // 60)
        if mins < 1:   return "Just now"
        if mins < 60:  return f"{mins}m ago"
        hrs = mins // 60; rem = mins % 60
        return f"{hrs}h {rem}m ago"
    except:
        return ""

def _elapsed_color(dt_value):
    """Return color based on elapsed time: green < 20m, amber < 45m, red >= 45m."""
    if not dt_value:
        return _TEXT_HINT
    try:
        if isinstance(dt_value, str):
            dt_value = datetime.fromisoformat(dt_value)
        mins = int((datetime.now() - dt_value).total_seconds() // 60)
        if mins < 20:  return _SUCCESS_MD
        if mins < 45:  return _WARNING_BR
        return _DANGER
    except:
        return _TEXT_HINT


# ─────────────────────────────────────────────────────────────────────────────
#  ASSIGN RIDER DIALOG — redesigned
# ─────────────────────────────────────────────────────────────────────────────
class AssignRiderDialog(QDialog):
    def __init__(self, order, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Rider")
        self.setFixedSize(460, 520)
        self.setStyleSheet(DEL_STYLE)
        self.order = order
        self.selected_rider = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Gradient header ───────────────────────────────────────────────
        hdr = QFrame()
        hdr.setFixedHeight(80)
        hdr.setStyleSheet(
            f"QFrame {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {_PRIMARY},stop:1 {_PRIMARY_DK}); border:none; }}"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(24, 0, 24, 0); hl.setSpacing(14)

        ico_wrap = QLabel()
        ico_wrap.setFixedSize(46, 46)
        ico_wrap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico_wrap.setPixmap(qta.icon('fa5s.motorcycle', color='white').pixmap(24, 24))
        ico_wrap.setStyleSheet("background:rgba(255,255,255,0.15); border-radius:12px; border:none;")

        txt_col = QVBoxLayout(); txt_col.setSpacing(3)
        ttl = QLabel("Assign Rider")
        ttl.setStyleSheet("color:white; font-size:18px; font-weight:900; border:none; background:transparent;")
        sub = QLabel(f"Order #{order.get('invoice_no', '—')}  ·  Rs {order.get('grand_total', 0):,.0f}")
        sub.setStyleSheet("color:rgba(255,255,255,0.75); font-size:12px; font-weight:600; border:none; background:transparent;")
        txt_col.addWidget(ttl); txt_col.addWidget(sub)
        hl.addWidget(ico_wrap); hl.addLayout(txt_col); hl.addStretch()
        root.addWidget(hdr)

        # ── Body ──────────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background:{_BG};")
        bl = QVBoxLayout(body); bl.setContentsMargins(20, 18, 20, 16); bl.setSpacing(14)

        # Order info card
        info_card = QFrame()
        info_card.setStyleSheet(
            f"QFrame {{ background:{_SURFACE}; border-radius:14px; border:1px solid {_BORDER}; }}"
        )
        il = QHBoxLayout(info_card); il.setContentsMargins(16, 12, 16, 12); il.setSpacing(20)

        def _info_block(label, value, color=_TEXT_PRI):
            col = QVBoxLayout(); col.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-size:10px; font-weight:700; color:{_TEXT_HINT}; letter-spacing:0.5px; border:none; background:transparent;")
            val = QLabel(value)
            val.setStyleSheet(f"font-size:13px; font-weight:800; color:{color}; border:none; background:transparent;")
            col.addWidget(lbl); col.addWidget(val)
            return col

        cust = str(order.get('customer_name', '—'))
        addr = str(order.get('delivery_address', '—'))
        addr_short = addr[:28] + "…" if len(addr) > 28 else addr

        il.addLayout(_info_block("CUSTOMER", cust))
        il.addWidget(_v_line())
        il.addLayout(_info_block("DELIVERY TO", f"📍 {addr_short}", _TEXT_SEC))
        il.addStretch()
        bl.addWidget(info_card)

        # Rider list label
        lbl_hdr = QLabel("Select a Rider")
        lbl_hdr.setStyleSheet(f"font-size:12px; font-weight:800; color:{_TEXT_SEC}; letter-spacing:0.3px; border:none; background:transparent;")
        bl.addWidget(lbl_hdr)

        # Rider list
        self.rider_list = QListWidget()
        self.rider_list.setSpacing(2)
        self.rider_list.itemDoubleClicked.connect(self.assign)
        bl.addWidget(self.rider_list)

        root.addWidget(body, stretch=1)

        # ── Footer ────────────────────────────────────────────────────────
        footer = QFrame()
        footer.setStyleSheet(f"QFrame {{ background:{_SURFACE}; border-top:1px solid {_BORDER}; }}")
        fl = QHBoxLayout(footer); fl.setContentsMargins(20, 14, 20, 14); fl.setSpacing(12)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(44); btn_cancel.setFixedWidth(110)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background:{_BG}; border:1.5px solid {_BORDER}; border-radius:10px;"
            f" color:{_TEXT_SEC}; font-weight:700; font-size:13px; }}"
            f"QPushButton:hover {{ background:{_BORDER}; color:{_TEXT_PRI}; }}"
        )
        btn_cancel.clicked.connect(self.reject)

        btn_assign = QPushButton("  Assign Rider")
        btn_assign.setIcon(qta.icon('fa5s.check', color='white'))
        btn_assign.setFixedHeight(44)
        btn_assign.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_assign.setStyleSheet(
            f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {_PRIMARY},stop:1 #818CF8); color:white; border:none; border-radius:10px;"
            f" font-size:13px; font-weight:800; padding:0 28px; }}"
            f"QPushButton:hover {{ background:{_PRIMARY_DK}; }}"
        )
        btn_assign.clicked.connect(self.assign)
        fl.addWidget(btn_cancel); fl.addStretch(); fl.addWidget(btn_assign)
        root.addWidget(footer)

        self.load_riders()

    def load_riders(self):
        riders = get_riders(active_only=True)
        for r in riders:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, r)
            vehicle = r.get('vehicle_no', 'N/A')
            deliveries = r.get('total_deliveries', 0)
            item.setText(f"  🏍  {r['name']}   ·   {vehicle}   ·   {deliveries} deliveries")
            self.rider_list.addItem(item)

    def assign(self):
        current_item = self.rider_list.currentItem()
        if not current_item:
            return
        rider = current_item.data(Qt.ItemDataRole.UserRole)
        assign_rider_to_order(str(self.order['_id']), str(rider['_id']), rider['name'])
        self.accept()


def _v_line():
    f = QFrame(); f.setFrameShape(QFrame.Shape.VLine)
    f.setFixedWidth(1); f.setStyleSheet(f"background:{_BORDER}; border:none;")
    return f


# ─────────────────────────────────────────────────────────────────────────────
#  DELIVERY PAGE  — fully redesigned
# ─────────────────────────────────────────────────────────────────────────────
class DeliveryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(DEL_STYLE)
        self.setObjectName("DeliveryPage")
        self._init_ui()
        self.load_data()

    # ── UI BUILD ──────────────────────────────────────────────────────────────
    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_stats_bar())
        root.addWidget(self._build_board(), stretch=1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data)
        self.timer.start(15000)

    # ── HEADER ────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = QFrame()
        hdr.setFixedHeight(70)
        hdr.setStyleSheet(
            f"QFrame {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {_DARK1},stop:0.6 {_DARK2},stop:1 {_DARK3});"
            f" border:none; }}"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(24, 0, 20, 0); hl.setSpacing(14)

        # Icon
        ico = QLabel()
        ico.setFixedSize(42, 42)
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico.setPixmap(qta.icon('fa5s.motorcycle', color=_PRIMARY).pixmap(22, 22))
        ico.setStyleSheet(f"background:{_PRIMARY}22; border-radius:10px; border:none;")

        # Title block
        tc = QVBoxLayout(); tc.setSpacing(2)
        title = QLabel("Delivery Management")
        title.setStyleSheet("color:white; font-size:20px; font-weight:900; letter-spacing:-0.3px; border:none; background:transparent;")
        sub = QLabel("Assign riders · Track orders · Manage deliveries")
        sub.setStyleSheet(f"color:rgba(255,255,255,0.55); font-size:11px; font-weight:500; border:none; background:transparent;")
        tc.addWidget(title); tc.addWidget(sub)

        # Refresh
        self._refresh_lbl = QLabel("")
        self._refresh_lbl.setStyleSheet(f"color:rgba(255,255,255,0.4); font-size:10px; font-weight:600; border:none; background:transparent;")

        btn_refresh = QPushButton("  Refresh")
        btn_refresh.setIcon(qta.icon('fa5s.sync-alt', color='white'))
        btn_refresh.setFixedHeight(36); btn_refresh.setFixedWidth(110)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(
            f"QPushButton {{ background:rgba(255,255,255,0.12); color:white; border:1px solid rgba(255,255,255,0.2);"
            f" border-radius:8px; font-size:12px; font-weight:700; padding:0 12px; }}"
            f"QPushButton:hover {{ background:rgba(255,255,255,0.2); }}"
        )
        btn_refresh.clicked.connect(self.load_data)

        hl.addWidget(ico)
        hl.addLayout(tc)
        hl.addStretch()
        hl.addWidget(self._refresh_lbl)
        hl.addSpacing(8)
        hl.addWidget(btn_refresh)
        return hdr

    # ── STATS BAR ─────────────────────────────────────────────────────────────
    def _build_stats_bar(self):
        bar = QFrame()
        bar.setFixedHeight(96)
        bar.setStyleSheet(f"QFrame {{ background:{_DARK2}; border:none; }}")
        row = QHBoxLayout(bar)
        row.setContentsMargins(20, 12, 20, 12)
        row.setSpacing(1)

        configs = [
            ('stat_pending',   'PENDING',     'fa5s.clock',         _WARNING_BR, '#78350F'),
            ('stat_assigned',  'ASSIGNED',    'fa5s.user-check',    _PRIMARY,    '#312E81'),
            ('stat_out',       'OUT FOR DEL', 'fa5s.motorcycle',    _INFO_BR,    '#075985'),
            ('stat_delivered', 'DELIVERED',   'fa5s.check-circle',  _SUCCESS_MD, '#064E3B'),
        ]

        for i, (attr, label_text, icon_name, color, dark) in enumerate(configs):
            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background:rgba(255,255,255,0.06); border-radius:12px; border:none; }}"
            )
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            cl = QHBoxLayout(card); cl.setContentsMargins(16, 10, 16, 10); cl.setSpacing(12)

            ico_w = QLabel()
            ico_w.setFixedSize(38, 38)
            ico_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ico_w.setPixmap(qta.icon(icon_name, color=color).pixmap(18, 18))
            ico_w.setStyleSheet(f"background:{color}22; border-radius:9px; border:none;")

            right = QVBoxLayout(); right.setSpacing(0)
            val = QLabel("0")
            val.setStyleSheet(
                f"font-size:26px; font-weight:900; color:white;"
                f" letter-spacing:-1px; border:none; background:transparent;"
            )
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"font-size:9px; font-weight:800; color:{color}; letter-spacing:0.8px; border:none; background:transparent;")
            right.addWidget(val); right.addWidget(lbl)

            cl.addWidget(ico_w); cl.addLayout(right); cl.addStretch()
            setattr(self, attr, val)

            row.addWidget(card)
            if i < len(configs) - 1:
                sep = QFrame(); sep.setFixedWidth(1); sep.setStyleSheet(f"background:rgba(255,255,255,0.08); border:none;")
                row.addWidget(sep)

        return bar

    # ── KANBAN BOARD ──────────────────────────────────────────────────────────
    def _build_board(self):
        board = QFrame()
        board.setStyleSheet(f"QFrame {{ background:{_BG}; border:none; }}")
        bl = QHBoxLayout(board)
        bl.setContentsMargins(16, 16, 16, 16)
        bl.setSpacing(14)

        # Column configs: (title, color, icon, attr)
        cols = [
            ("Pending / Unassigned", _WARNING_BR, "fa5s.clock",        "col_pending"),
            ("Out for Delivery",     _INFO_BR,    "fa5s.motorcycle",   "col_out"),
            ("Delivered Today",      _SUCCESS_MD, "fa5s.check-circle", "col_delivered"),
        ]
        for title, color, icon_name, attr in cols:
            col = self._create_column(title, color, icon_name)
            setattr(self, attr, col)
            bl.addWidget(col)

        return board

    def _create_column(self, title, color, icon_name):
        container = QFrame()
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        container.setStyleSheet(
            f"QFrame#col {{ background:{_SURFACE}; border-radius:16px; border:1px solid {_BORDER}; }}"
        )
        container.setObjectName("col")
        vl = QVBoxLayout(container); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        # Column header
        col_hdr = QFrame()
        col_hdr.setFixedHeight(54)
        col_hdr.setStyleSheet(
            f"QFrame {{ background:{color}; border-radius:15px 15px 0 0; border:none; }}"
        )
        hl = QHBoxLayout(col_hdr); hl.setContentsMargins(16, 0, 16, 0); hl.setSpacing(10)

        ico_lbl = QLabel()
        ico_lbl.setPixmap(qta.icon(icon_name, color='white').pixmap(18, 18))
        ico_lbl.setStyleSheet("border:none; background:transparent;")

        col_title = QLabel(title)
        col_title.setStyleSheet(
            "color:white; font-size:13px; font-weight:800; letter-spacing:0.2px; border:none; background:transparent;"
        )

        count_lbl = QLabel("0")
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count_lbl.setFixedSize(28, 28)
        count_lbl.setStyleSheet(
            "background:rgba(255,255,255,0.25); color:white; font-size:13px; font-weight:900;"
            " border-radius:14px; border:none;"
        )

        hl.addWidget(ico_lbl); hl.addWidget(col_title); hl.addStretch(); hl.addWidget(count_lbl)
        vl.addWidget(col_hdr)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent; border:none;")

        content = QWidget()
        content.setStyleSheet(f"background:{_BG};")
        cl = QVBoxLayout(content)
        cl.setSpacing(10)
        cl.setContentsMargins(10, 10, 10, 10)
        cl.addStretch()
        scroll.setWidget(content)
        vl.addWidget(scroll)

        container.item_layout = cl
        container.count_label = count_lbl
        container.accent_color = color
        return container

    # ── LOAD DATA ─────────────────────────────────────────────────────────────
    def load_data(self):
        for col in [self.col_pending, self.col_out, self.col_delivered]:
            lyt = col.item_layout
            while lyt.count() > 1:
                item = lyt.takeAt(0)
                if item.widget(): item.widget().deleteLater()

        orders = get_delivery_orders()
        today = datetime.now().date()
        counts = {"pending": 0, "assigned": 0, "out": 0, "delivered": 0}

        for order in orders:
            status = order.get('delivery_status', 'Pending')

            if status in ['Delivered', 'Cancelled']:
                completed_at = order.get('completed_at') or order.get('updated_at')
                if not completed_at: continue
                if isinstance(completed_at, str):
                    try: completed_at = datetime.fromisoformat(completed_at)
                    except: pass
                if isinstance(completed_at, datetime):
                    if completed_at.date() != today: continue

            card = self._create_order_card(order)

            if status in ('Pending', 'Assigned') or not status:
                self.col_pending.item_layout.insertWidget(
                    self.col_pending.item_layout.count() - 1, card
                )
                if status == 'Assigned': counts["assigned"] += 1
                else: counts["pending"] += 1
            elif status == 'Out for Delivery':
                self.col_out.item_layout.insertWidget(
                    self.col_out.item_layout.count() - 1, card
                )
                counts["out"] += 1
            elif status == 'Delivered':
                self.col_delivered.item_layout.insertWidget(
                    self.col_delivered.item_layout.count() - 1, card
                )
                counts["delivered"] += 1

        total_pending = counts["pending"] + counts["assigned"]
        self.stat_pending.setText(str(total_pending))
        self.stat_assigned.setText(str(counts["assigned"]))
        self.stat_out.setText(str(counts["out"]))
        self.stat_delivered.setText(str(counts["delivered"]))
        self.col_pending.count_label.setText(str(total_pending))
        self.col_out.count_label.setText(str(counts["out"]))
        self.col_delivered.count_label.setText(str(counts["delivered"]))

        now_str = datetime.now().strftime("%I:%M %p")
        self._refresh_lbl.setText(f"Updated {now_str}")

    # ── ORDER CARD — complete redesign ────────────────────────────────────────
    def _create_order_card(self, order):
        status = order.get('delivery_status', 'Pending')

        accent = {
            'Pending':          _WARNING_BR,
            'Assigned':         _PRIMARY,
            'Out for Delivery': _INFO_BR,
            'Delivered':        _SUCCESS_MD,
            'Cancelled':        _TEXT_HINT,
        }.get(status, _BORDER)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame#orderCard {{ background:{_SURFACE}; border-radius:14px;"
            f" border:1px solid {_BORDER}; }}"
            f"QFrame#orderCard:hover {{ border-color:{accent}60; }}"
        )
        card.setObjectName("orderCard")
        vl = QVBoxLayout(card); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        # ── Colored top stripe ───────────────────────────────────────────
        stripe = QFrame()
        stripe.setFixedHeight(4)
        stripe.setStyleSheet(f"background:{accent}; border-radius:14px 14px 0 0; border:none;")
        vl.addWidget(stripe)

        # ── Card body ────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(body); bl.setContentsMargins(14, 12, 14, 12); bl.setSpacing(9)

        # Row 1: Invoice + Amount
        top_row = QHBoxLayout(); top_row.setSpacing(6)

        inv_lbl = QLabel(f"#{order.get('invoice_no', '—')}")
        inv_lbl.setStyleSheet(
            f"font-size:14px; font-weight:900; color:{_TEXT_PRI}; letter-spacing:-0.3px;"
            f" border:none; background:transparent;"
        )

        ts = order.get('created_at')
        time_str = ""
        if ts:
            try:
                if isinstance(ts, str): ts = datetime.fromisoformat(ts)
                time_str = ts.strftime("%I:%M %p")
            except: pass

        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet(f"font-size:10px; color:{_TEXT_HINT}; border:none; background:transparent;")

        amt_lbl = QLabel(f"Rs {order.get('grand_total', 0):,.0f}")
        amt_lbl.setStyleSheet(
            f"font-size:15px; font-weight:900; color:{_SUCCESS_MD};"
            f" border:none; background:transparent;"
        )
        top_row.addWidget(inv_lbl); top_row.addWidget(time_lbl); top_row.addStretch(); top_row.addWidget(amt_lbl)
        bl.addLayout(top_row)

        # ── Thin divider ─────────────────────────────────────────────────
        bl.addWidget(_divider())

        # Row 2: Customer info
        cust_row = QHBoxLayout(); cust_row.setSpacing(10)

        avatar = QLabel(order.get('customer_name', '?')[0].upper())
        avatar.setFixedSize(34, 34)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            f"background:{accent}22; color:{accent}; font-size:15px; font-weight:900;"
            f" border-radius:17px; border:none;"
        )

        cust_col = QVBoxLayout(); cust_col.setSpacing(1)
        name_lbl = QLabel(order.get('customer_name', 'Unknown'))
        name_lbl.setStyleSheet(
            f"font-size:13px; font-weight:800; color:{_TEXT_PRI}; border:none; background:transparent;"
        )
        cust_col.addWidget(name_lbl)
        phone = order.get('customer_phone', '')
        if phone:
            phone_lbl = QLabel(f"📞 {phone}")
            phone_lbl.setStyleSheet(f"font-size:10px; color:{_TEXT_SEC}; border:none; background:transparent;")
            cust_col.addWidget(phone_lbl)

        cust_row.addWidget(avatar); cust_row.addLayout(cust_col); cust_row.addStretch()

        # Status badge on right
        status_styles = {
            'Pending':          (_WARNING_LT, _WARNING),
            'Assigned':         (_PRIMARY_LT, _PRIMARY),
            'Out for Delivery': (_INFO_LT,    _INFO_BR),
            'Delivered':        (_SUCCESS_LT, _SUCCESS_MD),
            'Cancelled':        ("#F1F5F9",   _TEXT_HINT),
        }
        sbg, sfg = status_styles.get(status, (_BG, _TEXT_HINT))
        s_lbl = QLabel(status)
        s_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s_lbl.setStyleSheet(
            f"background:{sbg}; color:{sfg}; font-size:10px; font-weight:800;"
            f" padding:3px 10px; border-radius:6px; border:none; letter-spacing:0.4px;"
        )
        cust_row.addWidget(s_lbl)
        bl.addLayout(cust_row)

        # Row 3: Address
        addr = order.get('delivery_address', 'No address')
        addr_lbl = QLabel(f"📍  {addr}")
        addr_lbl.setWordWrap(True)
        addr_lbl.setStyleSheet(
            f"font-size:11px; font-weight:600; color:{_TEXT_SEC};"
            f" background:{_BG}; padding:7px 10px; border-radius:8px; border:none;"
        )
        bl.addWidget(addr_lbl)

        # Row 4: Rider + Timer
        bottom_row = QHBoxLayout(); bottom_row.setSpacing(8)

        rider_name = order.get('rider_name')
        if rider_name:
            rider_lbl = QLabel(f"🏍  {rider_name}")
            rider_lbl.setStyleSheet(
                f"font-size:11px; font-weight:800; color:{_PRIMARY};"
                f" background:{_PRIMARY_LT}; padding:4px 12px; border-radius:8px; border:none;"
            )
        else:
            rider_lbl = QLabel("🏍  Unassigned")
            rider_lbl.setStyleSheet(
                f"font-size:11px; font-weight:600; color:{_TEXT_HINT};"
                f" background:#F1F5F9; padding:4px 12px; border-radius:8px; border:none;"
            )
        bottom_row.addWidget(rider_lbl)
        bottom_row.addStretch()

        # Elapsed timer — shows for active orders
        assigned_at = order.get('assigned_at')
        created_at  = order.get('created_at')
        if status in ('Assigned', 'Out for Delivery') and (assigned_at or created_at):
            ref_time = assigned_at or created_at
            elapsed  = _elapsed_text(ref_time)
            ecolor   = _elapsed_color(ref_time)
            if elapsed:
                timer_lbl = QLabel(f"⏱  {elapsed}")
                timer_lbl.setStyleSheet(
                    f"font-size:10px; font-weight:800; color:{ecolor};"
                    f" background:{ecolor}18; padding:4px 10px; border-radius:8px; border:none;"
                )
                bottom_row.addWidget(timer_lbl)

        bl.addLayout(bottom_row)

        # ── Action buttons ───────────────────────────────────────────────
        if status != 'Delivered' and status != 'Cancelled':
            bl.addWidget(_divider())
            btn_row = QHBoxLayout(); btn_row.setSpacing(8)

            if status == 'Pending' or not status:
                btn = _pill_btn("Assign Rider", "fa5s.user-plus", accent, _PRIMARY_DK, height=34)
                btn.clicked.connect(lambda ch, o=order: self.assign_rider(o))
                btn_row.addWidget(btn)

            elif status == 'Assigned':
                btn_out = _pill_btn("Start Delivery", "fa5s.motorcycle", _INFO_BR, _INFO, height=34)
                btn_out.clicked.connect(lambda ch, oid=str(order['_id']): self.update_status(oid, "Out for Delivery"))
                btn_re = _ghost_pill("Reassign", "fa5s.exchange-alt", _TEXT_SEC, _BG, height=34)
                btn_re.clicked.connect(lambda ch, o=order: self.assign_rider(o))
                btn_row.addWidget(btn_out); btn_row.addWidget(btn_re)

            elif status == 'Out for Delivery':
                btn_done = _pill_btn("Mark Delivered", "fa5s.check-circle", _SUCCESS_MD, _SUCCESS, height=34)
                btn_done.clicked.connect(lambda ch, oid=str(order['_id']): self.update_status(oid, "Delivered"))
                btn_fail = _ghost_pill("Cancel", "fa5s.times", _DANGER, _DANGER_LT, height=34)
                btn_fail.clicked.connect(lambda ch, oid=str(order['_id']): self.update_status(oid, "Cancelled"))
                btn_row.addWidget(btn_done); btn_row.addWidget(btn_fail)

            bl.addLayout(btn_row)

        vl.addWidget(body)
        return card

    # ── ACTIONS (original logic) ───────────────────────────────────────────────
    def assign_rider(self, order):
        dlg = AssignRiderDialog(order, self)
        if dlg.exec():
            self.load_data()

    def update_status(self, order_id, status):
        if status == "Cancelled":
            if QMessageBox.question(
                self, "Confirm", "Cancel this delivery?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
        update_delivery_status(order_id, status)
        self.load_data()
