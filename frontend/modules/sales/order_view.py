"""
Order / Billing view for the Sales module.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QLabel, QPushButton, QLineEdit, QComboBox,
    QScrollArea, QTableWidget, QHeaderView, QDoubleSpinBox,
    QAbstractItemView, QTableWidgetItem, QMessageBox,
    QInputDialog, QDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPixmap
import qtawesome as qta
import os
import threading
from datetime import datetime

from backend.core.config import get_setting
from backend.core.database import orders_col
from backend.services.menu_service import get_menu
from backend.services.inventory_service import deduct_stock
from backend.services.recipe_service import get_recipe
from backend.services.table_service import set_table_status, get_all_tables
from backend.services.shift_service import get_active_shift, update_shift_totals
from backend.services.customer_service import (
    get_customer_by_phone, create_or_update_customer,
    add_loyalty_points, deduct_loyalty_points, log_customer_order,
)
from backend.services.whatsapp_service import send_receipt_via_whatsapp
from backend.utils.print_utils import print_receipt, print_kot

from frontend.modules.sales.helpers import (
    IMPROVED_STYLE, _badge,
    generate_invoice_no, generate_token_no,
)
from frontend.dialogs.sales_dialogs import (
    PaymentDialog, SplitBillDialog, ItemSplitDialog, NoteDialog, BillTypeDialog,
)


class OrderView(QWidget):
    def __init__(self, parent_page):
        super().__init__()
        self.parent_page = parent_page
        self.table_no = None
        self.order_type = "Dine In"
        self.current_order_id = None
        self.cart_items = {}
        self.current_category = "All"
        self.discount_percent = 0.0
        self.service_percent  = 0.0
        self.current_customer = None
        self.redeemed_points  = 0
        self._payment_in_progress = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -- LEFT: Menu Panel ------------------------------------------------
        left_panel = QWidget()
        left_panel.setStyleSheet("background: #f8fafc;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 12, 10, 12)
        left_layout.setSpacing(10)

        # Top bar
        top_bar_frame = QFrame()
        top_bar_frame.setMinimumHeight(42)
        top_bar_frame.setMaximumHeight(52)
        top_bar_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1.5px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        top_bar = QHBoxLayout(top_bar_frame)
        top_bar.setContentsMargins(12, 6, 12, 6)
        top_bar.setSpacing(10)

        logo_path = get_setting("logo_path", "app/resources/POS.png")
        if logo_path and os.path.exists(logo_path):
            logo_lbl = QLabel()
            try:
                pixmap = QPixmap(logo_path)
                logo_lbl.setPixmap(pixmap.scaled(
                    34, 34,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
                top_bar.addWidget(logo_lbl)
            except Exception:
                pass

        btn_back = QPushButton("  Tables")
        btn_back.setIcon(qta.icon('fa5s.arrow-left', color='#475569'))
        btn_back.setMinimumHeight(28)
        btn_back.setMaximumHeight(36)
        btn_back.setProperty("class", "btn-back")
        btn_back.clicked.connect(self.go_back)
        top_bar.addWidget(btn_back)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search menu items...")
        self.search_input.setMinimumHeight(28)
        self.search_input.setMaximumHeight(36)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: #f1f5f9;
                border: 1.5px solid #e2e8f0;
                border-radius: 9px;
                padding: 0 14px;
                color: #1e293b;
                font-size: 13px;
            }
            QLineEdit:focus {
                background: white;
                border-color: #059669;
            }
            QLineEdit::placeholder { color: #94a3b8; }
        """)
        self.search_input.textChanged.connect(self.filter_menu)
        top_bar.addWidget(self.search_input)
        left_layout.addWidget(top_bar_frame)

        # Category scroll
        self.cat_scroll = QScrollArea()
        self.cat_scroll.setMinimumHeight(36)
        self.cat_scroll.setMaximumHeight(44)
        self.cat_scroll.setWidgetResizable(True)
        self.cat_scroll.setStyleSheet("border: none; background: transparent;")
        self.cat_container = QWidget()
        self.cat_container.setStyleSheet("background: transparent;")
        self.cat_layout = QHBoxLayout(self.cat_container)
        self.cat_layout.setContentsMargins(0, 2, 0, 2)
        self.cat_layout.setSpacing(8)
        self.cat_scroll.setWidget(self.cat_container)
        left_layout.addWidget(self.cat_scroll)

        # Menu grid
        self.menu_scroll = QScrollArea()
        self.menu_scroll.setWidgetResizable(True)
        self.menu_scroll.setStyleSheet("border: none; background: #f8fafc;")
        self.menu_grid_widget = QWidget()
        self.menu_grid_widget.setStyleSheet("background: #f8fafc;")
        self.menu_grid_layout = QGridLayout(self.menu_grid_widget)
        self.menu_grid_layout.setSpacing(12)
        self.menu_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.menu_scroll.setWidget(self.menu_grid_widget)
        left_layout.addWidget(self.menu_scroll)

        layout.addWidget(left_panel, stretch=6)

        # -- RIGHT: Billing Panel -------------------------------------------
        right_panel = QWidget()
        right_panel.setMinimumWidth(420)
        right_panel.setMaximumWidth(580)
        right_panel.setStyleSheet("background: #f8fafc; border-left: 2px solid #e2e8f0;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        # Info bar
        self.info_label = QLabel("Dine In | Table: -- | Staff: --")
        self.info_label.setProperty("class", "info-label")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.info_label)

        # CRM Card
        crm_card = QFrame()
        crm_card.setProperty("class", "crm-card")
        crm_layout = QVBoxLayout(crm_card)
        crm_layout.setContentsMargins(10, 8, 10, 8)
        crm_layout.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.combo_order_type = QComboBox()
        self.combo_order_type.addItems(["Dine In", "Takeaway", "Delivery"])
        self.combo_order_type.setMinimumHeight(24)
        self.combo_order_type.setMaximumHeight(30)
        self.combo_order_type.currentTextChanged.connect(self.on_order_type_change)

        self.cust_phone_input = QLineEdit()
        self.cust_phone_input.setPlaceholderText("Phone...")
        self.cust_phone_input.setMinimumHeight(24)
        self.cust_phone_input.setMaximumHeight(30)
        self.cust_phone_input.returnPressed.connect(self.search_customer)

        row1.addWidget(self.combo_order_type, stretch=3)
        row1.addWidget(self.cust_phone_input, stretch=4)
        crm_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self.cust_name_input = QLineEdit()
        self.cust_name_input.setPlaceholderText("Customer Name")
        self.cust_name_input.setMinimumHeight(24)
        self.cust_name_input.setMaximumHeight(30)

        self.lbl_points = QLabel("0 pts")
        self.lbl_points.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: 800; white-space: nowrap;")

        self.btn_redeem = QPushButton("Redeem")
        self.btn_redeem.setMinimumHeight(22)
        self.btn_redeem.setMaximumHeight(26)
        self.btn_redeem.setMinimumWidth(50)
        self.btn_redeem.setMaximumWidth(68)
        self.btn_redeem.setStyleSheet("""
            QPushButton {
                background: #f59e0b; color: #1e293b; border: none;
                border-radius: 5px; font-weight: 800; font-size: 10px;
            }
            QPushButton:hover { background: #d97706; color: white; }
        """)
        self.btn_redeem.clicked.connect(self.redeem_points)
        self.btn_redeem.hide()

        row2.addWidget(self.cust_name_input, stretch=5)
        row2.addWidget(self.lbl_points)
        row2.addWidget(self.btn_redeem)
        crm_layout.addLayout(row2)

        self.address_container = QWidget()
        addr_l = QVBoxLayout(self.address_container)
        addr_l.setContentsMargins(0, 0, 0, 0)
        self.cust_address_input = QLineEdit()
        self.cust_address_input.setPlaceholderText("Delivery Address")
        self.cust_address_input.setFixedHeight(30)
        addr_l.addWidget(self.cust_address_input)
        crm_layout.addWidget(self.address_container)

        right_layout.addWidget(crm_card)

        # Cart table
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHorizontalHeaderLabels(["Item", "Price", "Qty", "Total", ""])
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cart_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.cart_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.cart_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.cart_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.cart_table.setColumnWidth(1, 72)
        self.cart_table.setColumnWidth(2, 108)
        self.cart_table.setColumnWidth(3, 80)
        self.cart_table.setColumnWidth(4, 70)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cart_table.setShowGrid(False)
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.cart_table.setProperty("class", "cart-table")
        self.cart_table.setStyleSheet("""
            QTableWidget {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 12px 16px;
                border-bottom: 1px solid #F1F5F9;
            }
            QTableWidget::item:selected {
                background: #ECFDF5;
                color: #059669;
            }
            QHeaderView::section {
                background: #F8FAFC;
                color: #64748B;
                font-size: 11px;
                font-weight: 700;
                padding: 12px 16px;
                border: none;
                border-bottom: 2px solid #E2E8F0;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
        """)
        right_layout.addWidget(self.cart_table)

        # Totals card
        totals_card = QFrame()
        totals_card.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1.5px solid #E2E8F0; border-radius:14px; }"
        )
        tf = QVBoxLayout(totals_card)
        tf.setContentsMargins(14, 10, 14, 10)
        tf.setSpacing(4)

        spin_style = """
            QDoubleSpinBox {
                border: 1.5px solid #E2E8F0; border-radius: 7px;
                padding: 2px 6px; background: #F8FAFC;
                font-size: 12px; font-weight: 700; color: #1E293B;
                max-height: 26px;
            }
            QDoubleSpinBox:focus { border: 2px solid #059669; background:#FFF; }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 16px; background: #E2E8F0; border-radius: 3px;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background: #059669;
            }
        """

        def _row(label, value_widget, label_color="#64748B"):
            row = QHBoxLayout()
            row.setSpacing(6)
            l = QLabel(label)
            l.setStyleSheet(f"color:{label_color}; font-size:11px; font-weight:700; background:transparent;")
            row.addWidget(l)
            row.addStretch()
            row.addWidget(value_widget)
            return row

        def _val_lbl(c="#475569"):
            l = QLabel("0.00")
            l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            l.setStyleSheet(f"color:{c}; font-size:12px; font-weight:700; background:transparent;")
            return l

        def _spin(mx=100, suffix="%"):
            s = QDoubleSpinBox()
            s.setRange(0, mx)
            s.setDecimals(0)
            s.setSuffix(suffix)
            s.setFixedWidth(80)
            s.setAlignment(Qt.AlignmentFlag.AlignRight)
            s.setStyleSheet(spin_style)
            return s

        self.lbl_subtotal     = _val_lbl()
        self.lbl_discount_amt = _val_lbl("#ef4444")
        self.lbl_service_amt  = _val_lbl("#f59e0b")
        self.lbl_tax          = _val_lbl("#0ea5e9")
        self.spin_discount    = _spin()
        self.spin_service     = _spin()
        self.spin_tax         = _spin()
        self.spin_delivery_amt = _spin(999999, " Rs")
        for sp in (self.spin_discount, self.spin_service, self.spin_tax, self.spin_delivery_amt):
            sp.valueChanged.connect(lambda _v: self.update_totals_ui())

        tf.addLayout(_row("Subtotal", self.lbl_subtotal))

        disc_row = QHBoxLayout(); disc_row.setSpacing(6)
        disc_lbl = QLabel("Discount"); disc_lbl.setStyleSheet("color:#ef4444; font-size:11px; font-weight:700; background:transparent;")
        disc_row.addWidget(disc_lbl)
        disc_row.addWidget(self.spin_discount)
        disc_row.addStretch()
        disc_row.addWidget(self.lbl_discount_amt)
        tf.addLayout(disc_row)

        svc_row = QHBoxLayout(); svc_row.setSpacing(6)
        svc_lbl = QLabel("Service Chg"); svc_lbl.setStyleSheet("color:#f59e0b; font-size:11px; font-weight:700; background:transparent;")
        svc_row.addWidget(svc_lbl)
        svc_row.addWidget(self.spin_service)
        svc_row.addStretch()
        svc_row.addWidget(self.lbl_service_amt)
        tf.addLayout(svc_row)

        tax_row = QHBoxLayout(); tax_row.setSpacing(6)
        tax_lbl = QLabel("Tax"); tax_lbl.setStyleSheet("color:#0ea5e9; font-size:11px; font-weight:700; background:transparent;")
        tax_row.addWidget(tax_lbl)
        tax_row.addWidget(self.spin_tax)
        tax_row.addStretch()
        tax_row.addWidget(self.lbl_tax)
        tf.addLayout(tax_row)

        del_row = QHBoxLayout(); del_row.setSpacing(6)
        del_lbl = QLabel("Delivery"); del_lbl.setStyleSheet("color:#8b5cf6; font-size:11px; font-weight:700; background:transparent;")
        del_row.addWidget(del_lbl)
        del_row.addStretch()
        del_row.addWidget(self.spin_delivery_amt)
        tf.addLayout(del_row)

        # Divider
        div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background:#E2E8F0; max-height:1px; border:none;")
        tf.addWidget(div)

        # Grand Total row
        total_row = QHBoxLayout()
        lbl_t = QLabel("GRAND TOTAL")
        lbl_t.setStyleSheet("color:#1E293B; font-size:12px; font-weight:900; letter-spacing:0.5px; background:transparent;")
        self.lbl_total = QLabel("Rs 0.00")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_total.setStyleSheet(
            "color:#059669; font-size:20px; font-weight:900; letter-spacing:-0.5px;"
            "background:#ECFDF5; padding:6px 14px; border-radius:9px;"
        )
        total_row.addWidget(lbl_t)
        total_row.addStretch()
        total_row.addWidget(self.lbl_total)
        tf.addLayout(total_row)

        right_layout.addWidget(totals_card)

        # Action buttons row
        act_row = QHBoxLayout()
        act_row.setSpacing(10)

        self.btn_kot = QPushButton("  KOT")
        self.btn_kot.setIcon(qta.icon("fa5s.paper-plane", color="white"))
        self.btn_kot.setFixedHeight(46)
        self.btn_kot.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_kot.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0ea5e9, stop:1 #38bdf8);
                color: white; border: none; border-radius: 10px;
                font-weight: 800; font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #0ea5e9);
            }
        """)

        self.btn_split = QPushButton("  Split")
        self.btn_split.setIcon(qta.icon("fa5s.cut", color="white"))
        self.btn_split.setFixedHeight(46)
        self.btn_split.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_split.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f97316, stop:1 #fb923c);
                color: white; border: none; border-radius: 10px;
                font-weight: 800; font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ea580c, stop:1 #f97316);
            }
        """)

        btn_transfer = QPushButton("  Transfer")
        btn_transfer.setIcon(qta.icon("fa5s.exchange-alt", color="white"))
        btn_transfer.setFixedHeight(46)
        btn_transfer.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_transfer.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #a78bfa);
                color: white; border: none; border-radius: 10px;
                font-weight: 800; font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6d28d9, stop:1 #7c3aed);
            }
        """)

        self.btn_payment = QPushButton("  PAY / CHARGE")
        self.btn_payment.setIcon(qta.icon('fa5s.cash-register', color='white'))
        self.btn_payment.setFixedHeight(46)
        self.btn_payment.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_payment.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
                color: white; border: none; border-radius: 10px;
                font-size: 14px; font-weight: 900;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #059669);
            }
            QPushButton:disabled {
                background: #94a3b8;
            }
        """)

        self.btn_kot.clicked.connect(self.send_kot)
        self.btn_split.clicked.connect(self.process_split_bill)
        btn_transfer.clicked.connect(self.transfer_table)
        self.btn_payment.clicked.connect(self.process_payment)

        act_row.addWidget(self.btn_kot, stretch=1)
        act_row.addWidget(self.btn_split, stretch=1)
        act_row.addWidget(btn_transfer, stretch=1)
        act_row.addWidget(self.btn_payment, stretch=2)

        right_layout.addLayout(act_row)
        layout.addWidget(right_panel, stretch=4)

        self.load_menu_data()
        self.on_order_type_change("Dine In")

    # -- Navigation ------------------------------------------------------------

    def go_back(self):
        self.parent_page.show_tables()

    # -- Setup / Load ----------------------------------------------------------

    def setup(self, table_no, order_type, order_id=None):
        self.table_no = table_no
        self.order_type = order_type
        self.current_order_id = order_id
        self.cart_items = {}
        self.current_customer = None
        self.redeemed_points = 0
        self._payment_in_progress = False
        self.btn_payment.setEnabled(True)

        for sp in (self.spin_discount, self.spin_service, self.spin_tax, self.spin_delivery_amt):
            sp.blockSignals(True)
            sp.setValue(0.0)
            sp.blockSignals(False)
        self.cust_name_input.clear()
        self.cust_phone_input.clear()
        self.cust_address_input.clear()
        self.combo_order_type.blockSignals(True)
        self.combo_order_type.setCurrentText(order_type if order_type else "Dine In")
        self.combo_order_type.blockSignals(False)
        self.on_order_type_change(self.combo_order_type.currentText())
        self.update_customer_ui()
        self.update_cart_ui()

        waiter = self.parent_page.user.get('username', 'Staff')
        info = order_type or "Dine In"
        if table_no:
            info += f"  .  Table: {table_no}"
        info += f"  .  {waiter}"
        self.info_label.setText(info)

        now = datetime.now()
        if 17 <= now.hour < 19:
            self.spin_discount.setValue(10.0)
            self.info_label.setText(info + "  .  Happy Hour -10%")

        if order_id:
            existing = orders_col.find_one({"_id": order_id})
            if existing:
                self.load_existing_order(existing)
        elif table_no:
            existing = orders_col.find_one({"table_no": table_no, "status": {"$in": ["Running", "Kitchen"]}})
            if existing:
                self.current_order_id = existing["_id"]
                self.load_existing_order(existing)

    def load_existing_order(self, order):
        self.cart_items = {}
        for item in order.get('items', []):
            name = item['name']
            self.cart_items[name] = {
                'qty': item['qty'], 'price': item['price'],
                'note': item.get('note', ''),
                'obj': {'_id': item.get('id', ''), 'name': name, 'price': item['price'],
                        'category': item.get('category', ''),
                        'is_combo': item.get('is_combo', False),
                        'combo_items': item.get('combo_items', [])},
            }
        self.spin_discount.blockSignals(True)
        self.spin_service.blockSignals(True)
        self.spin_discount.setValue(order.get('discount_percent', 0.0))
        self.spin_service.setValue(order.get('service_percent', 0.0))
        self.spin_discount.blockSignals(False)
        self.spin_service.blockSignals(False)
        self.cust_name_input.setText(order.get('customer_name', ''))
        self.cust_phone_input.setText(order.get('customer_phone', ''))
        self.cust_address_input.setText(order.get('delivery_address', ''))
        o_type = order.get('order_type', 'Dine In')
        self.combo_order_type.setCurrentText(o_type)
        self.on_order_type_change(o_type)
        if order.get('customer_phone'):
            self.search_customer()
        if order.get('token_no'):
            cur = self.info_label.text()
            if "Token:" not in cur:
                self.info_label.setText(f"{cur}  .  Token: {order['token_no']}")
        self.update_cart_ui()

    # -- Menu ------------------------------------------------------------------

    def load_menu_data(self):
        try:
            self.menu_items = get_menu()
            categories = sorted(set(i['category'] for i in self.menu_items if i.get('category')))
            categories.insert(0, "All")
            for i in reversed(range(self.cat_layout.count())):
                w = self.cat_layout.itemAt(i).widget()
                if w:
                    w.setParent(None)
            self.cat_buttons = []
            for cat in categories:
                btn = QPushButton(cat)
                btn.setFixedHeight(32)
                btn.setCheckable(True)
                is_all = cat == "All"
                if is_all:
                    btn.setChecked(True)
                btn.setProperty("class", "cat-btn-active" if is_all else "cat-btn")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda c, ca=cat, b=btn: self.filter_category(ca, b))
                self.cat_layout.addWidget(btn)
                self.cat_buttons.append(btn)
            self.cat_layout.addStretch()
            self.render_menu()
        except Exception as e:
            print(f"Menu Load Error: {e}")

    def filter_category(self, cat, btn):
        self.current_category = cat
        for b in self.cat_buttons:
            b.setChecked(False)
            b.setProperty("class", "cat-btn")
            b.style().unpolish(b)
            b.style().polish(b)
        btn.setChecked(True)
        btn.setProperty("class", "cat-btn-active")
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        self.render_menu()

    def filter_menu(self):
        self.render_menu()

    def render_menu(self):
        for i in reversed(range(self.menu_grid_layout.count())):
            w = self.menu_grid_layout.itemAt(i).widget()
            if w:
                w.setParent(None)
        search = self.search_input.text().lower()
        row, col, count = 0, 0, 0
        for item in self.menu_items:
            if not item.get('available', True):
                continue
            if self.current_category != "All" and item.get('category') != self.current_category:
                continue
            if search and search not in item['name'].lower():
                continue
            self.menu_grid_layout.addWidget(self.create_item_card(item), row, col)
            col += 1
            count += 1
            if col >= 5:
                col = 0
                row += 1
        if count == 0:
            empty_lbl = QLabel("No menu items found")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet(
                "color: #94a3b8; font-size: 16px; padding: 60px; background: transparent;"
            )
            self.menu_grid_layout.addWidget(empty_lbl, 0, 0, 1, 5)

    def create_item_card(self, item):
        card = QFrame()
        card.setMinimumSize(140, 148)
        card.setMaximumSize(190, 180)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setProperty("class", "item-card")
        card.setStyleSheet("""
            QFrame[class="item-card"] {
                background: white;
                border: 1.5px solid #f1f5f9;
                border-radius: 14px;
            }
            QFrame[class="item-card"]:hover {
                border-color: #059669;
                background: #fafbff;
            }
        """)

        l = QVBoxLayout(card)
        l.setContentsMargins(8, 8, 8, 8)
        l.setSpacing(4)

        if item.get('is_combo'):
            badge = _badge("COMBO", "#f59e0b", "#1e293b", 4)
            badge.setFixedHeight(18)
            badge.setStyleSheet(
                "background: #fef3c7; color: #b45309; border-radius: 5px; "
                "font-size: 9px; font-weight: 800; padding: 2px 8px; letter-spacing: 0.5px;"
            )
            l.addWidget(badge)

        img_lbl = QLabel()
        img_lbl.setFixedHeight(80)
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_path = item.get('image', '')
        if img_path and os.path.exists(img_path):
            try:
                pix = QPixmap(img_path)
                if not pix.isNull():
                    img_lbl.setPixmap(pix.scaled(
                        139, 80,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ))
                    img_lbl.setStyleSheet("background: #f8fafc; border-radius: 10px;")
                else:
                    img_lbl.setPixmap(qta.icon('fa5s.utensils', color='#cbd5e1').pixmap(34, 34))
                    img_lbl.setStyleSheet("background: #f1f5f9; border-radius: 10px;")
            except Exception:
                img_lbl.setPixmap(qta.icon('fa5s.utensils', color='#cbd5e1').pixmap(34, 34))
                img_lbl.setStyleSheet("background: #f1f5f9; border-radius: 10px;")
        else:
            img_lbl.setPixmap(qta.icon('fa5s.utensils', color='#cbd5e1').pixmap(34, 34))
            img_lbl.setStyleSheet("background: #f1f5f9; border-radius: 10px;")
        l.addWidget(img_lbl)

        name_lbl = QLabel(item['name'])
        name_lbl.setWordWrap(True)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setProperty("class", "item-name")
        name_lbl.setFixedHeight(30)
        l.addWidget(name_lbl)

        price_lbl = QLabel(f"Rs {item['price']:.0f}")
        price_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price_lbl.setProperty("class", "item-price")
        l.addWidget(price_lbl)

        card.mousePressEvent = lambda e: self.add_to_cart(item)
        return card

    # -- Cart ------------------------------------------------------------------

    def add_to_cart(self, item):
        name = item['name']
        if name in self.cart_items:
            self.cart_items[name]['qty'] += 1
        else:
            self.cart_items[name] = {'qty': 1, 'price': item['price'], 'obj': item}
        self.update_cart_ui()

    def remove_item(self, item_name):
        if item_name in self.cart_items:
            del self.cart_items[item_name]
            self.update_cart_ui()

    def change_qty(self, item_name, delta):
        if item_name in self.cart_items:
            self.cart_items[item_name]['qty'] = max(0, self.cart_items[item_name]['qty'] + delta)
            if self.cart_items[item_name]['qty'] == 0:
                del self.cart_items[item_name]
            self.update_cart_ui()

    def add_note(self, item_name):
        if item_name not in self.cart_items:
            return
        dlg = NoteDialog(self.cart_items[item_name].get('note', ''), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cart_items[item_name]['note'] = dlg.get_note()
            self.update_cart_ui()

    # -- Totals ----------------------------------------------------------------

    def get_totals(self, payment_method=None):
        sub = sum(i['qty'] * i['price'] for i in self.cart_items.values())
        self.discount_percent = self.spin_discount.value()
        disc_amt    = sub * (self.discount_percent / 100)
        points_disc = getattr(self, 'redeemed_points', 0)
        taxable     = max(sub - disc_amt - points_disc, 0)
        self.service_percent = self.spin_service.value()
        svc_amt = taxable * (self.service_percent / 100)

        tax_rate = self.spin_tax.value() / 100.0
        tax      = taxable * tax_rate
        delivery = self.spin_delivery_amt.value()
        grand    = taxable + svc_amt + tax + delivery
        return {
            "subtotal": sub, "discount": disc_amt, "points_discount": points_disc,
            "service_charge": svc_amt, "tax": tax, "tax_rate_pct": self.spin_tax.value(),
            "delivery_charge": delivery, "grand_total": grand,
        }

    def update_totals_ui(self):
        t = self.get_totals()
        self.lbl_subtotal.setText(f"Rs {t['subtotal']:,.2f}")
        self.lbl_discount_amt.setText(f"- Rs {t['discount']:,.2f}")
        self.lbl_service_amt.setText(f"Rs {t['service_charge']:,.2f}")
        self.lbl_tax.setText(f"Rs {t['tax']:,.2f}")
        self.lbl_total.setText(f"Rs {t['grand_total']:,.2f}")

    def update_cart_ui(self):
        self.cart_table.setRowCount(len(self.cart_items))
        for r, (name, data) in enumerate(self.cart_items.items()):
            qty = data['qty']
            price = data['price']

            name_item = QTableWidgetItem(name)
            name_item.setForeground(QColor("#1e293b"))
            name_item.setToolTip(name)
            name_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            self.cart_table.setItem(r, 0, name_item)

            # Price column
            price_item = QTableWidgetItem(f"{price:,.0f}")
            price_item.setForeground(QColor("#475569"))
            price_item.setFont(QFont("Segoe UI", 10))
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.cart_table.setItem(r, 1, price_item)

            # Qty widget with +/- buttons
            qty_w = QWidget()
            qty_w.setStyleSheet("background: transparent;")
            ql = QHBoxLayout(qty_w)
            ql.setContentsMargins(0, 2, 0, 2)
            ql.setSpacing(4)
            ql.setAlignment(Qt.AlignmentFlag.AlignCenter)

            def _qbtn(sym, bg_hover, text_c="#1e293b"):
                b = QPushButton(sym)
                b.setFixedSize(26, 26)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setStyleSheet(f"""
                    QPushButton {{
                        background: #f1f5f9; color: {text_c};
                        border-radius: 7px; font-weight: 900; font-size: 14px;
                        border: 1.5px solid #e2e8f0;
                    }}
                    QPushButton:hover {{
                        background: {bg_hover}; color: white; border: none;
                    }}
                """)
                return b

            b_minus = _qbtn("\u2212", "#ef4444")
            lbl_q = QLabel(str(qty))
            lbl_q.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_q.setStyleSheet("color: #1e293b; font-weight: 900; font-size: 14px; min-width: 20px; background: transparent;")
            b_plus = _qbtn("+", "#059669")

            b_minus.clicked.connect(lambda c, n=name: self.change_qty(n, -1))
            b_plus.clicked.connect(lambda c, n=name: self.change_qty(n, 1))
            lbl_q.mouseDoubleClickEvent = lambda e, n=name, q=qty: self._edit_qty_direct(n, q)
            lbl_q.setCursor(Qt.CursorShape.IBeamCursor)
            lbl_q.setToolTip("Double-click to enter quantity")

            ql.addWidget(b_minus)
            ql.addWidget(lbl_q)
            ql.addWidget(b_plus)
            self.cart_table.setCellWidget(r, 2, qty_w)

            # Total column
            total_val = qty * price
            total_item = QTableWidgetItem(f"{total_val:,.0f}")
            total_item.setForeground(QColor("#059669"))
            total_item.setFont(QFont("Segoe UI", 12, QFont.Weight.ExtraBold))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.cart_table.setItem(r, 3, total_item)

            # Actions column
            act_w = QWidget()
            act_w.setStyleSheet("background: transparent;")
            al = QHBoxLayout(act_w)
            al.setContentsMargins(0, 0, 4, 0)
            al.setSpacing(5)
            al.setAlignment(Qt.AlignmentFlag.AlignRight)

            note = data.get('note', '')
            btn_note = QPushButton()
            btn_note.setIcon(qta.icon('fa5s.sticky-note', color='white' if note else '#94a3b8'))
            btn_note.setFixedSize(28, 28)
            btn_note.setCursor(Qt.CursorShape.PointingHandCursor)
            if note:
                btn_note.setStyleSheet("background: #f59e0b; border: none; border-radius: 7px;")
                btn_note.setToolTip(f"Note: {note}")
            else:
                btn_note.setStyleSheet("background: transparent; border: 1.5px solid #e2e8f0; border-radius: 7px;")
                btn_note.setToolTip("Add Note")
            btn_note.clicked.connect(lambda c, n=name: self.add_note(n))

            btn_del = QPushButton()
            btn_del.setIcon(qta.icon('fa5s.trash-alt', color='#ef4444'))
            btn_del.setFixedSize(28, 28)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background: transparent; border: 1.5px solid #e2e8f0; border-radius: 7px;")
            btn_del.clicked.connect(lambda c, n=name: self._confirm_remove_item(n))

            al.addWidget(btn_note)
            al.addWidget(btn_del)
            self.cart_table.setCellWidget(r, 4, act_w)
            self.cart_table.setRowHeight(r, 52)

        self.update_totals_ui()

    # -- KOT -------------------------------------------------------------------

    def send_kot(self):
        if not self.cart_items:
            return
        items_list = [{
            "name": n, "qty": d['qty'], "price": d['price'],
            "total": d['qty'] * d['price'],
            "category": d['obj'].get('category', ''),
            "note": d.get('note', ''), "id": str(d['obj'].get('_id', '')),
            "is_combo": d['obj'].get('is_combo', False),
            "combo_items": d['obj'].get('combo_items', []),
        } for n, d in self.cart_items.items()]
        totals = self.get_totals()
        order_data = {
            "table_no": self.table_no, "order_type": self.combo_order_type.currentText(),
            "items": items_list, "subtotal": totals['subtotal'],
            "discount": totals['discount'], "discount_percent": self.discount_percent,
            "points_discount": totals.get('points_discount', 0),
            "service_charge": totals['service_charge'], "service_percent": self.service_percent,
            "tax": totals['tax'], "delivery_charge": totals.get('delivery_charge', 0),
            "grand_total": totals['grand_total'],
            "customer_phone": self.cust_phone_input.text(),
            "customer_name": self.cust_name_input.text(),
            "delivery_address": self.cust_address_input.text(),
            "rider": None, "status": "Running", "payment_method": "Pending",
            "kitchen_status": "Pending",
            "waiter": self.parent_page.user.get('username') if self.parent_page.user else "Admin",
            "updated_at": datetime.now(),
        }
        if self.current_order_id:
            orders_col.update_one({"_id": self.current_order_id}, {"$set": order_data})
            full_order = orders_col.find_one({"_id": self.current_order_id})
        else:
            current_user = self.parent_page.user.get('username')
            active_shift = get_active_shift(current_user)
            shift_id = active_shift['_id'] if active_shift else None
            shift_id_str = str(shift_id) if shift_id else None
            order_data["shift_id"] = shift_id_str
            order_data["token_no"] = generate_token_no(shift_id_str, self.combo_order_type.currentText())
            cur = self.info_label.text()
            if "Token:" not in cur:
                self.info_label.setText(f"{cur}  .  Token: {order_data['token_no']}")
            order_data["created_at"] = datetime.now()
            order_data["invoice_no"] = generate_invoice_no()
            res = orders_col.insert_one(order_data)
            self.current_order_id = res.inserted_id
            full_order = order_data
        if self.table_no:
            set_table_status(self.table_no, "Running")
        threading.Thread(target=print_kot, args=(full_order,), daemon=True).start()
        QMessageBox.information(self, "KOT Sent", f"Order sent to Kitchen!\nTable: {self.table_no}")
        self.go_back()

    # -- Split Bill ------------------------------------------------------------

    def process_split_bill(self):
        if not self.cart_items:
            return
        msg = QMessageBox(self)
        msg.setWindowTitle("Split Bill Options")
        msg.setText("Choose split method:")
        btn_amount = msg.addButton("By Amount", QMessageBox.ButtonRole.ActionRole)
        btn_items  = msg.addButton("By Items",  QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()
        if msg.clickedButton() == btn_amount:
            dlg = SplitBillDialog(self.get_totals()['grand_total'], self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.complete_order("Split", dlg.payments)
        elif msg.clickedButton() == btn_items:
            dlg = ItemSplitDialog(self.cart_items, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.handle_item_split_payment(dlg.paid_items)

    def handle_item_split_payment(self, paid_items):
        sub_items_list = []
        sub_subtotal = 0
        for name, qty in paid_items.items():
            if qty > 0:
                d = self.cart_items[name]
                price = d['price']
                sub_subtotal += qty * price
                sub_items_list.append({
                    "name": name, "qty": qty, "price": price, "note": d.get('note', ''),
                    "id": str(d['obj'].get('_id', '')),
                    "is_combo": d['obj'].get('is_combo', False),
                    "combo_items": d['obj'].get('combo_items', []),
                })
        disc_amt = sub_subtotal * (self.discount_percent / 100)
        taxable  = max(sub_subtotal - disc_amt, 0)
        svc_amt  = taxable * (self.service_percent / 100)
        tax      = taxable * (get_setting("tax_rate", 0.0) / 100.0)
        grand    = taxable + svc_amt + tax
        _split_user = self.parent_page.user.get('username') if self.parent_page.user else "Admin"
        _split_shift = get_active_shift(_split_user)
        _now = datetime.now()
        split_order = {
            "invoice_no": generate_invoice_no(), "table_no": self.table_no,
            "order_type": self.order_type, "items": sub_items_list,
            "subtotal": sub_subtotal, "discount": disc_amt,
            "service_charge": svc_amt, "tax": tax, "grand_total": grand,
            "status": "Completed", "payment_method": "Split-Item",
            "created_at": _now, "updated_at": _now, "completed_at": _now,
            "parent_order_id": self.current_order_id,
            "waiter": _split_user,
            "shift_id": str(_split_shift['_id']) if _split_shift else None,
        }
        orders_col.insert_one(split_order)
        try:
            for item in sub_items_list:
                qty = item.get("qty", 0)
                if not qty:
                    continue
                if item.get("is_combo"):
                    for sub in item.get("combo_items", []):
                        sub_id = sub.get("id")
                        if sub_id:
                            recipe = get_recipe(sub_id)
                            if recipe:
                                for ing in recipe.get("ingredients", []):
                                    needed = ing.get("quantity", 0) * sub.get("qty", 1) * qty
                                    if needed:
                                        deduct_stock(ing.get("item_name"), needed,
                                                     reason=f"Sale Split {split_order.get('invoice_no')}",
                                                     user=split_order.get("waiter", "System"))
                else:
                    item_id = item.get("id")
                    if item_id:
                        recipe = get_recipe(item_id)
                        if recipe:
                            for ing in recipe.get("ingredients", []):
                                needed = ing.get("quantity", 0) * qty
                                if needed:
                                    deduct_stock(ing.get("item_name"), needed,
                                                 reason=f"Sale Split {split_order.get('invoice_no')}",
                                                 user=split_order.get("waiter", "System"))
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Inventory deduction failed: {e}")
        print_receipt(split_order)
        for name, qty in paid_items.items():
            cur_qty = self.cart_items[name]['qty']
            new_qty = cur_qty - qty
            if new_qty <= 0:
                del self.cart_items[name]
            else:
                self.cart_items[name]['qty'] = new_qty
        self.update_cart_ui()
        if self.cart_items:
            new_items = [{
                "name": n, "qty": d['qty'], "price": d['price'], "note": d.get('note', ''),
                "id": str(d['obj'].get('_id', '')),
                "is_combo": d['obj'].get('is_combo', False),
                "combo_items": d['obj'].get('combo_items', []),
            } for n, d in self.cart_items.items()]
            t = self.get_totals()
            if self.current_order_id:
                orders_col.update_one({"_id": self.current_order_id}, {"$set": {
                    "items": new_items, "subtotal": t['subtotal'],
                    "tax": t['tax'], "grand_total": t['grand_total'],
                    "updated_at": datetime.now(),
                }})
        else:
            if self.current_order_id:
                orders_col.update_one({"_id": self.current_order_id}, {"$set": {
                    "status": "Completed", "completed_at": datetime.now(),
                }})
            if self.table_no:
                set_table_status(self.table_no, "Free")
            self.go_back()
        QMessageBox.information(self, "Success", "Split payment successful!")

    # -- Payment ---------------------------------------------------------------

    def process_payment(self):
        if not self.cart_items or self._payment_in_progress:
            return
        self._payment_in_progress = True
        self.btn_payment.setEnabled(False)
        # Show payment dialog with totals based on no specific method yet
        dlg = PaymentDialog(self.get_totals()['grand_total'], self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            pd = dlg.payment_data
            # Recalculate with payment-method-specific tax
            method = pd['method']
            totals_final = self.get_totals(payment_method=method)
            amt = totals_final['grand_total']
            payments = [{"method": method, "amount": amt, "received": pd['received'], "change": pd['change']}]
            self.complete_order(method, payments, pd.get('send_whatsapp', False), totals_final)
        else:
            self._payment_in_progress = False
            self.btn_payment.setEnabled(True)

    def complete_order(self, main_method, payments, send_whatsapp=False, totals=None):
        totals = totals or self.get_totals(payment_method=main_method)
        items_list = [{
            "name": n, "qty": d['qty'], "price": d['price'],
            "total": d['qty'] * d['price'],
            "category": d['obj'].get('category', ''),
            "note": d.get('note', ''),
            "id": str(d['obj'].get('_id', '')),
            "is_combo": d['obj'].get('is_combo', False),
            "combo_items": d['obj'].get('combo_items', []),
        } for n, d in self.cart_items.items()]
        order_data = {
            "table_no": self.table_no, "order_type": self.combo_order_type.currentText(),
            "items": items_list, "subtotal": totals['subtotal'],
            "discount": totals['discount'], "discount_percent": self.discount_percent,
            "points_discount": totals.get('points_discount', 0),
            "service_charge": totals['service_charge'], "service_percent": self.service_percent,
            "tax": totals['tax'], "delivery_charge": totals.get('delivery_charge', 0),
            "grand_total": totals['grand_total'],
            "customer_phone": self.cust_phone_input.text(),
            "customer_name": self.cust_name_input.text(),
            "delivery_address": self.cust_address_input.text(),
            "rider": None, "status": "Completed", "payment_method": main_method,
            "payments": payments,
            "waiter": self.parent_page.user.get('username') if self.parent_page.user else "Admin",
            "completed_at": datetime.now(),
        }
        if self.current_customer:
            order_data["customer_id"] = str(self.current_customer.get('_id'))
        order_data["updated_at"] = datetime.now()
        if self.current_order_id:
            orders_col.update_one({"_id": self.current_order_id}, {"$set": order_data})
            full_order = orders_col.find_one({"_id": self.current_order_id})
            # Update shift totals for orders that were created via KOT and now completed
            if full_order:
                existing_shift_id = full_order.get("shift_id")
                if existing_shift_id:
                    grand = totals['grand_total']
                    if main_method == "Cash":
                        update_shift_totals(existing_shift_id, cash_inc=grand)
                    else:
                        update_shift_totals(existing_shift_id, card_inc=grand)
        else:
            current_user = self.parent_page.user.get('username')
            active_shift = get_active_shift(current_user)
            shift_id = active_shift['_id'] if active_shift else None
            order_data["shift_id"] = str(shift_id) if shift_id else None
            order_data["token_no"] = generate_token_no(shift_id, self.combo_order_type.currentText())
            cur = self.info_label.text()
            if "Token:" not in cur:
                self.info_label.setText(f"{cur}  .  Token: {order_data['token_no']}")
            order_data["created_at"] = datetime.now()
            order_data["invoice_no"] = generate_invoice_no()
            try:
                res = orders_col.insert_one(order_data)
                full_order = order_data
                full_order["_id"] = res.inserted_id
            except Exception as db_err:
                QMessageBox.critical(self, "Database Error", f"Failed to save order:\n{db_err}")
                return
            if shift_id:
                grand = totals['grand_total']
                if main_method == "Cash":
                    update_shift_totals(shift_id, cash_inc=grand)
                else:
                    update_shift_totals(shift_id, card_inc=grand)
        if self.cust_phone_input.text():
            cust = create_or_update_customer(
                self.cust_phone_input.text(),
                self.cust_name_input.text(),
                self.cust_address_input.text(),
            )
            cust_id = cust.get('_id')
            log_customer_order(cust_id, full_order.get('_id'), totals['grand_total'])
            pts = int(totals['grand_total'] / 100)
            if pts > 0:
                add_loyalty_points(cust_id, pts)
            if getattr(self, 'redeemed_points', 0) > 0:
                deduct_loyalty_points(cust_id, self.redeemed_points)
        for name, data in self.cart_items.items():
            qty = data['qty']
            item_obj = data['obj']
            if item_obj.get('is_combo'):
                for sub in item_obj.get('combo_items', []):
                    sub_id = sub.get('id')
                    if sub_id:
                        recipe = get_recipe(sub_id)
                        if recipe:
                            for ing in recipe.get('ingredients', []):
                                deduct_stock(
                                    ing['item_name'],
                                    ing['quantity'] * sub.get('qty', 1) * qty,
                                    reason=f"Sale Combo {name}",
                                )
            else:
                recipe = get_recipe(str(item_obj.get('_id', '')))
                if recipe:
                    for ing in recipe.get('ingredients', []):
                        deduct_stock(
                            ing['item_name'],
                            ing['quantity'] * qty,
                            reason=f"Sale {self.table_no}",
                        )
        if self.table_no:
            set_table_status(self.table_no, "Free")

        # Ask which bill type to print (Cash or Card)
        bill_dlg = BillTypeDialog(full_order.get('grand_total', totals['grand_total']), self)
        if bill_dlg.exec() == QDialog.DialogCode.Accepted and bill_dlg.bill_type:
            bill_order = dict(full_order)
            bill_order['bill_type'] = bill_dlg.bill_type
            threading.Thread(target=print_receipt, args=(bill_order,), daemon=True).start()
        else:
            threading.Thread(target=print_receipt, args=(full_order,), daemon=True).start()

        if send_whatsapp:
            phone = self.cust_phone_input.text().strip()
            if phone:
                try:
                    send_receipt_via_whatsapp(phone, full_order, auto_send=True)
                    QMessageBox.information(self, "WhatsApp", "WhatsApp Receipt initiated!")
                except Exception as e:
                    QMessageBox.warning(self, "WhatsApp Error", f"Failed to send: {e}")
            else:
                QMessageBox.warning(self, "WhatsApp Error", "No phone number provided!")
        self._payment_in_progress = False
        QMessageBox.information(self, "Success", "Payment Recorded & Receipt Printed!")
        self.go_back()

    # -- Order Type Change -----------------------------------------------------

    def on_order_type_change(self, order_type):
        self.order_type = order_type
        cat_charges = get_setting("category_charges", {})
        cat_cfg = cat_charges.get(order_type, {})

        # Service charge from settings
        svc = cat_cfg.get("service_charge", 0.0)
        self.spin_service.blockSignals(True)
        self.spin_service.setValue(svc)
        self.spin_service.blockSignals(False)

        # Tax rate from settings
        tax_rate = cat_cfg.get("tax_rate", get_setting("tax_rate", 0.0))
        self.spin_tax.blockSignals(True)
        self.spin_tax.setValue(tax_rate)
        self.spin_tax.blockSignals(False)

        # Delivery charge
        if order_type == "Delivery":
            self.address_container.show()
            self.spin_delivery_amt.blockSignals(True)
            self.spin_delivery_amt.setValue(get_setting("delivery_charge", 150.0))
            self.spin_delivery_amt.blockSignals(False)
            self.spin_delivery_amt.setEnabled(True)
        else:
            self.address_container.hide()
            self.spin_delivery_amt.blockSignals(True)
            self.spin_delivery_amt.setValue(0.0)
            self.spin_delivery_amt.blockSignals(False)
            self.spin_delivery_amt.setEnabled(False)

        self.update_totals_ui()

    # -- Customer / CRM --------------------------------------------------------

    def search_customer(self):
        phone = self.cust_phone_input.text().strip()
        if not phone:
            return
        cust = get_customer_by_phone(phone)
        if cust:
            self.current_customer = cust
            self.cust_name_input.setText(cust.get('name', ''))
            self.cust_address_input.setText(cust.get('address', ''))
        else:
            self.current_customer = None
        self.update_customer_ui()

    def update_customer_ui(self):
        if self.current_customer:
            pts = int(self.current_customer.get('points', 0) or 0)
            self.lbl_points.setText(f"{pts} pts")
            self.btn_redeem.setVisible(pts > 0)
        else:
            self.lbl_points.setText("0 pts")
            self.btn_redeem.hide()

    def redeem_points(self):
        if not self.current_customer:
            return
        pts = int(self.current_customer.get('points', 0) or 0)
        max_r = min(pts, self.get_totals()['subtotal'])
        amt, ok = QInputDialog.getInt(
            self, "Redeem Points",
            f"Available: {pts} pts  (1 pt = Rs 1)\nMax redeem: {int(max_r)}",
            value=0, min=0, max=int(max_r),
        )
        if ok:
            self.redeemed_points = amt
            self.update_totals_ui()

    # -- Helper Actions --------------------------------------------------------

    def _confirm_remove_item(self, item_name):
        if QMessageBox.question(
            self, "Remove Item",
            f"Remove '{item_name}' from cart?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            self.remove_item(item_name)

    def _edit_qty_direct(self, item_name, current_qty):
        new_qty, ok = QInputDialog.getInt(
            self, "Edit Quantity",
            f"Enter quantity for:\n{item_name}",
            current_qty, 0, 999,
        )
        if ok:
            if new_qty == 0:
                self.remove_item(item_name)
            else:
                self.cart_items[item_name]['qty'] = new_qty
                self.update_cart_ui()

    def transfer_table(self):
        if not self.table_no:
            QMessageBox.information(self, "Transfer", "Table transfer is only available for Dine In orders.")
            return
        if not self.current_order_id:
            QMessageBox.information(self, "Transfer", "No active order to transfer.")
            return
        all_tables = get_all_tables()
        free_tables = [t['table_no'] for t in all_tables if t['status'] == 'Available' and t['table_no'] != self.table_no]
        if not free_tables:
            QMessageBox.warning(self, "Transfer", "No free tables available to transfer to.")
            return
        target, ok = QInputDialog.getItem(
            self, "Transfer Table",
            f"Transfer from {self.table_no} to:",
            free_tables, 0, False,
        )
        if not ok or not target:
            return
        if QMessageBox.question(
            self, "Confirm Transfer",
            f"Transfer order from {self.table_no} to {target}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        orders_col.update_one({"_id": self.current_order_id}, {"$set": {"table_no": target, "updated_at": datetime.now()}})
        set_table_status(self.table_no, "Free")
        set_table_status(target, "Running")
        old_table = self.table_no
        self.table_no = target
        cur = self.info_label.text()
        self.info_label.setText(cur.replace(f"Table: {old_table}", f"Table: {target}"))
        QMessageBox.information(self, "Transferred", f"Order moved from {old_table} to {target}.")

    # -- Resize ----------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
