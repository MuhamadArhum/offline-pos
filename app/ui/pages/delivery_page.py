from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QPushButton, QScrollArea, QGridLayout,
                             QComboBox, QMessageBox, QDialog, QListWidget, QListWidgetItem,
                             QSizePolicy, QAbstractItemView)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QColor, QFont, QPixmap
import qtawesome as qta
from datetime import datetime
from app.services.rider_service import get_riders, assign_rider_to_order, update_delivery_status, get_delivery_orders
from app.ui.styles import Theme
from app.ui.shared_ui import GLOBAL_STYLE, C, page_header, make_ghost_btn

# ─────────────────────────────────────────────────────────────────────────────
#  DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────
_PRIMARY    = "#6366F1"
_PRIMARY_DK = "#4F46E5"
_PRIMARY_LT = "#EDE9FE"
_SUCCESS    = "#059669"
_SUCCESS_LT = "#D1FAE5"
_DANGER     = "#EF4444"
_DANGER_LT  = "#FEE2E2"
_WARNING    = "#F59E0B"
_WARNING_LT = "#FEF3C7"
_INFO       = "#0EA5E9"
_INFO_LT    = "#E0F2FE"
_DARK1      = "#0F172A"
_DARK2      = "#1E293B"
_TEXT_PRI   = "#1E293B"
_TEXT_SEC   = "#64748B"
_TEXT_HINT  = "#94A3B8"
_BG         = "#F8FAFC"
_SURFACE    = "#FFFFFF"
_BORDER     = "#E2E8F0"
_DIVIDER    = "#F1F5F9"

