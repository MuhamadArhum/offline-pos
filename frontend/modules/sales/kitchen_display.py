"""
Kitchen Display System (KDS) - A standalone window for kitchen staff.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QLabel, QPushButton, QScrollArea, QDialog,
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
import qtawesome as qta
from datetime import datetime

from backend.core.database import orders_col
from frontend.modules.sales.helpers import IMPROVED_STYLE


class OrderDetailDialog(QDialog):
    """Full order detail popup for KDS."""

    def __init__(self, order, parent=None):
        super().__init__(parent)
        self.order = order
        self.setWindowTitle("Order Details")
        self.setMinimumWidth(480)
        self.setStyleSheet(IMPROVED_STYLE + """
            QDialog { background: #0f172a; }
            QLabel  { color: #e2e8f0; }
            QFrame#detail-card { background: #1e293b; border-radius: 14px; border: 1px solid rgba(255,255,255,0.08); }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── Header Info ──────────────────────────────────────────────
        created  = order.get('created_at', datetime.now())
        elapsed  = int((datetime.now() - created).total_seconds() / 60)
        order_type = order.get('order_type', 'Dine In')

        if elapsed > 20:
            timer_color = "#ef4444"
        elif elapsed > 10:
            timer_color = "#f59e0b"
        else:
            timer_color = "#10b981"

        title_row = QHBoxLayout()
        tbl_lbl = QLabel(
            f"Table: <b>{order.get('table_no', order_type)}</b>"
        )
        tbl_lbl.setStyleSheet("font-size: 20px; font-weight: 900; color: white;")
        timer_lbl = QLabel(f"⏱ {elapsed} min")
        timer_lbl.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {timer_color};")
        title_row.addWidget(tbl_lbl)
        title_row.addStretch()
        title_row.addWidget(timer_lbl)
        layout.addLayout(title_row)

        # ── Order Meta ───────────────────────────────────────────────
        meta_card = QFrame()
        meta_card.setObjectName("detail-card")
        meta_layout = QVBoxLayout(meta_card)
        meta_layout.setContentsMargins(16, 14, 16, 14)
        meta_layout.setSpacing(6)

        def _meta_row(label, value, value_color="#e2e8f0"):
            r = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
            val = QLabel(str(value))
            val.setStyleSheet(f"color: {value_color}; font-size: 13px; font-weight: 700;")
            r.addWidget(lbl)
            r.addStretch()
            r.addWidget(val)
            return r

        if order.get('token_no'):
            meta_layout.addLayout(_meta_row("Token No:", order['token_no'], "#f59e0b"))
        if order.get('invoice_no'):
            meta_layout.addLayout(_meta_row("Invoice No:", order['invoice_no'], "#94a3b8"))
        meta_layout.addLayout(_meta_row("Order Type:", order_type))
        if order.get('waiter'):
            meta_layout.addLayout(_meta_row("Waiter:", order['waiter']))
        meta_layout.addLayout(_meta_row(
            "Order Time:",
            created.strftime('%H:%M  %d-%b-%Y') if isinstance(created, datetime) else str(created)
        ))
        k_status = order.get('kitchen_status', 'Pending')
        k_color  = "#10b981" if k_status == "Ready" else "#f59e0b"
        meta_layout.addLayout(_meta_row("Kitchen Status:", k_status, k_color))
        if order.get('note'):
            meta_layout.addLayout(_meta_row("Order Note:", order['note'], "#f59e0b"))

        layout.addWidget(meta_card)

        # ── Items ────────────────────────────────────────────────────
        items_title = QLabel("Items Ordered")
        items_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #94a3b8; letter-spacing: 0.5px;")
        layout.addWidget(items_title)

        items_card = QFrame()
        items_card.setObjectName("detail-card")
        items_layout = QVBoxLayout(items_card)
        items_layout.setContentsMargins(16, 12, 16, 12)
        items_layout.setSpacing(8)

        for i, item in enumerate(order.get('items', [])):
            row = QHBoxLayout()
            qty_lbl = QLabel(f"{item.get('qty', 0)}x")
            qty_lbl.setFixedWidth(30)
            qty_lbl.setStyleSheet("color: #f59e0b; font-weight: 900; font-size: 14px;")
            name_lbl = QLabel(item.get('name', ''))
            name_lbl.setStyleSheet("color: white; font-size: 13px;")
            name_lbl.setWordWrap(True)
            price_lbl = QLabel(f"Rs {item.get('price', 0):,.0f}")
            price_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
            row.addWidget(qty_lbl)
            row.addWidget(name_lbl, stretch=1)
            row.addWidget(price_lbl)
            items_layout.addLayout(row)
            if item.get('note'):
                note_lbl = QLabel(f"   → {item['note']}")
                note_lbl.setStyleSheet("color: #f59e0b; font-size: 11px; font-style: italic;")
                items_layout.addWidget(note_lbl)
            if i < len(order.get('items', [])) - 1:
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet("background: rgba(255,255,255,0.06); border: none;")
                items_layout.addWidget(sep)

        layout.addWidget(items_card)

        # ── Totals ───────────────────────────────────────────────────
        subtotal = order.get('subtotal', 0)
        grand    = order.get('grand_total', 0)
        if grand:
            tot_row = QHBoxLayout()
            tot_lbl = QLabel("Grand Total:")
            tot_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #94a3b8;")
            tot_val = QLabel(f"Rs {grand:,.2f}")
            tot_val.setStyleSheet("font-size: 18px; font-weight: 900; color: #10b981;")
            tot_row.addWidget(tot_lbl)
            tot_row.addStretch()
            tot_row.addWidget(tot_val)
            layout.addLayout(tot_row)

        # ── Actions ──────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_close = QPushButton("  Close")
        btn_close.setIcon(qta.icon('fa5s.times', color='#94a3b8'))
        btn_close.setFixedHeight(44)
        btn_close.setStyleSheet(
            "QPushButton { background: #334155; color: #e2e8f0; border-radius: 10px; "
            "font-size: 14px; font-weight: 700; padding: 0 20px; border: none; } "
            "QPushButton:hover { background: #475569; }"
        )
        btn_close.clicked.connect(self.reject)

        self.btn_ready = QPushButton("  MARK READY")
        self.btn_ready.setIcon(qta.icon('fa5s.check', color='white'))
        self.btn_ready.setFixedHeight(44)
        self.btn_ready.setStyleSheet(
            "QPushButton { background: #059669; color: white; border-radius: 10px; "
            "font-size: 14px; font-weight: 800; padding: 0 24px; border: none; } "
            "QPushButton:hover { background: #047857; }"
        )
        if order.get('kitchen_status') == 'Ready':
            self.btn_ready.setEnabled(False)
            self.btn_ready.setText("  Already Ready")

        btn_row.addWidget(btn_close)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_ready)
        layout.addLayout(btn_row)

        self.btn_ready.clicked.connect(self.accept)


class KitchenDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kitchen Display System")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)
        self.setProperty("class", "kitchen-display")
        self.setStyleSheet(IMPROVED_STYLE + "QWidget { background: #0f172a; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        lbl = QLabel("KITCHEN DISPLAY")
        lbl.setProperty("class", "kitchen-title")
        header.addWidget(lbl)
        header.addStretch()

        btn_refresh = QPushButton("  Refresh")
        btn_refresh.setIcon(qta.icon('fa5s.sync-alt', color='#f59e0b'))
        btn_refresh.setFixedHeight(38)
        btn_refresh.setProperty("class", "btn-kitchen-refresh")
        btn_refresh.clicked.connect(self.load_orders)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: transparent;")
        self.grid = QGridLayout()
        self.grid.setSpacing(16)
        container_widget = QWidget()
        container_widget.setStyleSheet("background: transparent;")
        container_widget.setLayout(self.grid)
        self.scroll.setWidget(container_widget)
        layout.addWidget(self.scroll)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_orders)
        self.timer.start(10000)
        self.load_orders()

    def load_orders(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        orders = list(orders_col.find(
            {"status": "Running", "kitchen_status": {"$ne": "Ready"}}
        ).sort("updated_at", 1))
        row, col = 0, 0
        for order in orders:
            self.grid.addWidget(self.create_order_card(order), row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1

    def create_order_card(self, order):
        card = QFrame()
        card.setFixedSize(268, 340)
        created = order.get('created_at', datetime.now())
        elapsed = (datetime.now() - created).total_seconds() / 60

        border_color = "#10b981"
        if elapsed > 20:
            border_color = "#ef4444"
        elif elapsed > 10:
            border_color = "#f59e0b"

        card.setProperty("class", "kitchen-card")
        card.setStyleSheet(
            f"QFrame {{ background: #1e293b; border-radius: 14px; border-left: 5px solid {border_color}; }}"
        )

        l = QVBoxLayout(card)
        l.setContentsMargins(14, 14, 14, 14)
        l.setSpacing(8)

        h = QHBoxLayout()
        tbl = QLabel(f"Table {order.get('table_no', 'N/A')}")
        tbl.setProperty("class", "kitchen-tbl")
        elapsed_lbl = QLabel(f"{int(elapsed)} min")
        elapsed_lbl.setProperty("class", "kitchen-timer")
        elapsed_lbl.setStyleSheet(f"color: {border_color}; font-weight: 800;")
        h.addWidget(tbl)
        h.addStretch()
        h.addWidget(elapsed_lbl)
        l.addLayout(h)

        inv_lbl = QLabel(order.get('invoice_no', ''))
        inv_lbl.setProperty("class", "kitchen-meta")
        l.addWidget(inv_lbl)

        if order.get('token_no'):
            tok = QLabel(f"Token: {order['token_no']}")
            tok.setProperty("class", "kitchen-token")
            l.addWidget(tok)

        waiter = QLabel(f"Waiter: {order.get('waiter', '')}")
        waiter.setProperty("class", "kitchen-meta")
        l.addWidget(waiter)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.08); border: none;")
        l.addWidget(sep)

        for item in order.get('items', []):
            row_lbl = QLabel(
                f"<b style='color:white;'>{item['qty']}x</b>  "
                f"<span style='color:rgba(255,255,255,0.85);'>{item['name']}</span>"
            )
            row_lbl.setWordWrap(True)
            if item.get('note'):
                row_lbl.setText(
                    row_lbl.text()
                    + f"<br><span style='color:#f59e0b; font-size:11px;'>  -> {item['note']}</span>"
                )
            l.addWidget(row_lbl)

        l.addStretch()

        btn_done = QPushButton("  MARK READY")
        btn_done.setFixedHeight(40)
        btn_done.setProperty("class", "btn-kitchen-ready")
        btn_done.clicked.connect(lambda c, oid=order['_id']: self.mark_ready(oid))
        l.addWidget(btn_done)

        # Clicking anywhere on the card (except the button) opens detail dialog
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mousePressEvent = lambda e, o=order: self.open_detail(o)

        return card

    def open_detail(self, order):
        # Re-fetch order to get latest state
        fresh = orders_col.find_one({"_id": order["_id"]}) or order
        dlg = OrderDetailDialog(fresh, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.mark_ready(fresh["_id"])

    def mark_ready(self, order_id):
        orders_col.update_one(
            {"_id": order_id},
            {"$set": {"kitchen_status": "Ready", "updated_at": datetime.now(), "waiter_notified": False}},
        )
        self.load_orders()
