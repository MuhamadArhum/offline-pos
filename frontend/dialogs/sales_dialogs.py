"""
All dialog classes used by the Sales module.

Classes:
    PinDialog, SplitBillDialog, PaymentDialog,
    StartShiftDialog, EndShiftDialog,
    MergeTablesDialog, ShiftTableDialog,
    NoteDialog, ShortcutsDialog,
    DoneOrdersDialog, RunningOrdersDialog, ItemSplitDialog
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QLabel, QPushButton, QLineEdit, QComboBox,
    QDoubleSpinBox, QRadioButton, QButtonGroup, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QWidget,
    QDateEdit, QTimeEdit,
)
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QColor, QFont
import qtawesome as qta
import threading
from datetime import datetime

from backend.core.config import get_setting
from backend.core.database import orders_col, expenses_col
from backend.core.permissions import has_permission
from backend.services.table_service import get_all_tables, set_table_status
from backend.services.recipe_service import get_recipe
from backend.services.inventory_service import restore_stock
from backend.services.shift_service import get_all_shifts
from backend.utils.print_utils import print_receipt, print_kot
from frontend.components.pagination import PaginationControl

from frontend.modules.sales.helpers import (
    IMPROVED_STYLE,
    _divider, _card, _badge, _icon_btn, _action_btn,
)


# ─────────────────────────────────────────────────────────────────────────────
#  BILL TYPE DIALOG  (Cash Bill / Card Bill)
# ─────────────────────────────────────────────────────────────────────────────
class BillTypeDialog(QDialog):
    """
    Popup before printing: ask whether to print Cash Bill or Card Bill.
    Returns bill_type = 'Cash' or 'Card' via .bill_type attribute.
    """
    def __init__(self, grand_total, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Bill Type")
        self.setFixedSize(400, 260)
        self.setStyleSheet(IMPROVED_STYLE)
        self.bill_type = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(18)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon('fa5s.file-invoice-dollar', color='#f59e0b').pixmap(36, 36))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title = QLabel("Select Bill Type")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 900; color: #1e293b;")
        layout.addWidget(title)

        amt_lbl = QLabel(f"Grand Total: Rs {grand_total:,.2f}")
        amt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        amt_lbl.setStyleSheet("font-size: 13px; color: #64748b; font-weight: 600;")
        layout.addWidget(amt_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        btn_cash = QPushButton("  Cash Bill")
        btn_cash.setIcon(qta.icon('fa5s.money-bill-wave', color='white'))
        btn_cash.setMinimumHeight(50)
        btn_cash.setStyleSheet(
            "QPushButton { background: #059669; color: white; border-radius: 12px; "
            "font-size: 15px; font-weight: 800; border: none; }"
            "QPushButton:hover { background: #047857; }"
        )
        btn_cash.clicked.connect(lambda: self._select('Cash'))

        btn_card = QPushButton("  Card Bill")
        btn_card.setIcon(qta.icon('fa5s.credit-card', color='white'))
        btn_card.setMinimumHeight(50)
        btn_card.setStyleSheet(
            "QPushButton { background: #0ea5e9; color: white; border-radius: 12px; "
            "font-size: 15px; font-weight: 800; border: none; }"
            "QPushButton:hover { background: #0284c7; }"
        )
        btn_card.clicked.connect(lambda: self._select('Card'))

        btn_row.addWidget(btn_cash)
        btn_row.addWidget(btn_card)
        layout.addLayout(btn_row)

    def _select(self, bill_type):
        self.bill_type = bill_type
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  PIN DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class PinDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Security Check")
        self.setFixedSize(340, 460)
        self.setStyleSheet(IMPROVED_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(18)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon('fa5s.shield-alt', color='#059669').pixmap(52, 52))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        lbl = QLabel("Enter Admin PIN")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setProperty("class", "pin-title")
        layout.addWidget(lbl)

        self.pin_display = QLineEdit()
        self.pin_display.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pin_display.setReadOnly(True)
        self.pin_display.setFixedHeight(58)
        self.pin_display.setProperty("class", "pin-display")
        layout.addWidget(self.pin_display)

        grid = QGridLayout()
        grid.setSpacing(10)
        keys = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('C', 3, 0), ('0', 3, 1), ('\u232b', 3, 2),
        ]
        for k, r, c in keys:
            btn = QPushButton(k)
            btn.setFixedSize(78, 58)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if k == 'C':
                btn.setProperty("class", "pin-key pin-key-c")
            elif k == '\u232b':
                btn.setProperty("class", "pin-key pin-key-back")
            else:
                btn.setProperty("class", "pin-key")
            btn.clicked.connect(lambda _, x=k: self.key_press(x))
            grid.addWidget(btn, r, c)
        layout.addLayout(grid)

        btn_enter = QPushButton("CONFIRM")
        btn_enter.setFixedHeight(50)
        btn_enter.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_enter.setProperty("class", "pin-confirm")
        btn_enter.clicked.connect(self.check_pin)
        layout.addWidget(btn_enter)

    def key_press(self, key):
        if key == 'C':
            self.pin_display.clear()
        elif key == '\u232b':
            self.pin_display.backspace()
        else:
            self.pin_display.setText(self.pin_display.text() + key)

    def check_pin(self):
        actual_pin = get_setting("admin_pin", "1234")
        if self.pin_display.text() == actual_pin:
            self.accept()
        else:
            QMessageBox.warning(self, "Access Denied", "Invalid PIN!")
            self.pin_display.clear()


# ─────────────────────────────────────────────────────────────────────────────
#  SPLIT BILL DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class SplitBillDialog(QDialog):
    def __init__(self, total_amount, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Split Bill")
        self.setFixedSize(460, 560)
        self.setStyleSheet(IMPROVED_STYLE)
        self.total_amount = total_amount
        self.remaining_amount = total_amount
        self.payments = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        status_card = _card(radius=12)
        status_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f172a, stop:1 #1e293b);
                border: none; border-radius: 12px;
            }
        """)
        sl = QVBoxLayout(status_card)
        sl.setContentsMargins(20, 16, 20, 16)
        self.lbl_total_disp = QLabel(f"Total  Rs {total_amount:,.2f}")
        self.lbl_total_disp.setProperty("class", "split-total")
        self.lbl_total_disp.setStyleSheet("color: white; font-size: 18px; font-weight: 900;")
        self.lbl_remaining = QLabel(f"Remaining  Rs {total_amount:,.2f}")
        self.lbl_remaining.setProperty("class", "split-remaining")
        self.lbl_remaining.setStyleSheet("color: #f87171; font-size: 13px; font-weight: 700;")
        sl.addWidget(self.lbl_total_disp)
        sl.addWidget(self.lbl_remaining)
        layout.addWidget(status_card)

        form = _card(radius=12)
        fl = QGridLayout(form)
        fl.setContentsMargins(18, 16, 18, 16)
        fl.setSpacing(12)

        fl.addWidget(QLabel("Amount:"), 0, 0)
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0, 1000000)
        self.spin_amount.setValue(total_amount / 2)
        self.spin_amount.setFixedHeight(38)
        self.spin_amount.setProperty("class", "split-spin")
        fl.addWidget(self.spin_amount, 0, 1)

        fl.addWidget(QLabel("Method:"), 1, 0)
        self.combo_method = QComboBox()
        self.combo_method.addItems(["Cash", "Card", "Online"])
        self.combo_method.setFixedHeight(38)
        fl.addWidget(self.combo_method, 1, 1)

        btn_add = _action_btn("Add Payment", "fa5s.plus", "#059669", "#047857", height=40)
        fl.addWidget(btn_add, 2, 0, 1, 2)
        btn_add.clicked.connect(self.add_payment)
        layout.addWidget(form)

        layout.addWidget(QLabel("Payments Added:"))
        self.list_payments = QTableWidget()
        self.list_payments.setColumnCount(2)
        self.list_payments.setHorizontalHeaderLabels(["Method", "Amount"])
        self.list_payments.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.list_payments.verticalHeader().setVisible(False)
        self.list_payments.setShowGrid(False)
        self.list_payments.setAlternatingRowColors(True)
        layout.addWidget(self.list_payments)

        btn_finish = _action_btn("Finish & Print Receipt", "fa5s.receipt", "#059669", "#059669", height=48)
        btn_finish.clicked.connect(self.finish)
        layout.addWidget(btn_finish)

    def add_payment(self):
        amount = self.spin_amount.value()
        if amount <= 0:
            return
        if amount > self.remaining_amount + 1.0:
            QMessageBox.warning(self, "Error", "Amount exceeds remaining balance!")
            return
        method = self.combo_method.currentText()
        self.payments.append({"method": method, "amount": amount})
        self.remaining_amount -= amount
        if self.remaining_amount < 0:
            self.remaining_amount = 0
        self.update_ui()

    def update_ui(self):
        color = "#10b981" if self.remaining_amount <= 0 else "#f87171"
        self.lbl_remaining.setText(f"Remaining  Rs {self.remaining_amount:,.2f}")
        self.lbl_remaining.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 700;")
        self.spin_amount.setValue(self.remaining_amount)
        self.list_payments.setRowCount(len(self.payments))
        for r, p in enumerate(self.payments):
            self.list_payments.setItem(r, 0, QTableWidgetItem(p['method']))
            self.list_payments.setItem(r, 1, QTableWidgetItem(f"{p['amount']:,.2f}"))

    def finish(self):
        if self.remaining_amount > 1.0:
            QMessageBox.warning(self, "Error", "Bill not fully paid!")
            return
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  PAYMENT DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class PaymentDialog(QDialog):
    def __init__(self, total_amount, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Payment & Checkout")
        self.setFixedSize(520, 620)
        self.setStyleSheet(IMPROVED_STYLE)
        self.total_amount = total_amount
        self.payment_data = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        total_card = QFrame()
        total_card.setProperty("class", "payment-total-card")
        tc_layout = QVBoxLayout(total_card)
        tc_layout.setContentsMargins(28, 22, 28, 22)
        lbl_t = QLabel("TOTAL PAYABLE")
        lbl_t.setProperty("class", "payment-total-label")
        lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_amt = QLabel(f"Rs {total_amount:,.2f}")
        lbl_amt.setProperty("class", "payment-total-amount")
        lbl_amt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tc_layout.addWidget(lbl_t)
        tc_layout.addWidget(lbl_amt)
        layout.addWidget(total_card)

        method_lbl = QLabel("SELECT PAYMENT METHOD")
        method_lbl.setStyleSheet("font-size: 11px; font-weight: 800; color: #94a3b8; letter-spacing: 1px;")
        layout.addWidget(method_lbl)

        self.method_group = QButtonGroup(self)
        methods_layout = QHBoxLayout()
        methods_layout.setSpacing(12)
        methods = [
            ("Cash",   "fa5s.money-bill-wave", "#059669"),
            ("Card",   "fa5s.credit-card",     "#059669"),
            ("Online", "fa5s.mobile-alt",       "#0ea5e9"),
        ]
        self.radios = {}
        self.method_btns = {}
        for i, (m, icon_n, color) in enumerate(methods):
            frame = QFrame()
            frame.setFixedHeight(78)
            frame.setCursor(Qt.CursorShape.PointingHandCursor)
            frame.setProperty("class", "payment-method-btn")

            fl = QVBoxLayout(frame)
            fl.setContentsMargins(14, 10, 14, 10)
            fl.setSpacing(4)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(qta.icon(icon_n, color=color).pixmap(26, 26))
            rb = QRadioButton(m)
            rb.setStyleSheet("font-size: 13px; font-weight: 800; color: #1e293b;")
            if i == 0:
                rb.setChecked(True)
                frame.setProperty("class", "payment-method-btn payment-method-btn-selected")

            self.method_group.addButton(rb)
            self.radios[m] = rb
            self.method_btns[m] = frame

            row = QHBoxLayout()
            row.addWidget(icon_lbl)
            row.addWidget(rb)
            row.addStretch()
            fl.addLayout(row)
            methods_layout.addWidget(frame)

        self.method_group.buttonClicked.connect(self.toggle_cash_input)
        layout.addLayout(methods_layout)

        self.cash_frame = _card(radius=12)
        cf_layout = QVBoxLayout(self.cash_frame)
        cf_layout.setContentsMargins(18, 16, 18, 16)
        cf_layout.setSpacing(10)

        cash_title = QLabel("Amount Received")
        cash_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        cf_layout.addWidget(cash_title)

        self.received_spin = QDoubleSpinBox()
        self.received_spin.setRange(0, 1000000)
        self.received_spin.setValue(total_amount)
        self.received_spin.setFixedHeight(52)
        self.received_spin.setProperty("class", "payment-received")
        self.received_spin.valueChanged.connect(self.calc_change)
        cf_layout.addWidget(self.received_spin)

        self.lbl_change = QLabel("Change: Rs 0.00")
        self.lbl_change.setProperty("class", "payment-change")
        self.lbl_change.setAlignment(Qt.AlignmentFlag.AlignRight)
        cf_layout.addWidget(self.lbl_change)
        layout.addWidget(self.cash_frame)

        self.chk_whatsapp = QCheckBox("  Send Receipt via WhatsApp")
        self.chk_whatsapp.setIcon(qta.icon('fa5b.whatsapp', color='#25D366'))
        self.chk_whatsapp.setStyleSheet("font-size: 13px; font-weight: 700; color: #25D366;")
        self.chk_whatsapp.setChecked(True)
        layout.addWidget(self.chk_whatsapp)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(50)
        btn_cancel.setFixedWidth(110)
        btn_cancel.setProperty("class", "payment-cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_confirm = QPushButton("  Confirm Payment")
        btn_confirm.setIcon(qta.icon('fa5s.check-circle', color='white'))
        btn_confirm.setFixedHeight(50)
        btn_confirm.setProperty("class", "payment-confirm")
        btn_confirm.clicked.connect(self.confirm_payment)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_confirm, stretch=1)
        layout.addLayout(btn_layout)

    def toggle_cash_input(self, btn):
        self.cash_frame.setVisible(btn.text() == "Cash")

    def calc_change(self):
        received = self.received_spin.value()
        change = max(received - self.total_amount, 0)
        self.lbl_change.setText(f"Change: Rs {change:,.2f}")

    def confirm_payment(self):
        method = self.method_group.checkedButton().text()
        received = self.received_spin.value() if method == "Cash" else 0
        change = received - self.total_amount if method == "Cash" else 0
        if method == "Cash" and received < self.total_amount:
            QMessageBox.warning(self, "Error", "Received amount is less than total!")
            return
        self.payment_data = {
            "method": method, "received": received,
            "change": change, "send_whatsapp": self.chk_whatsapp.isChecked()
        }
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  START SHIFT DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class StartShiftDialog(QDialog):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Start Shift")
        self.setFixedSize(360, 260)
        self.setStyleSheet(IMPROVED_STYLE)
        self.user = user

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        lbl_welcome = QLabel(f"Welcome, {user.get('username', 'User')}!")
        lbl_welcome.setProperty("class", "shift-welcome")
        layout.addWidget(lbl_welcome)

        sub = QLabel("Enter your opening cash to begin shift.")
        sub.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(sub)

        layout.addWidget(QLabel("Opening Cash:"))
        self.spin_cash = QDoubleSpinBox()
        self.spin_cash.setRange(0, 1000000)
        self.spin_cash.setPrefix("Rs. ")
        self.spin_cash.setValue(0)
        self.spin_cash.setFixedHeight(46)
        self.spin_cash.setProperty("class", "shift-spin")
        layout.addWidget(self.spin_cash)

        btn_start = _action_btn("Start Shift", "fa5s.play", "#059669", "#047857", height=50)
        btn_start.clicked.connect(self.accept)
        layout.addWidget(btn_start)

    def get_opening_cash(self):
        return self.spin_cash.value()


# ─────────────────────────────────────────────────────────────────────────────
#  END SHIFT DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class EndShiftDialog(QDialog):
    def __init__(self, shift_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("End Shift / Day Close")
        self.setFixedSize(540, 620)
        self.setStyleSheet(IMPROVED_STYLE)
        self.shift_data = shift_data

        opening_cash = shift_data.get('opening_cash', 0)
        start_time = shift_data.get('start_time')
        shift_id = shift_data.get('_id')

        cash_sales = 0
        if shift_id:
            sales = list(orders_col.find({
                "shift_id": {"$in": [str(shift_id), shift_id]},
                "status": "Completed",
                "payment_method": "Cash"
            }))
            if sales:
                cash_sales = sum(o.get('grand_total', 0) for o in sales)

        if cash_sales == 0:
            end_time = datetime.now()
            sales = list(orders_col.find({
                "updated_at": {"$gte": start_time, "$lte": end_time},
                "status": "Completed",
                "payment_method": "Cash"
            }))
            if sales:
                cash_sales = sum(o.get('grand_total', 0) for o in sales)

        total_expenses = 0
        if shift_id:
            expenses = list(expenses_col.find({"shift_id": {"$in": [str(shift_id), shift_id]}}))
            if expenses:
                total_expenses = sum(e.get('amount', 0) for e in expenses)

        if total_expenses == 0:
            user = shift_data.get('user')
            exp_query = {"timestamp": {"$gte": start_time, "$lte": datetime.now()}}
            if user:
                exp_query["$or"] = [{"user": user}, {"recorded_by": user}]
            expenses = list(expenses_col.find(exp_query))
            if expenses:
                total_expenses = sum(e.get('amount', 0) for e in expenses)

        expected_cash = opening_cash + cash_sales - total_expenses

        total_sales = 0
        if shift_id:
            all_sales = list(orders_col.find({
                "shift_id": {"$in": [str(shift_id), shift_id]},
                "status": "Completed"
            }))
            if not all_sales:
                all_sales = list(orders_col.find({
                    "updated_at": {"$gte": start_time, "$lte": datetime.now()},
                    "status": "Completed"
                }))
            total_sales = sum(o.get('grand_total', 0) for o in all_sales)

        card_sales = total_sales - cash_sales

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        title = QLabel("Shift Summary")
        title.setStyleSheet("font-size: 20px; font-weight: 900; color: #1e293b; letter-spacing: -0.5px;")
        layout.addWidget(title)

        summary = QFrame()
        summary.setProperty("class", "card")
        sl = QVBoxLayout(summary)
        sl.setContentsMargins(22, 18, 22, 18)
        sl.setSpacing(10)

        def _row(label, val, color=None):
            r = QHBoxLayout()
            l = QLabel(label)
            l.setStyleSheet("color: #94a3b8; font-size: 13px; font-family: 'Consolas', monospace;")
            v = QLabel(val)
            v.setStyleSheet(f"color: {color or '#1e293b'}; font-size: 13px; font-weight: 800; font-family: 'Consolas', monospace;")
            r.addWidget(l)
            r.addStretch()
            r.addWidget(v)
            return r

        sl.addLayout(_row("Shift Started:", shift_data['start_time'].strftime('%Y-%m-%d %H:%M')))
        sl.addLayout(_row("Opening Cash:", f"Rs {opening_cash:,.2f}"))
        sl.addWidget(_divider())
        sl.addLayout(_row("Total Sales:", f"Rs {total_sales:,.2f}", "#10b981"))
        sl.addLayout(_row("Cash Sales:", f"Rs {cash_sales:,.2f}"))
        sl.addLayout(_row("Card Sales:", f"Rs {card_sales:,.2f}"))
        sl.addLayout(_row("Expenses:", f"- Rs {total_expenses:,.2f}", "#ef4444"))
        sl.addWidget(_divider())
        sl.addLayout(_row("Expected Cash:", f"Rs {expected_cash:,.2f}", "#059669"))
        layout.addWidget(summary)

        layout.addWidget(QLabel("Actual Closing Cash:"))
        self.spin_closing = QDoubleSpinBox()
        self.spin_closing.setRange(0, 1000000)
        self.spin_closing.setPrefix("Rs. ")
        self.spin_closing.setValue(expected_cash)
        self.spin_closing.setFixedHeight(46)
        self.spin_closing.setProperty("class", "shift-spin")
        layout.addWidget(self.spin_closing)

        self.expected_cash = expected_cash

        self.lbl_diff = QLabel("Difference: Rs 0.00")
        self.lbl_diff.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_diff.setProperty("class", "shift-diff")
        self.lbl_diff.setStyleSheet("background: #f0fdf4; color: #10b981; border-radius: 10px; padding: 8px 16px; font-size: 14px; font-weight: 800;")
        layout.addWidget(self.lbl_diff)
        self.spin_closing.valueChanged.connect(self.calc_diff)

        btn_close = _action_btn("Close Shift & Print Report", "fa5s.file-invoice-dollar", "#ef4444", "#dc2626", height=50)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def calc_diff(self):
        actual = self.spin_closing.value()
        expected = self.expected_cash
        diff = actual - expected
        self.lbl_diff.setText(f"Difference: Rs {diff:,.2f}")
        if diff < 0:
            self.lbl_diff.setStyleSheet("background: #fef2f2; color: #ef4444; border-radius: 10px; padding: 8px 16px; font-size: 14px; font-weight: 800;")
        elif diff > 0:
            self.lbl_diff.setStyleSheet("background: #fffbeb; color: #f59e0b; border-radius: 10px; padding: 8px 16px; font-size: 14px; font-weight: 800;")
        else:
            self.lbl_diff.setStyleSheet("background: #f0fdf4; color: #10b981; border-radius: 10px; padding: 8px 16px; font-size: 14px; font-weight: 800;")

    def get_closing_cash(self):
        return self.spin_closing.value()


# ─────────────────────────────────────────────────────────────────────────────
#  MERGE TABLES DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class MergeTablesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Merge Tables")
        self.setFixedSize(440, 300)
        self.setStyleSheet(IMPROVED_STYLE + "QDialog { background: #ffffff; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        title = QLabel("Merge Tables")
        title.setStyleSheet("font-size: 18px; font-weight: 900; color: #1e293b;")
        layout.addWidget(title)
        layout.addWidget(_divider())

        lbl_src = QLabel("Source Table (to be merged & cleared):")
        lbl_src.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: 600;")
        layout.addWidget(lbl_src)
        self.combo_source = QComboBox()
        self.combo_source.setFixedHeight(38)
        layout.addWidget(self.combo_source)

        lbl_tgt = QLabel("Target Table (to merge into):")
        lbl_tgt.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: 600;")
        layout.addWidget(lbl_tgt)
        self.combo_target = QComboBox()
        self.combo_target.setFixedHeight(38)
        layout.addWidget(self.combo_target)

        btn_merge = _action_btn("Merge Tables", "fa5s.object-group", "#059669", "#059669", height=46)
        btn_merge.clicked.connect(self.merge)
        layout.addWidget(btn_merge)

        self.load_tables()

    def load_tables(self):
        tables = get_all_tables()
        running = [t['table_no'] for t in tables if t['status'] == 'Running']
        self.combo_source.addItems(running)
        self.combo_target.addItems(running)

    def merge(self):
        src = self.combo_source.currentText()
        tgt = self.combo_target.currentText()
        if not src or not tgt:
            return
        if src == tgt:
            QMessageBox.warning(self, "Error", "Cannot merge the same table!")
            return

        order_src = orders_col.find_one({"table_no": src, "status": "Running"})
        order_tgt = orders_col.find_one({"table_no": tgt, "status": "Running"})

        if not order_src:
            QMessageBox.warning(self, "Error", f"No running order on {src}")
            return
        if not order_tgt:
            QMessageBox.warning(self, "Error", f"No running order on {tgt}")
            return

        combined_items = order_tgt.get('items', []) + order_src.get('items', [])
        for item in combined_items:
            item['total'] = item.get('qty', 0) * item.get('price', 0)
        subtotal = sum(i['total'] for i in combined_items)
        discount_percent = float(order_tgt.get("discount_percent", 0) or 0)
        service_percent = float(order_tgt.get("service_percent", 0) or 0)
        points_disc = float(order_tgt.get("points_discount", 0) or 0)
        delivery_charge = float(order_tgt.get("delivery_charge", 0) or 0)
        disc_amt = subtotal * (discount_percent / 100.0)
        taxable = max(subtotal - disc_amt - points_disc, 0)
        svc_amt = taxable * (service_percent / 100.0)
        tax_rate = get_setting("tax_rate", 0.0) / 100.0
        tax = taxable * tax_rate
        total = taxable + svc_amt + tax + delivery_charge

        orders_col.update_one({"_id": order_tgt["_id"]}, {"$set": {
            "items": combined_items, "subtotal": subtotal, "discount": disc_amt,
            "points_discount": points_disc, "service_charge": svc_amt, "tax": tax,
            "grand_total": total, "updated_at": datetime.now()
        }})
        orders_col.update_one({"_id": order_src["_id"]}, {"$set": {"status": "Merged", "merged_into": tgt}})
        set_table_status(src, "Free")
        QMessageBox.information(self, "Success", f"Merged {src} into {tgt}")
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  SHIFT TABLE DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class ShiftTableDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shift Table")
        self.setFixedSize(440, 280)
        self.setStyleSheet(IMPROVED_STYLE + "QDialog { background: #ffffff; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        title = QLabel("Shift Table")
        title.setStyleSheet("font-size: 18px; font-weight: 900; color: #1e293b;")
        layout.addWidget(title)
        layout.addWidget(_divider())

        lbl_src = QLabel("Source Table (Running):")
        lbl_src.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: 600;")
        layout.addWidget(lbl_src)
        self.combo_source = QComboBox()
        self.combo_source.setFixedHeight(38)
        layout.addWidget(self.combo_source)

        lbl_tgt = QLabel("Target Table (Free):")
        lbl_tgt.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: 600;")
        layout.addWidget(lbl_tgt)
        self.combo_target = QComboBox()
        self.combo_target.setFixedHeight(38)
        layout.addWidget(self.combo_target)

        btn_shift = _action_btn("Shift Table", "fa5s.exchange-alt", "#0ea5e9", "#0284c7", height=46)
        btn_shift.clicked.connect(self.shift)
        layout.addWidget(btn_shift)

        self.load_tables()

    def load_tables(self):
        tables = get_all_tables()
        self.combo_source.addItems([t['table_no'] for t in tables if t['status'] == 'Running'])
        self.combo_target.addItems([t['table_no'] for t in tables if t['status'] == 'Free'])

    def shift(self):
        src = self.combo_source.currentText()
        tgt = self.combo_target.currentText()
        if not src or not tgt:
            return
        order = orders_col.find_one({"table_no": src, "status": "Running"})
        if not order:
            QMessageBox.warning(self, "Error", f"No running order on {src}")
            return
        orders_col.update_one({"_id": order["_id"]}, {"$set": {"table_no": tgt, "updated_at": datetime.now()}})
        set_table_status(src, "Free")
        set_table_status(tgt, "Running")
        QMessageBox.information(self, "Success", f"Shifted Table {src} \u2192 {tgt}")
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  NOTE DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class NoteDialog(QDialog):
    def __init__(self, current_note="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Note / Modifiers")
        self.setFixedSize(540, 420)
        self.setStyleSheet(IMPROVED_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        title = QLabel("Note & Modifiers")
        title.setStyleSheet("font-size: 17px; font-weight: 900; color: #1e293b;")
        layout.addWidget(title)

        layout.addWidget(QLabel("Custom Note:"))
        self.text_note = QLineEdit(current_note)
        self.text_note.setPlaceholderText("Enter custom note or select a modifier below...")
        self.text_note.setFixedHeight(44)
        self.text_note.setProperty("class", "note-input")
        layout.addWidget(self.text_note)

        layout.addWidget(QLabel("Quick Modifiers:"))
        grid = QGridLayout()
        grid.setSpacing(10)
        modifiers = [
            "Extra Cheese", "No Spicy", "Less Sugar", "No Ice",
            "Extra Spicy", "Well Done", "Medium Rare", "Pack Separately",
            "Less Oil", "No Onion", "No Garlic", "Sugar Free"
        ]
        row, col = 0, 0
        for mod in modifiers:
            btn = QPushButton(mod)
            btn.setFixedHeight(36)
            btn.setProperty("class", "modifier-btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda c, m=mod: self.add_modifier(m))
            grid.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1
        layout.addLayout(grid)

        btns = QHBoxLayout()
        btns.setSpacing(12)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(44)
        btn_cancel.setFixedWidth(100)
        btn_cancel.setStyleSheet("background: #f1f5f9; border: 1.5px solid #e2e8f0; border-radius: 10px; color: #64748b; font-weight: 700; padding: 0 16px;")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = _action_btn("Save Note", "fa5s.check", "#059669", "#059669", height=44)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok, stretch=1)
        btn_ok.clicked.connect(self.accept)
        layout.addLayout(btns)

    def add_modifier(self, mod):
        current = self.text_note.text()
        self.text_note.setText((current + ", " + mod) if current else mod)

    def get_note(self):
        return self.text_note.text().strip()


# ─────────────────────────────────────────────────────────────────────────────
#  SHORTCUTS DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setFixedSize(440, 340)
        self.setStyleSheet(IMPROVED_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        title = QLabel("Keyboard Shortcuts")
        title.setStyleSheet("font-size: 17px; font-weight: 900; color: #1e293b;")
        layout.addWidget(title)
        layout.addWidget(_divider())

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Key", "Action"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("border: none; font-size: 13px;")

        shortcuts = [
            ("F1", "Focus Search Box"),
            ("F5", "Refresh Tables / Orders"),
            ("Shift + T", "Shift Table"),
            ("Esc", "Go Back / Close Dialog"),
            ("Del", "Remove Item from Cart"),
        ]
        table.setRowCount(len(shortcuts))
        for r, (key, action) in enumerate(shortcuts):
            key_item = QTableWidgetItem(key)
            key_item.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
            key_item.setForeground(QColor("#059669"))
            key_item.setBackground(QColor("#ede9fe"))
            table.setItem(r, 0, key_item)
            table.setItem(r, 1, QTableWidgetItem(action))
            table.setRowHeight(r, 38)
        layout.addWidget(table)

        btn = _action_btn("Close", "fa5s.times", "#64748b", "#475569", height=40)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


# ─────────────────────────────────────────────────────────────────────────────
#  DONE ORDERS / HISTORY DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class DoneOrdersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_view = parent
        self.parent_page = getattr(parent, "parent_page", None)
        self.setWindowTitle("Order History & Refund")
        self.setMinimumSize(900, 600)
        self.resize(1100, 750)
        self.setStyleSheet(IMPROVED_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.pagination = PaginationControl()
        self.pagination.page_changed.connect(self.load_orders)
        self.pagination.limit_changed.connect(self.load_orders)

        h_layout = QHBoxLayout()
        title = QLabel("Order History & Refunds")
        title.setStyleSheet("font-size: 20px; font-weight: 900; color: #1e293b;")

        date_layout = QGridLayout()
        date_layout.setSpacing(10)
        date_layout.setColumnStretch(1, 1)
        date_layout.setColumnStretch(3, 1)

        self.start_date_label = QLabel("From Date:")
        self.start_date_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b;")
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate())
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_date_edit.setMinimumWidth(100)
        self.start_date_edit.setMaximumWidth(140)
        self.start_date_edit.setFixedHeight(32)
        self.start_date_edit.dateChanged.connect(lambda: (self.pagination.reset(), self.load_orders()))

        self.start_time_label = QLabel("From Time:")
        self.start_time_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b;")
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("HH:mm")
        self.start_time_edit.setTime(QTime(0, 0, 0))
        self.start_time_edit.setMinimumWidth(70)
        self.start_time_edit.setMaximumWidth(90)
        self.start_time_edit.setFixedHeight(32)
        self.start_time_edit.timeChanged.connect(lambda: (self.pagination.reset(), self.load_orders()))

        self.end_date_label = QLabel("To Date:")
        self.end_date_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b;")
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setMinimumWidth(100)
        self.end_date_edit.setMaximumWidth(140)
        self.end_date_edit.setFixedHeight(32)
        self.end_date_edit.dateChanged.connect(lambda: (self.pagination.reset(), self.load_orders()))

        self.end_time_label = QLabel("To Time:")
        self.end_time_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b;")
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat("HH:mm")
        self.end_time_edit.setTime(QTime(23, 59, 59))
        self.end_time_edit.setMinimumWidth(70)
        self.end_time_edit.setMaximumWidth(90)
        self.end_time_edit.setFixedHeight(32)
        self.end_time_edit.timeChanged.connect(lambda: (self.pagination.reset(), self.load_orders()))

        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("Search Invoice...")
        self.search_inp.setMinimumWidth(180)
        self.search_inp.setMaximumWidth(250)
        self.search_inp.setFixedHeight(38)
        self.search_inp.textChanged.connect(lambda: (self.pagination.reset(), self.load_orders()))

        self.shift_label = QLabel("Shift:")
        self.shift_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b;")
        self.shift_combo = QComboBox()
        self.shift_combo.setMinimumWidth(150)
        self.shift_combo.setMaximumWidth(200)
        self.shift_combo.setFixedHeight(38)
        self.shift_combo.currentIndexChanged.connect(lambda: (self.pagination.reset(), self.load_orders()))
        self._load_shifts()

        date_layout.addWidget(self.start_date_label, 0, 0)
        date_layout.addWidget(self.start_date_edit, 0, 1)
        date_layout.addWidget(self.start_time_label, 0, 2)
        date_layout.addWidget(self.start_time_edit, 0, 3)
        date_layout.addWidget(self.end_date_label, 1, 0)
        date_layout.addWidget(self.end_date_edit, 1, 1)
        date_layout.addWidget(self.end_time_label, 1, 2)
        date_layout.addWidget(self.end_time_edit, 1, 3)
        date_layout.addWidget(self.search_inp, 2, 0, 1, 2)
        date_layout.addWidget(self.shift_label, 2, 2)
        date_layout.addWidget(self.shift_combo, 2, 3)

        date_layout.setColumnStretch(1, 2)
        date_layout.setColumnStretch(3, 2)
        date_layout.setColumnStretch(0, 1)
        date_layout.setColumnStretch(2, 1)

        self.btn_today = QPushButton("Today")
        self.btn_today.setMinimumHeight(32)
        self.btn_today.setMinimumWidth(60)
        self.btn_today.clicked.connect(self.set_today_date)
        self.btn_today.setStyleSheet("QPushButton { background: #059669; color: white; border: none; border-radius: 6px; padding: 0 12px; font-size: 11px; font-weight: 600; } QPushButton:hover { background: #059669; }")

        self.btn_yesterday = QPushButton("Yesterday")
        self.btn_yesterday.setMinimumHeight(32)
        self.btn_yesterday.setMinimumWidth(70)
        self.btn_yesterday.clicked.connect(self.set_yesterday_date)
        self.btn_yesterday.setStyleSheet("QPushButton { background: #64748b; color: white; border: none; border-radius: 6px; padding: 0 12px; font-size: 11px; font-weight: 600; } QPushButton:hover { background: #475569; }")

        self.btn_this_week = QPushButton("This Week")
        self.btn_this_week.setMinimumHeight(32)
        self.btn_this_week.setMinimumWidth(70)
        self.btn_this_week.clicked.connect(self.set_this_week_date)
        self.btn_this_week.setStyleSheet("QPushButton { background: #059669; color: white; border: none; border-radius: 6px; padding: 0 12px; font-size: 11px; font-weight: 600; } QPushButton:hover { background: #047857; }")

        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(8)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.btn_today)
        button_layout.addWidget(self.btn_yesterday)
        button_layout.addWidget(self.btn_this_week)
        button_layout.addStretch()

        date_layout.addWidget(button_container, 0, 4, 1, 3)
        date_layout.addWidget(self.search_inp, 1, 4, 1, 3)

        h_layout.addWidget(title)
        h_layout.addStretch()
        h_layout.addLayout(date_layout)
        layout.addLayout(h_layout)
        layout.addWidget(_divider())

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Date & Time", "Invoice", "Token", "Table", "Total", "Payment", "Status", "Action"])
        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background: #f8fafc; color: #64748b;
                font-size: 11px; font-weight: 800; padding: 8px;
                border: none; border-bottom: 2px solid #e2e8f0;
                letter-spacing: 0.5px;
            }
        """)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, 140)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 110)
        layout.addWidget(self.table)

        layout.addWidget(self.pagination)
        self.load_orders()

    def _load_shifts(self):
        self.shift_combo.blockSignals(True)
        self.shift_combo.clear()
        self.shift_combo.addItem("All Shifts", None)
        try:
            shifts = get_all_shifts()
            for shift in shifts:
                shift_id = str(shift.get('_id', ''))
                user = shift.get('user', 'Unknown')
                start = shift.get('start_time', '')
                if isinstance(start, datetime):
                    start_str = start.strftime("%b %d, %H:%M")
                else:
                    start_str = "Unknown"
                display_text = f"Shift by {user} - {start_str}"
                self.shift_combo.addItem(display_text, shift_id)
        except Exception as e:
            print(f"Error loading shifts: {e}")
        self.shift_combo.blockSignals(False)

    def load_orders(self, *args):
        query = {"status": {"$in": ["Completed", "Void", "Refunded"]}}

        selected_shift_id = self.shift_combo.currentData()
        if selected_shift_id:
            query["shift_id"] = selected_shift_id

        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()

        start_qt = self.start_time_edit.time()
        end_qt = self.end_time_edit.time()
        start_time = datetime.min.time().replace(hour=start_qt.hour(), minute=start_qt.minute(), second=start_qt.second())
        end_time = datetime.min.time().replace(hour=end_qt.hour(), minute=end_qt.minute(), second=end_qt.second())

        start_datetime = datetime.combine(start_date, start_time)
        end_datetime = datetime.combine(end_date, end_time)

        if start_datetime > end_datetime:
            start_datetime, end_datetime = end_datetime, start_datetime

        query["created_at"] = {"$gte": start_datetime, "$lte": end_datetime}

        txt = self.search_inp.text().strip()
        if txt:
            query["invoice_no"] = {"$regex": txt, "$options": "i"}
        skip = (self.pagination.current_page - 1) * self.pagination.page_size
        total = orders_col.count_documents(query)
        self.pagination.set_total_records(total)
        orders = list(orders_col.find(query).sort("created_at", -1).skip(skip).limit(self.pagination.page_size))

        self.table.setRowCount(len(orders))
        for r, o in enumerate(orders):
            created = o.get('created_at', '')
            date_str = created.strftime("%b %d, %Y %I:%M %p") if isinstance(created, datetime) else ""
            self.table.setItem(r, 0, QTableWidgetItem(date_str))
            self.table.setItem(r, 1, QTableWidgetItem(o.get('invoice_no', '')))

            token_item = QTableWidgetItem(o.get('token_no', ''))
            token_item.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            token_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 2, token_item)

            self.table.setItem(r, 3, QTableWidgetItem(o.get('table_no', '')))
            self.table.setItem(r, 4, QTableWidgetItem(f"{o.get('grand_total', 0):.2f}"))
            self.table.setItem(r, 5, QTableWidgetItem(o.get('payment_method', '')))

            status = o.get('status', '')
            badge_bg = {"Completed": "#059669", "Void": "#ef4444", "Refunded": "#f59e0b"}.get(status, "#64748b")
            badge = _badge(status, badge_bg)
            bw = QWidget()
            bl = QHBoxLayout(bw)
            bl.setContentsMargins(6, 3, 6, 3)
            bl.addWidget(badge)
            self.table.setCellWidget(r, 6, bw)

            aw = QWidget()
            al = QHBoxLayout(aw)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(6)
            btn_print = _icon_btn('fa5s.print', 'white', '#059669', '#059669', "Reprint", (30, 30))
            btn_print.setStyleSheet("background: #059669; border-radius: 6px;")
            btn_print.clicked.connect(lambda c, order=o: self.reprint_order(order))
            al.addWidget(btn_print)

            btn_refund = _icon_btn('fa5s.undo', 'white', '#ef4444', '#dc2626', "Refund", (30, 30))
            btn_refund.setStyleSheet("background: #ef4444; border-radius: 6px;")
            if status in ["Void", "Refunded"]:
                btn_refund.setEnabled(False)
                btn_refund.setStyleSheet("background: #e2e8f0; border-radius: 6px;")
            else:
                btn_refund.clicked.connect(lambda c, oid=o['_id']: self.process_refund(oid))
            al.addWidget(btn_refund)
            self.table.setCellWidget(r, 7, aw)
            self.table.setRowHeight(r, 46)

    def set_today_date(self):
        today = QDate.currentDate()
        self.start_date_edit.setDate(today)
        self.end_date_edit.setDate(today)
        self.start_time_edit.setTime(QTime(0, 0, 0))
        self.end_time_edit.setTime(QTime(23, 59, 59))

    def set_yesterday_date(self):
        yesterday = QDate.currentDate().addDays(-1)
        self.start_date_edit.setDate(yesterday)
        self.end_date_edit.setDate(yesterday)
        self.start_time_edit.setTime(QTime(0, 0, 0))
        self.end_time_edit.setTime(QTime(23, 59, 59))

    def set_this_week_date(self):
        today = QDate.currentDate()
        monday = today.addDays(-(today.dayOfWeek() - 1))
        self.start_date_edit.setDate(monday)
        self.end_date_edit.setDate(today)
        self.start_time_edit.setTime(QTime(0, 0, 0))
        self.end_time_edit.setTime(QTime(23, 59, 59))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = self.width()
        if width < 1000:
            self.table.setColumnWidth(0, 120)
            self.table.setColumnWidth(7, 90)
        elif width < 1200:
            self.table.setColumnWidth(0, 130)
            self.table.setColumnWidth(7, 100)
        else:
            self.table.setColumnWidth(0, 140)
            self.table.setColumnWidth(7, 110)

    def reprint_order(self, order):
        threading.Thread(target=print_receipt, args=(order,), daemon=True).start()
        QMessageBox.information(self, "Success", "Receipt sent to printer!")

    def process_refund(self, order_id):
        if self.parent_page and not has_permission(self.parent_page.user, "refund_order"):
            QMessageBox.warning(self, "Access Denied", "No permission to refund orders.")
            return
        pin_dlg = PinDialog(self)
        if pin_dlg.exec() != QDialog.DialogCode.Accepted:
            return
        order = orders_col.find_one({"_id": order_id})
        if not order:
            return
        msg = QMessageBox(self)
        msg.setWindowTitle("Refund / Void Order")
        msg.setText(f"Invoice: {order.get('invoice_no')}\nTotal: {order.get('grand_total')}\n\nVoid this order and restore stock?")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            orders_col.update_one({"_id": order_id}, {"$set": {"status": "Refunded", "refunded_at": datetime.now()}})
            actor = "Admin"
            if self.parent_page and self.parent_page.user:
                actor = self.parent_page.user.get("username") or actor
            for item in order.get('items', []):
                qty = item.get('qty', 0)
                if item.get('is_combo'):
                    for sub in item.get('combo_items', []):
                        sub_id = sub.get('id')
                        if sub_id:
                            recipe = get_recipe(sub_id)
                            if recipe:
                                for ing in recipe.get('ingredients', []):
                                    restore_stock(ing['item_name'], ing['quantity'] * sub.get('qty', 1) * qty,
                                                  reason=f"Refund Combo {order.get('invoice_no')}", user=actor)
                else:
                    item_id = item.get('id')
                    if item_id:
                        recipe = get_recipe(item_id)
                        if recipe:
                            for ing in recipe.get('ingredients', []):
                                restore_stock(ing['item_name'], ing['quantity'] * qty,
                                              reason=f"Refund {order.get('invoice_no')}", user=actor)
            QMessageBox.information(self, "Success", "Order Refunded & Stock Restored!")
            self.load_orders()


# ─────────────────────────────────────────────────────────────────────────────
#  RUNNING ORDERS DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class RunningOrdersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_page = parent
        self.setWindowTitle("Running Orders")
        self.setFixedSize(1100, 750)
        self.setStyleSheet(IMPROVED_STYLE)
        self.orders_list = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Running Orders")
        title.setStyleSheet("font-size: 20px; font-weight: 900; color: #1e293b;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Invoice or Table...")
        self.search_input.setFixedWidth(280)
        self.search_input.setFixedHeight(38)
        self.search_input.textChanged.connect(self.update_view)

        btn_refresh = _action_btn("Refresh", "fa5s.sync-alt", "#059669", "#059669", height=38)
        btn_refresh.clicked.connect(self.load_orders)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.search_input)
        header.addWidget(btn_refresh)
        layout.addLayout(header)
        layout.addWidget(_divider())

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Date & Time", "Invoice No", "Token", "Table", "Total", "Status", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background: #f8fafc; color: #64748b;
                font-size: 11px; font-weight: 800; padding: 8px;
                border: none; border-bottom: 2px solid #e2e8f0;
                letter-spacing: 0.5px;
            }
        """)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 290)
        layout.addWidget(self.table)

        footer = QHBoxLayout()
        self.lbl_count = QLabel("Showing 0 orders")
        self.lbl_count.setStyleSheet("color: #64748b; font-weight: 600;")
        btn_close = QPushButton("Close")
        btn_close.setFixedSize(90, 36)
        btn_close.setStyleSheet("background: #f1f5f9; border: 1.5px solid #e2e8f0; border-radius: 8px; color: #64748b; font-weight: 700;")
        btn_close.clicked.connect(self.accept)
        footer.addWidget(self.lbl_count)
        footer.addStretch()
        footer.addWidget(btn_close)
        layout.addLayout(footer)

        self.load_orders()

    def load_orders(self):
        try:
            self.orders_list = list(
                orders_col.find({"status": {"$in": ["Running", "Kitchen"]}}).sort("created_at", -1)
            )
        except Exception:
            self.orders_list = []
        self.update_view()

    def update_view(self):
        text = self.search_input.text().lower().strip()
        filtered = [o for o in self.orders_list if
                    not text or text in str(o.get('invoice_no', '')).lower()
                    or text in str(o.get('table_no', '')).lower()]
        self.populate_table(filtered)

    def populate_table(self, orders):
        self.table.setRowCount(len(orders))
        self.lbl_count.setText(f"Showing {len(orders)} orders")

        for r, order in enumerate(orders):
            created = order.get('created_at', datetime.now())
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created)
                except Exception:
                    pass
            date_str = created.strftime('%Y-%m-%d %H:%M') if isinstance(created, datetime) else str(created)

            self.table.setItem(r, 0, QTableWidgetItem(date_str))

            inv_item = QTableWidgetItem(order.get('invoice_no', 'N/A'))
            inv_item.setForeground(QColor("#059669"))
            self.table.setItem(r, 1, inv_item)

            token_item = QTableWidgetItem(order.get('token_no', ''))
            token_item.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            token_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 2, token_item)

            self.table.setItem(r, 3, QTableWidgetItem(str(order.get('table_no', 'Takeaway'))))

            total_item = QTableWidgetItem(f"Rs {order.get('grand_total', 0):.2f}")
            total_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r, 4, total_item)

            o_status = order.get('status', 'Running')
            if o_status == "Kitchen":
                badge = _badge("In Kitchen", "#f97316", "white", 10)
            else:
                badge = _badge("Running", "#f59e0b", "white", 10)
            bw = QWidget()
            bl = QHBoxLayout(bw)
            bl.setContentsMargins(8, 2, 8, 2)
            bl.addWidget(badge)
            self.table.setCellWidget(r, 5, bw)

            btn_w = QWidget()
            btn_l = QHBoxLayout(btn_w)
            btn_l.setContentsMargins(4, 2, 4, 2)
            btn_l.setSpacing(8)

            btn_kot = QPushButton("KOT")
            btn_kot.setIcon(qta.icon('fa5s.print', color='white'))
            btn_kot.setFixedHeight(32)
            btn_kot.setToolTip("Reprint KOT")
            btn_kot.setStyleSheet("background: #0ea5e9; color: white; border: none; border-radius: 7px; font-weight: 700; padding: 0 8px;")
            btn_kot.clicked.connect(lambda c, o=order: self.reprint_kot(o))

            btn_bill = QPushButton("Bill")
            btn_bill.setIcon(qta.icon('fa5s.file-invoice', color='white'))
            btn_bill.setFixedHeight(32)
            btn_bill.setToolTip("Print Bill")
            btn_bill.setStyleSheet("background: #f59e0b; color: white; border: none; border-radius: 7px; font-weight: 700; padding: 0 8px;")
            btn_bill.clicked.connect(lambda c, o=order: self.reprint_bill(o))

            btn_edit = QPushButton("Edit")
            btn_edit.setIcon(qta.icon('fa5s.edit', color='white'))
            btn_edit.setFixedHeight(32)
            btn_edit.setToolTip("Edit Order")
            btn_edit.setStyleSheet("background: #059669; color: white; border: none; border-radius: 7px; font-weight: 700; padding: 0 8px;")
            btn_edit.clicked.connect(lambda c, o=order: self.edit_order(o))

            btn_l.addWidget(btn_kot)
            btn_l.addWidget(btn_bill)
            btn_l.addWidget(btn_edit)
            self.table.setCellWidget(r, 6, btn_w)
            self.table.setRowHeight(r, 52)

    def reprint_kot(self, order):
        threading.Thread(target=print_kot, args=(order,), daemon=True).start()
        QMessageBox.information(self, "KOT Printed", "KOT sent to printer.")

    def reprint_bill(self, order):
        threading.Thread(target=print_receipt, args=(order,), daemon=True).start()
        QMessageBox.information(self, "Bill Printed", "Bill sent to printer.")

    def edit_order(self, order):
        if self.parent_page:
            self.parent_page.edit_running_order(order)
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  ITEM SPLIT DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class ItemSplitDialog(QDialog):
    def __init__(self, cart_items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Split Bill by Items")
        self.setFixedSize(840, 640)
        self.setStyleSheet(IMPROVED_STYLE)
        self.cart_items = cart_items
        self.parent_page = parent
        self.split_data = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Split Bill by Items")
        header.setStyleSheet("font-size: 20px; font-weight: 900; color: #1e293b;")
        layout.addWidget(header)

        sub = QLabel("Select items to move to the split bill")
        sub.setStyleSheet("font-size: 13px; color: #64748b;")
        layout.addWidget(sub)
        layout.addWidget(_divider())

        content = QHBoxLayout()
        content.setSpacing(16)

        def _make_side(title, color):
            card = QFrame()
            card.setStyleSheet(f"background: white; border-radius: 12px; border: 2px solid {color}33;")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 14, 14, 14)
            header_lbl = QLabel(title)
            header_lbl.setStyleSheet(f"font-size: 14px; font-weight: 900; color: {color}; padding-bottom: 6px; letter-spacing: -0.3px;")
            cl.addWidget(header_lbl)
            tbl = QTableWidget()
            tbl.setColumnCount(3)
            tbl.setHorizontalHeaderLabels(["Item", "Qty", ""])
            tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            tbl.setColumnWidth(1, 48)
            tbl.setColumnWidth(2, 52)
            tbl.verticalHeader().setVisible(False)
            tbl.setShowGrid(False)
            tbl.setAlternatingRowColors(True)
            cl.addWidget(tbl)
            return card, tbl

        main_card, self.table_main = _make_side("Main Order", "#059669")
        split_card, self.table_split = _make_side("Split Bill", "#059669")
        content.addWidget(main_card)
        content.addWidget(split_card)
        layout.addLayout(content)

        totals_row = QHBoxLayout()
        self.lbl_main_total = QLabel("Main: Rs 0.00")
        self.lbl_main_total.setStyleSheet("font-size: 15px; font-weight: 800; color: #059669;")
        self.lbl_split_total = QLabel("Split: Rs 0.00")
        self.lbl_split_total.setStyleSheet("font-size: 15px; font-weight: 800; color: #059669; background: #f0fdf4; padding: 6px 16px; border-radius: 8px;")
        totals_row.addWidget(self.lbl_main_total)
        totals_row.addStretch()
        totals_row.addWidget(self.lbl_split_total)
        layout.addLayout(totals_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(46)
        btn_cancel.setFixedWidth(110)
        btn_cancel.setStyleSheet("background: #f1f5f9; border: 1.5px solid #e2e8f0; border-radius: 10px; color: #64748b; font-weight: 700;")
        btn_cancel.clicked.connect(self.reject)
        btn_pay = _action_btn("Pay Split Bill", "fa5s.receipt", "#059669", "#047857", height=46)
        btn_pay.clicked.connect(self.pay_split)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(btn_pay)
        layout.addLayout(btn_row)

        self.render_tables()

    def render_tables(self):
        self.table_main.setRowCount(0)
        self.table_split.setRowCount(0)
        main_total = split_total = 0

        for row_m, (name, data) in enumerate([x for x in self.cart_items.items() if x[1]['qty'] - self.split_data.get(x[0], 0) > 0]):
            rq = data['qty'] - self.split_data.get(name, 0)
            self.table_main.insertRow(row_m)
            self.table_main.setItem(row_m, 0, QTableWidgetItem(name))
            self.table_main.setItem(row_m, 1, QTableWidgetItem(str(rq)))
            btn = QPushButton("\u2192")
            btn.setFixedSize(38, 26)
            btn.setStyleSheet("background: #059669; color: white; border: none; border-radius: 6px; font-weight: 800;")
            btn.clicked.connect(lambda c, n=name: self.move_to_split(n))
            self.table_main.setCellWidget(row_m, 2, btn)
            main_total += rq * data['price']

        for row_s, (name, qty) in enumerate([(n, q) for n, q in self.split_data.items() if q > 0]):
            price = self.cart_items[name]['price']
            self.table_split.insertRow(row_s)
            self.table_split.setItem(row_s, 0, QTableWidgetItem(name))
            self.table_split.setItem(row_s, 1, QTableWidgetItem(str(qty)))
            btn = QPushButton("\u2190")
            btn.setFixedSize(38, 26)
            btn.setStyleSheet("background: #ef4444; color: white; border: none; border-radius: 6px; font-weight: 800;")
            btn.clicked.connect(lambda c, n=name: self.remove_from_split(n))
            self.table_split.setCellWidget(row_s, 2, btn)
            split_total += qty * price

        self.lbl_main_total.setText(f"Main: Rs {main_total:,.2f}")
        self.lbl_split_total.setText(f"Split: Rs {split_total:,.2f}")

    def move_to_split(self, name):
        current = self.split_data.get(name, 0)
        if current < self.cart_items[name]['qty']:
            self.split_data[name] = current + 1
            self.render_tables()

    def remove_from_split(self, name):
        current = self.split_data.get(name, 0)
        if current > 0:
            self.split_data[name] = current - 1
            self.render_tables()

    def pay_split(self):
        total_to_pay = sum(qty * self.cart_items[n]['price'] for n, qty in self.split_data.items() if qty > 0)
        if total_to_pay <= 0:
            QMessageBox.warning(self, "Error", "No items in split bill!")
            return
        dlg = PaymentDialog(total_to_pay, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.paid_items = self.split_data
            self.accept()