DEL_STYLE = f"""
* {{ font-family: 'Segoe UI', 'SF Pro Display', system-ui, sans-serif; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 5px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: #CBD5E1; border-radius: 3px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: #94A3B8; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QListWidget {{
    background: {_SURFACE}; border: 1.5px solid {_BORDER};
    border-radius: 10px; padding: 4px; outline: none;
}}
QListWidget::item {{
    border-radius: 8px; padding: 10px 14px; border: none;
    color: {_TEXT_PRI}; font-size: 13px; font-weight: 600;
}}
QListWidget::item:selected {{ background: {_PRIMARY_LT}; color: {_PRIMARY}; }}
QListWidget::item:hover:!selected {{ background: {_BG}; }}

QDialog {{ background: {_BG}; }}
QMessageBox {{ background: {_SURFACE}; }}
QMessageBox QPushButton {{
    background: {_PRIMARY}; color: white; border: none; border-radius: 8px;
    padding: 6px 20px; font-weight: 700; min-width: 80px;
}}
QMessageBox QPushButton:hover {{ background: {_PRIMARY_DK}; }}
QToolTip {{
    background: {_DARK2}; color: white; border: none;
    border-radius: 6px; padding: 5px 10px; font-size: 11px;
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS  (same logic, improved styling)
# ─────────────────────────────────────────────────────────────────────────────
def _divider():
    f = QFrame(); f.setFrameShape(QFrame.Shape.HLine); f.setFixedHeight(1)
    f.setStyleSheet(f"background:{_BORDER}; border:none;")
    return f

def _badge(text, bg, fg="white", radius=8):
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(
        f"background:{bg}; color:{fg}; font-size:10px; font-weight:800;"
        f" padding:3px 10px; border-radius:{radius}px; border:none; letter-spacing:0.3px;"
    )
    return lbl

def _action_btn(text, icon_name, bg, hover_bg, fg="white", height=36):
    btn = QPushButton(f"  {text}")
    btn.setIcon(qta.icon(icon_name, color=fg))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
    btn.setStyleSheet(
        f"QPushButton {{ background:{bg}; color:{fg}; border:none; border-radius:8px;"
        f" font-size:12px; font-weight:700; padding:0 14px; }}"
        f"QPushButton:hover {{ background:{hover_bg}; }}"
    )
    return btn

def _flat_btn(text, color, hover_bg, height=30):
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
    btn.setStyleSheet(
        f"QPushButton {{ background:transparent; color:{color}; border:1.5px solid {color};"
        f" border-radius:7px; font-size:11px; font-weight:700; padding:0 12px; }}"
        f"QPushButton:hover {{ background:{hover_bg}; }}"
    )
    return btn

def _field_lbl(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size:10px; font-weight:800; color:{_TEXT_HINT}; letter-spacing:0.5px;"
        f" border:none; background:transparent;"
    )
    return lbl


# ─────────────────────────────────────────────────────────────────────────────
#  ASSIGN RIDER DIALOG  — original logic, improved UI
# ─────────────────────────────────────────────────────────────────────────────
class AssignRiderDialog(QDialog):
    def __init__(self, order, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Rider")
        self.setFixedSize(440, 470)
        self.setStyleSheet(DEL_STYLE)
        self.order = order
        self.selected_rider = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Dark gradient header ───────────────────────────────────────────
        hdr = QFrame(); hdr.setFixedHeight(64)
        hdr.setStyleSheet(
            f"QFrame {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {_DARK1},stop:1 {_DARK2}); border:none; }}"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(24, 0, 24, 0); hl.setSpacing(12)
        ico = QLabel(); ico.setPixmap(qta.icon('fa5s.motorcycle', color=_PRIMARY).pixmap(28, 28))
        txt_col = QVBoxLayout(); txt_col.setSpacing(2)
        ttl = QLabel("Assign Rider")
        ttl.setStyleSheet("color:white; font-size:17px; font-weight:900; letter-spacing:-0.3px; border:none; background:transparent;")
        sub = QLabel(f"Order  #{order.get('invoice_no', '—')}")
        sub.setStyleSheet(f"color:{_TEXT_HINT}; font-size:11px; font-weight:600; border:none; background:transparent;")
        txt_col.addWidget(ttl); txt_col.addWidget(sub)
        hl.addWidget(ico); hl.addLayout(txt_col); hl.addStretch()
        layout.addWidget(hdr)

        # ── Body ──────────────────────────────────────────────────────────
        body = QWidget(); body.setStyleSheet(f"background:{_BG};")
        bl = QVBoxLayout(body); bl.setContentsMargins(22, 16, 22, 20); bl.setSpacing(12)

        # Order summary card
        order_card = QFrame()
        order_card.setStyleSheet(
            f"QFrame {{ background:{_SURFACE}; border-radius:12px; border:1.5px solid {_BORDER}; }}"
        )
        ol = QVBoxLayout(order_card); ol.setContentsMargins(16, 14, 16, 14); ol.setSpacing(10)

        # Top row: customer + amount
        top_row = QHBoxLayout()
        c1 = QVBoxLayout(); c1.setSpacing(2)
        c1.addWidget(_field_lbl("CUSTOMER"))
        cust_val = QLabel(str(order.get('customer_name', '—')))
        cust_val.setStyleSheet(f"font-size:14px; font-weight:800; color:{_TEXT_PRI}; border:none; background:transparent;")
        c1.addWidget(cust_val)

        c2 = QVBoxLayout(); c2.setSpacing(2)
        c2.addWidget(_field_lbl("AMOUNT"))
        amt_val = QLabel(f"Rs {order.get('grand_total', 0):,.0f}")
        amt_val.setStyleSheet(f"font-size:16px; font-weight:900; color:{_SUCCESS}; border:none; background:transparent;")
        c2.addWidget(amt_val)
        top_row.addLayout(c1); top_row.addStretch(); top_row.addLayout(c2)
        ol.addLayout(top_row)

        ol.addWidget(_divider())

        # Address
        ol.addWidget(_field_lbl("DELIVERY ADDRESS"))
        addr_lbl = QLabel(f"📍  {order.get('delivery_address', '—')}")
        addr_lbl.setWordWrap(True)
        addr_lbl.setStyleSheet(
            f"font-size:12px; font-weight:600; color:{_TEXT_SEC};"
            f" background:{_BG}; padding:8px 10px; border-radius:8px; border:none;"
        )
        ol.addWidget(addr_lbl)
        bl.addWidget(order_card)

        # Rider list header
        bl.addWidget(_field_lbl("SELECT A RIDER"))

        # Rider list
        self.rider_list = QListWidget()
        self.rider_list.setSpacing(3)
        self.rider_list.itemDoubleClicked.connect(self.assign)
        bl.addWidget(self.rider_list)

        layout.addWidget(body, stretch=1)

        # ── Footer ────────────────────────────────────────────────────────
        footer = QFrame()
        footer.setStyleSheet(f"QFrame {{ background:{_SURFACE}; border-top:1.5px solid {_BORDER}; }}")
        fl = QHBoxLayout(footer); fl.setContentsMargins(22, 14, 22, 14); fl.setSpacing(12)
        btn_cancel = QPushButton("Cancel"); btn_cancel.setFixedHeight(44); btn_cancel.setFixedWidth(100)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background:{_DIVIDER}; border:1.5px solid {_BORDER}; border-radius:10px;"
            f" color:{_TEXT_SEC}; font-weight:700; }}"
            f"QPushButton:hover {{ background:{_BORDER}; color:{_TEXT_PRI}; }}"
        )
        btn_cancel.clicked.connect(self.reject)
        btn_assign = QPushButton("  Assign Rider")
        btn_assign.setIcon(qta.icon('fa5s.check-circle', color='white'))
        btn_assign.setFixedHeight(44); btn_assign.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_assign.setStyleSheet(
            f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {_PRIMARY},stop:1 #818CF8); color:white; border:none; border-radius:10px;"
            f" font-size:13px; font-weight:800; padding:0 22px; }}"
            f"QPushButton:hover {{ background:{_PRIMARY_DK}; }}"
        )
        btn_assign.clicked.connect(self.assign)
        fl.addWidget(btn_cancel); fl.addStretch(); fl.addWidget(btn_assign)
        layout.addWidget(footer)

        self.load_riders()

    # ── original logic ─────────────────────────────────────────────────────
    def load_riders(self):
        riders = get_riders(active_only=True)
        for r in riders:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, r)
            vehicle = r.get('vehicle_no', 'N/A')
            item.setText(f"  🏍  {r['name']}  ·  {vehicle}")
            self.rider_list.addItem(item)

    def assign(self):
        current_item = self.rider_list.currentItem()
        if not current_item:
            return
        rider = current_item.data(Qt.ItemDataRole.UserRole)
        assign_rider_to_order(str(self.order['_id']), str(rider['_id']), rider['name'])
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  DELIVERY PAGE  — original logic, improved UI
# ─────────────────────────────────────────────────────────────────────────────
class DeliveryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(DEL_STYLE)
        self._init_ui()
        self.load_data()

    # ── UI BUILD ──────────────────────────────────────────────────────────────
    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())
        root.addWidget(self._build_stats_bar())
        root.addWidget(self._build_board())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data)
        self.timer.start(15000)

    # ── TOP BAR ───────────────────────────────────────────────────────────────
    def _build_top_bar(self):
        btn_refresh = make_ghost_btn(
            "  Refresh",
            icon=qta.icon('fa5s.sync-alt', color=C['text_sec']),
            height=36
        )
        btn_refresh.clicked.connect(self.load_data)
        return page_header(
            "Delivery Management",
            subtitle="Assign riders · Track deliveries · Manage status",
            right_widget=btn_refresh
        )

    # ── STATS BAR ─────────────────────────────────────────────────────────────
    def _build_stats_bar(self):
        bar = QFrame()
        bar.setFixedHeight(90)
        bar.setStyleSheet(f"QFrame {{ background:{_BG}; border:none; }}")
        row = QHBoxLayout(bar)
        row.setContentsMargins(20, 12, 20, 12)
        row.setSpacing(12)

        configs = [
            ('stat_pending',   'Pending',    'fa5s.clock',         _WARNING, _WARNING_LT),
            ('stat_assigned',  'Assigned',   'fa5s.user-check',    _PRIMARY, _PRIMARY_LT),
            ('stat_out',       'Out',        'fa5s.motorcycle',    _INFO,    _INFO_LT),
            ('stat_delivered', 'Delivered',  'fa5s.check-circle',  _SUCCESS, _SUCCESS_LT),
        ]

        for attr, label_text, icon_name, color, lt in configs:
            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background:{_SURFACE}; border-radius:12px;"
                f" border-left:4px solid {color}; border-top:1px solid {_BORDER};"
                f" border-right:1px solid {_BORDER}; border-bottom:1px solid {_BORDER}; }}"
            )
            cl = QHBoxLayout(card); cl.setContentsMargins(14, 8, 14, 8); cl.setSpacing(10)

            ico_wrap = QLabel(); ico_wrap.setFixedSize(40, 40)
            ico_wrap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ico_wrap.setPixmap(qta.icon(icon_name, color=color).pixmap(20, 20))
            ico_wrap.setStyleSheet(f"background:{lt}; border-radius:10px; border:none;")

            right = QVBoxLayout(); right.setSpacing(1)
            val = QLabel("0")
            val.setStyleSheet(
                f"font-size:24px; font-weight:900; color:{color};"
                f" letter-spacing:-1px; border:none; background:transparent;"
            )
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"font-size:10px; font-weight:700; color:{_TEXT_HINT}; letter-spacing:0.5px; border:none; background:transparent;")
            right.addWidget(val); right.addWidget(lbl)

            cl.addWidget(ico_wrap); cl.addLayout(right); cl.addStretch()
            setattr(self, attr, val)
            row.addWidget(card)

        row.addStretch()
        return bar

    # ── KANBAN BOARD ──────────────────────────────────────────────────────────
    def _build_board(self):
        board_frame = QFrame()
        board_frame.setStyleSheet(f"QFrame {{ background:{_BG}; border:none; }}")
        board_layout = QHBoxLayout(board_frame)
        board_layout.setContentsMargins(16, 12, 16, 16)
        board_layout.setSpacing(14)

        self.col_pending   = self._create_column("Pending / Unassigned", _WARNING, "fa5s.clock")
        self.col_out       = self._create_column("Out for Delivery",     _INFO,    "fa5s.motorcycle")
        self.col_delivered = self._create_column("Delivered  (Today)",   _SUCCESS, "fa5s.check-circle")

        board_layout.addWidget(self.col_pending)
        board_layout.addWidget(self.col_out)
        board_layout.addWidget(self.col_delivered)
        return board_frame

    def _create_column(self, title, color, icon_name):
        # Outer container
        container = QFrame()
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        container.setStyleSheet(
            f"QFrame {{ background:{_SURFACE}; border-radius:14px; border:1.5px solid {_BORDER}; }}"
        )
        layout = QVBoxLayout(container); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)

        # Column header
        header = QFrame(); header.setFixedHeight(50)
        header.setStyleSheet(
            f"QFrame {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {color}14,stop:1 {color}08);"
            f" border-radius:14px 14px 0 0;"
            f" border-bottom:2px solid {color}30;"
            f" border-top:none; border-left:none; border-right:none; }}"
        )
        hl = QHBoxLayout(header); hl.setContentsMargins(14, 0, 14, 0); hl.setSpacing(8)
        col_icon = QLabel(); col_icon.setPixmap(qta.icon(icon_name, color=color).pixmap(16, 16))
        col_title = QLabel(title)
        col_title.setStyleSheet(
            f"font-size:13px; font-weight:800; color:{color}; border:none; background:transparent;"
        )
        count_lbl = QLabel("0")
        count_lbl.setStyleSheet(
            f"background:{color}; color:white; font-size:11px; font-weight:900;"
            f" padding:2px 10px; border-radius:10px; border:none;"
        )
        hl.addWidget(col_icon); hl.addWidget(col_title); hl.addStretch(); hl.addWidget(count_lbl)
        layout.addWidget(header)

        # Scroll area for cards
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent; border:none;")
        content = QWidget(); content.setStyleSheet("background:transparent;")
        cl = QVBoxLayout(content); cl.setSpacing(10)
        cl.setContentsMargins(10, 10, 10, 10); cl.addStretch()
        scroll.setWidget(content); layout.addWidget(scroll)

        container.item_layout = cl
        container.count_label = count_lbl
        return container

    # ── LOAD DATA  (original logic) ───────────────────────────────────────────
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

        self.stat_pending.setText(str(counts["pending"] + counts["assigned"]))
        self.stat_assigned.setText(str(counts["assigned"]))
        self.stat_out.setText(str(counts["out"]))
        self.stat_delivered.setText(str(counts["delivered"]))
        self.col_pending.count_label.setText(str(counts["pending"] + counts["assigned"]))
        self.col_out.count_label.setText(str(counts["out"]))
        self.col_delivered.count_label.setText(str(counts["delivered"]))

    # ── ORDER CARD ────────────────────────────────────────────────────────────
    def _create_order_card(self, order):
        status = order.get('delivery_status', 'Pending')

        accent = {
            'Pending':          _WARNING,
            'Assigned':         _PRIMARY,
            'Out for Delivery': _INFO,
            'Delivered':        _SUCCESS,
        }.get(status, _BORDER)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background:{_SURFACE}; border-radius:12px;"
            f" border:1px solid {_BORDER}; border-left:4px solid {accent}; }}"
        )
        layout = QVBoxLayout(card); layout.setContentsMargins(14, 12, 14, 12); layout.setSpacing(8)

        # ── Invoice row ─────────────────────────────────────────────────────
        top = QHBoxLayout(); top.setSpacing(6)
        inv_lbl = QLabel(f"# {order.get('invoice_no', '—')}")
        inv_lbl.setStyleSheet(
            f"font-size:12px; font-weight:900; color:{_PRIMARY}; letter-spacing:0.3px;"
            f" border:none; background:transparent;"
        )
        time_str = ""
        ts = order.get('created_at')
        if ts:
            try:
                if isinstance(ts, str): ts = datetime.fromisoformat(ts)
                time_str = ts.strftime("%I:%M %p")
            except: pass
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet(f"font-size:11px; color:{_TEXT_HINT}; border:none; background:transparent;")
        amt_lbl = QLabel(f"Rs {order.get('grand_total', 0):,.0f}")
        amt_lbl.setStyleSheet(
            f"font-size:14px; font-weight:900; color:{_SUCCESS}; letter-spacing:-0.3px;"
            f" border:none; background:transparent;"
        )
        top.addWidget(inv_lbl); top.addWidget(time_lbl); top.addStretch(); top.addWidget(amt_lbl)
        layout.addLayout(top)

        layout.addWidget(_divider())

        # ── Customer block ───────────────────────────────────────────────────
        cust_name  = order.get('customer_name', 'Unknown')
        cust_phone = order.get('customer_phone', '')

        cust_row = QHBoxLayout(); cust_row.setSpacing(8)
        avatar = QLabel("👤")
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            f"background:{_PRIMARY_LT}; border-radius:16px; font-size:14px; border:none;"
        )
        cust_col = QVBoxLayout(); cust_col.setSpacing(1)
        name_lbl = QLabel(cust_name)
        name_lbl.setStyleSheet(
            f"font-size:13px; font-weight:800; color:{_TEXT_PRI}; border:none; background:transparent;"
        )
        cust_col.addWidget(name_lbl)
        if cust_phone:
            phone_lbl = QLabel(f"📞  {cust_phone}")
            phone_lbl.setStyleSheet(
                f"font-size:11px; color:{_TEXT_SEC}; border:none; background:transparent;"
            )
            cust_col.addWidget(phone_lbl)
        cust_row.addWidget(avatar); cust_row.addLayout(cust_col); cust_row.addStretch()
        layout.addLayout(cust_row)

        # ── Address ──────────────────────────────────────────────────────────
        addr = order.get('delivery_address', 'No Address')
        addr_lbl = QLabel(f"📍  {addr}")
        addr_lbl.setWordWrap(True)
        addr_lbl.setStyleSheet(
            f"font-size:11px; font-weight:600; color:{_TEXT_SEC};"
            f" background:{_BG}; padding:7px 10px; border-radius:8px; border:none;"
        )
        layout.addWidget(addr_lbl)

        # ── Rider chip ───────────────────────────────────────────────────────
        rider_name = order.get('rider_name', None)
        if rider_name:
            rider_lbl = QLabel(f"🏍  {rider_name}")
            rider_lbl.setStyleSheet(
                f"font-size:12px; font-weight:800; color:{_PRIMARY};"
                f" background:{_PRIMARY_LT}; padding:5px 12px; border-radius:8px; border:none;"
            )
        else:
            rider_lbl = QLabel("🏍  No Rider Assigned")
            rider_lbl.setStyleSheet(
                f"font-size:11px; font-weight:600; color:{_TEXT_HINT};"
                f" background:{_BG}; padding:5px 12px; border-radius:8px; border:none;"
            )
        layout.addWidget(rider_lbl)

        # ── Status badge ─────────────────────────────────────────────────────
        status_cfg = {
            'Pending':          (_WARNING_LT, _WARNING),
            'Assigned':         (_PRIMARY_LT, _PRIMARY),
            'Out for Delivery': (_INFO_LT,    _INFO),
            'Delivered':        (_SUCCESS_LT, _SUCCESS),
            'Cancelled':        (_DIVIDER,    _TEXT_HINT),
        }
        bg_c, fg_c = status_cfg.get(status, (_BG, _TEXT_SEC))
        layout.addWidget(_badge(status, bg_c, fg_c))

        layout.addWidget(_divider())

        # ── Action buttons (original logic unchanged) ─────────────────────
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)

        if status == 'Pending' or not status:
            btn_assign = _action_btn("Assign Rider", "fa5s.user-plus", _PRIMARY, _PRIMARY_DK, height=34)
            btn_assign.clicked.connect(lambda ch, o=order: self.assign_rider(o))
            btn_row.addWidget(btn_assign)

        elif status == 'Assigned':
            btn_out = _action_btn("Start Delivery", "fa5s.motorcycle", _INFO, "#0284C7", height=34)
            btn_out.clicked.connect(lambda ch, oid=str(order['_id']): self.update_status(oid, "Out for Delivery"))
            btn_row.addWidget(btn_out)
            btn_re = _flat_btn("Reassign", _TEXT_SEC, _BG, height=34)
            btn_re.clicked.connect(lambda ch, o=order: self.assign_rider(o))
            btn_row.addWidget(btn_re)

        elif status == 'Out for Delivery':
            btn_done = _action_btn("Mark Delivered", "fa5s.check-circle", _SUCCESS, "#047857", height=34)
            btn_done.clicked.connect(lambda ch, oid=str(order['_id']): self.update_status(oid, "Delivered"))
            btn_row.addWidget(btn_done)
            btn_fail = _flat_btn("Cancel", _DANGER, _DANGER_LT, height=34)
            btn_fail.clicked.connect(lambda ch, oid=str(order['_id']): self.update_status(oid, "Cancelled"))
            btn_row.addWidget(btn_fail)

        layout.addLayout(btn_row)
        return card

    # ── ORIGINAL LOGIC: ACTIONS ───────────────────────────────────────────────
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