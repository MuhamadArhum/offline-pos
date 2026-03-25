from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QDoubleSpinBox, 
                             QMessageBox, QTableWidget, QHeaderView, QTableWidgetItem,
                             QDateEdit, QFrame, QFileDialog, QScrollArea, QSizePolicy,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QDate, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QColor, QFont, QPalette
from datetime import datetime, timedelta
import os
from app.core.config import load_config
from app.core.database import expenses_col, orders_col
from app.utils.print_utils import print_dummy_receipt, print_report_v2
from app.services.report_service import export_to_csv
from app.ui.shared_ui import GLOBAL_STYLE

# ─── Shared Style Constants ────────────────────────────────────────────────────

DARK_BG        = "#F0F2F5"
PANEL_BG       = "#FFFFFF"
CARD_BG        = "#F8FAFC"
BORDER_COLOR   = "#E2E8F0"
ACCENT         = "#059669"
ACCENT_HOVER   = "#34d399"
SUCCESS        = "#22c55e"
INFO           = "#14b8a6"
DANGER         = "#ef4444"
TEXT_PRIMARY   = "#1e293b"
TEXT_SECONDARY = "#475569"
FONT_MONO      = "Consolas, 'Courier New', monospace"

BASE_DIALOG_STYLE = f"""
    QDialog {{
        background-color: {DARK_BG};
        color: {TEXT_PRIMARY};
        font-family: 'Segoe UI', sans-serif;
    }}
    QLabel {{
        color: {TEXT_PRIMARY};
        font-size: 13px;
    }}
    QLineEdit, QDoubleSpinBox, QDateEdit, QComboBox {{
        background-color: {CARD_BG};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        min-height: 36px;
        selection-background-color: {ACCENT};
    }}
    QLineEdit:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {{
        border: 1.5px solid {ACCENT};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {CARD_BG};
        color: {TEXT_PRIMARY};
        selection-background-color: {ACCENT};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        padding: 4px;
    }}
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background: {PANEL_BG};
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER_COLOR};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {ACCENT};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
"""

def styled_btn(text, color=ACCENT, text_color=TEXT_PRIMARY):
    """Return a styled QPushButton."""
    btn = QPushButton(text)
    btn.setMinimumHeight(40)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {color};
            color: {text_color};
            border: none;
            border-radius: 8px;
            padding: 8px 20px;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}
        QPushButton:hover {{
            background-color: {_lighten(color)};
        }}
        QPushButton:pressed {{
            background-color: {_darken(color)};
        }}
    """)
    return btn

def _lighten(hex_color, factor=20):
    c = QColor(hex_color)
    return QColor(min(c.red()+factor,255), min(c.green()+factor,255), min(c.blue()+factor,255)).name()

def _darken(hex_color, factor=20):
    c = QColor(hex_color)
    return QColor(max(c.red()-factor,0), max(c.green()-factor,0), max(c.blue()-factor,0)).name()

def section_header(text):
    """Return a styled section header label."""
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(f"""
        QLabel {{
            color: {ACCENT};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            padding: 4px 0px;
        }}
    """)
    return lbl

def divider():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"background-color: {BORDER_COLOR}; max-height: 1px; border: none;")
    return line

# ─── Expense Dialog ────────────────────────────────────────────────────────────

class ExpenseDialog(QDialog):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Add Expense")
        self.setModal(True)
        self.resize(420, 380)
        self.setStyleSheet(GLOBAL_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(6)

        # ── Header ──
        title = QLabel("💸  Add Expense")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {TEXT_PRIMARY}; padding-bottom: 6px;")
        layout.addWidget(title)
        layout.addWidget(divider())
        layout.addSpacing(10)

        # ── Category ──
        layout.addWidget(section_header("Category"))
        self.combo_cat = QComboBox()
        self.combo_cat.addItems(["Groceries", "Utilities", "Maintenance", "Salary", "Petrol", "Misc", "Refund"])
        layout.addWidget(self.combo_cat)
        layout.addSpacing(10)

        # ── Description ──
        layout.addWidget(section_header("Description"))
        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("e.g. Ice, Rider Petrol, Cleaning items")
        layout.addWidget(self.txt_desc)
        layout.addSpacing(10)

        # ── Amount ──
        layout.addWidget(section_header("Amount"))
        self.spin_amt = QDoubleSpinBox()
        self.spin_amt.setRange(0, 1000000)
        self.spin_amt.setPrefix("Rs. ")
        self.spin_amt.setDecimals(2)
        layout.addWidget(self.spin_amt)
        layout.addSpacing(18)

        # ── Save Button ──
        btn_save = styled_btn("  Save Expense", DANGER)
        btn_save.clicked.connect(self.save_expense)
        layout.addWidget(btn_save)

    def save_expense(self):
        # ── Logic unchanged ──
        amt = self.spin_amt.value()
        if amt <= 0:
            QMessageBox.warning(self, "Error", "Enter valid amount!")
            return
        desc = self.txt_desc.text().strip()
        if not desc:
            QMessageBox.warning(self, "Error", "Enter description!")
            return
        expense_data = {
            "category": self.combo_cat.currentText(),
            "description": desc,
            "amount": amt,
            "user": self.user.get('username', 'Staff'),
            "date": datetime.now()
        }
        expenses_col.insert_one(expense_data)
        QMessageBox.information(self, "Success", "Expense Recorded!")
        self.accept()


# ─── Shift Report Dialog ───────────────────────────────────────────────────────

from app.services.shift_service import get_shifts_by_date, get_shift_report
from app.services.report_service import get_shift_report_data

class ShiftReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shift-wise Report")
        self.resize(860, 720)
        self.setStyleSheet(GLOBAL_STYLE)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(14)

        # ── Title ──
        title = QLabel("📊  Shift-wise Report")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {TEXT_PRIMARY};")
        self.layout.addWidget(title)
        self.layout.addWidget(divider())

        # ── Controls Bar ──
        ctrl_card = QFrame()
        ctrl_card.setStyleSheet(f"""
            QFrame {{
                background-color: {PANEL_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 10px;
                padding: 4px;
            }}
        """)
        h = QHBoxLayout(ctrl_card)
        h.setContentsMargins(12, 8, 12, 8)
        h.setSpacing(12)

        date_lbl = QLabel("Date:")
        date_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: 600;")
        h.addWidget(date_lbl)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setFixedWidth(140)
        self.date_edit.dateChanged.connect(self.load_shifts)
        h.addWidget(self.date_edit)

        shift_lbl = QLabel("Shift:")
        shift_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: 600;")
        h.addWidget(shift_lbl)

        self.combo_shifts = QComboBox()
        self.combo_shifts.setMinimumWidth(260)
        self.combo_shifts.currentIndexChanged.connect(self.load_report)
        h.addWidget(self.combo_shifts)
        h.addStretch()

        self.layout.addWidget(ctrl_card)

        # ── Report Area ──
        report_card = QFrame()
        report_card.setStyleSheet(f"""
            QFrame {{
                background-color: {PANEL_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 10px;
            }}
        """)
        report_inner = QVBoxLayout(report_card)
        report_inner.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.lbl_report = QLabel()
        self.lbl_report.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.lbl_report.setStyleSheet(f"""
            QLabel {{
                font-family: {FONT_MONO};
                font-size: 13px;
                color: {TEXT_PRIMARY};
                background-color: transparent;
                padding: 20px 24px;
                line-height: 1.6;
            }}
        """)
        self.lbl_report.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.scroll.setWidget(self.lbl_report)
        report_inner.addWidget(self.scroll)
        self.layout.addWidget(report_card, stretch=1)

        # ── Buttons ──
        btns = QHBoxLayout()
        btns.setSpacing(10)

        btn_print = styled_btn("🖨  Print Report", ACCENT)
        btn_print.clicked.connect(self.print_report)
        btns.addWidget(btn_print)

        btn_export = styled_btn("📄  Export CSV", SUCCESS)
        btn_export.clicked.connect(self.export_report)
        btns.addWidget(btn_export)

        btns.addStretch()

        btn_close = styled_btn("✕  Close", CARD_BG, TEXT_SECONDARY)
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_close)

        self.layout.addLayout(btns)

        self.shifts_data = []
        self.current_report_data = None
        self.load_shifts()

    def load_shifts(self):
        # ── Logic unchanged ──
        selected_date = self.date_edit.date().toPyDate()
        self.shifts_data = get_shifts_by_date(selected_date)

        self.combo_shifts.blockSignals(True)
        self.combo_shifts.clear()

        if not self.shifts_data:
            self.combo_shifts.addItem("No Shifts Found")
            self.lbl_report.setText(f"<span style='color:{TEXT_SECONDARY}'>No shifts found for this date.</span>")
            self.current_report_data = None
        else:
            for s in self.shifts_data:
                start = s['start_time'].strftime("%H:%M")
                end = s['end_time'].strftime("%H:%M") if s.get('end_time') else "Active"
                user = s.get('user', 'Unknown')
                self.combo_shifts.addItem(f"{user} ({start} - {end})", userData=s['_id'])
            self.combo_shifts.setCurrentIndex(0)
            self.load_report()

        self.combo_shifts.blockSignals(False)

    def load_report(self):
        # ── Logic unchanged ──
        if not self.shifts_data: return
        idx = self.combo_shifts.currentIndex()
        if idx < 0: return

        shift_id = self.combo_shifts.currentData()
        data = get_shift_report_data(shift_id)
        if not data:
            self.lbl_report.setText("Error loading data.")
            return

        self.current_report_data = data
        shift = data['shift']

        start_str = shift['start_time'].strftime("%Y-%m-%d %H:%M")
        end_str = shift['end_time'].strftime("%Y-%m-%d %H:%M") if shift.get('end_time') else "ACTIVE"

        top_items_str = ""
        for item in data.get('top_items', [])[:10]:
            top_items_str += f"  {item['name']:<22} {item['qty']:>4}   Rs.{item['total']:>10,.0f}\n"

        expenses_str = ""
        for exp in data.get('expenses', []):
            expenses_str += f"  {exp.get('category','Misc'):<18} Rs.{exp.get('amount',0):>10,.0f}\n"

        sep  = "  " + "─" * 52
        sep2 = "  " + "═" * 52

        report_text = (
            f"\n"
            f"{sep2}\n"
            f"              ◆  SHIFT REPORT  ◆\n"
            f"{sep2}\n\n"
            f"  User     :  {shift.get('user')}\n"
            f"  Start    :  {start_str}\n"
            f"  End      :  {end_str}\n"
            f"  Status   :  {shift.get('status')}\n\n"
            f"{sep}\n\n"
            f"  SALES SUMMARY\n"
            f"{sep}\n"
            f"  Total Sales       Rs. {data['total_sales']:>12,.2f}\n"
            f"  Cash Sales        Rs. {data['cash_sales']:>12,.2f}\n"
            f"  Card Sales        Rs. {data['card_sales']:>12,.2f}\n"
            f"  Online Sales      Rs. {data.get('online_sales',0):>12,.2f}\n\n"
            f"{sep}\n\n"
            f"  CASH DRAWER\n"
            f"{sep}\n"
            f"  Opening Cash      Rs. {shift.get('opening_cash',0):>12,.2f}\n"
            f"  + Cash Sales      Rs. {data['cash_sales']:>12,.2f}\n"
            f"  - Expenses        Rs. {data['total_expenses']:>12,.2f}\n"
            f"{sep}\n"
            f"  Expected Cash     Rs. {data['net_cash']:>12,.2f}\n"
            f"  Actual Cash       Rs. {shift.get('closing_cash',0):>12,.2f}\n"
            f"  Difference        Rs. {shift.get('cash_diff',0):>12,.2f}\n\n"
            f"{sep}\n\n"
            f"  TOP ITEMS SOLD\n"
            f"{sep}\n"
            f"  {'Item':<22} {'Qty':>4}   {'Total':>13}\n"
            f"  {'─'*44}\n"
            f"{top_items_str}\n"
            f"{sep}\n\n"
            f"  EXPENSES\n"
            f"{sep}\n"
            f"  {'Category':<18} {'Amount':>13}\n"
            f"  {'─'*34}\n"
            f"{expenses_str}\n"
            f"  Total Expenses    Rs. {data['total_expenses']:>12,.2f}\n"
            f"{sep2}\n"
        )

        self.lbl_report.setText(report_text)

    def print_report(self):
        # ── Logic unchanged ──
        if not self.current_report_data: return
        report_dict = {
            "title": "SHIFT REPORT",
            "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "content": self.lbl_report.text()
        }
        print_report_v2(report_dict)

    def export_report(self):
        # ── Logic unchanged ──
        if not self.current_report_data: return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Shift",
            f"Shift-{datetime.now().strftime('%Y%m%d%H%M')}.csv",
            "CSV Files (*.csv)"
        )
        if not filename: return
        sales = self.current_report_data['sales']
        data = []
        for s in sales:
            data.append({
                "Invoice": s.get('invoice_no'),
                "Total": s.get('grand_total'),
                "Method": s.get('payment_method'),
                "Time": s.get('created_at')
            })
        success, msg = export_to_csv(data, filename)
        if success:
            QMessageBox.information(self, "Success", f"Shift Sales Exported!\n{msg}")
        else:
            QMessageBox.warning(self, "Export Failed", msg)


# ─── Day Close Dialog ──────────────────────────────────────────────────────────

class DayCloseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Day Close / Z-Report")
        self.resize(640, 740)
        self.setStyleSheet(GLOBAL_STYLE)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(14)

        # ── Title ──
        title = QLabel("📋  Day Close — Z Report")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {TEXT_PRIMARY};")
        self.layout.addWidget(title)
        self.layout.addWidget(divider())

        # ── Controls Bar ──
        ctrl_card = QFrame()
        ctrl_card.setStyleSheet(f"""
            QFrame {{
                background-color: {PANEL_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 10px;
            }}
        """)
        h = QHBoxLayout(ctrl_card)
        h.setContentsMargins(12, 8, 12, 8)
        h.setSpacing(12)

        date_lbl = QLabel("Date:")
        date_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: 600;")
        h.addWidget(date_lbl)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setFixedWidth(150)
        self.date_edit.dateChanged.connect(self.load_report)
        h.addWidget(self.date_edit)

        h.addStretch()

        btn_refresh = styled_btn("↻  Refresh", CARD_BG, TEXT_PRIMARY)
        btn_refresh.setFixedWidth(110)
        btn_refresh.clicked.connect(self.load_report)
        h.addWidget(btn_refresh)

        self.layout.addWidget(ctrl_card)

        # ── Report Area ──
        report_card = QFrame()
        report_card.setStyleSheet(f"""
            QFrame {{
                background-color: {PANEL_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 10px;
            }}
        """)
        report_inner = QVBoxLayout(report_card)
        report_inner.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.lbl_report = QLabel()
        self.lbl_report.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.lbl_report.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_report.setStyleSheet(f"""
            QLabel {{
                font-family: {FONT_MONO};
                font-size: 13px;
                color: {TEXT_PRIMARY};
                background-color: transparent;
                padding: 20px 24px;
                line-height: 1.7;
            }}
        """)
        scroll.setWidget(self.lbl_report)
        report_inner.addWidget(scroll)
        self.layout.addWidget(report_card, stretch=1)

        # ── Buttons ──
        btns = QHBoxLayout()
        btns.setSpacing(10)

        btn_print = styled_btn("🖨  Print Report", SUCCESS)
        btn_print.clicked.connect(self.print_report)
        btns.addWidget(btn_print)

        btn_export = styled_btn("📄  Export CSV", INFO)
        btn_export.clicked.connect(self.export_report)
        btns.addWidget(btn_export)

        btns.addStretch()

        btn_close = styled_btn("✕  Close", CARD_BG, TEXT_SECONDARY)
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_close)

        self.layout.addLayout(btns)

        self.load_report()

    def load_report(self):
        # ── Logic unchanged ──
        self.setCursor(Qt.CursorShape.WaitCursor)
        try:
            selected_date = self.date_edit.date().toPyDate()
            start = datetime.combine(selected_date, datetime.min.time())
            end   = datetime.combine(selected_date, datetime.max.time())

            self.sales = list(orders_col.find({
                "created_at": {"$gte": start, "$lte": end},
                "status": "Completed"
            }))
            sales = self.sales

            total_sales = cash_sales = card_sales = online_sales = 0

            for sale in sales:
                total = sale.get('grand_total', 0)
                total_sales += total
                payments = sale.get('payments', [])
                if payments:
                    for p in payments:
                        method = p.get('method', 'Cash')
                        amt    = p.get('amount', 0)
                        if method == 'Cash':   cash_sales   += amt
                        elif method == 'Card': card_sales   += amt
                        else:                  online_sales += amt
                else:
                    method = sale.get('payment_method', 'Cash')
                    if method == 'Cash':   cash_sales   += total
                    elif method == 'Card': card_sales   += total
                    else:                  online_sales += total

            expenses = list(expenses_col.find({
                "date": {"$gte": start, "$lte": end}
            }))
            total_expense = sum(e.get('amount', 0) for e in expenses)
            cash_in_hand  = cash_sales - total_expense

            sep  = "  " + "─" * 48
            sep2 = "  " + "═" * 48

            self.report_text = (
                f"\n"
                f"{sep2}\n"
                f"            ◆  DAILY Z-REPORT  ◆\n"
                f"{sep2}\n\n"
                f"  Date           :  {selected_date.strftime('%Y-%m-%d')}\n\n"
                f"{sep}\n\n"
                f"  TOTAL SALES         Rs. {total_sales:>12,.2f}\n\n"
                f"  BREAKDOWN\n"
                f"{sep}\n"
                f"  Cash Sales          Rs. {cash_sales:>12,.2f}\n"
                f"  Card Sales          Rs. {card_sales:>12,.2f}\n"
                f"  Online Sales        Rs. {online_sales:>12,.2f}\n\n"
                f"{sep}\n\n"
                f"  TOTAL EXPENSES      Rs. {total_expense:>12,.2f}\n\n"
                f"{sep}\n\n"
                f"  NET CASH IN HAND    Rs. {cash_in_hand:>12,.2f}\n\n"
                f"{sep}\n\n"
                f"  Total Orders   :  {len(sales)}\n"
                f"  Total Expenses :  {len(expenses)}\n\n"
                f"{sep2}\n\n"
                f"  Generated at   :  {datetime.now().strftime('%H:%M:%S')}\n"
            )

            self.lbl_report.setText(self.report_text)
        finally:
            self.unsetCursor()

    def print_report(self):
        # ── Logic unchanged ──
        report_data = {
            "title": "DAILY Z-REPORT",
            "date": self.date_edit.date().toPyDate().strftime('%Y-%m-%d'),
            "content": self.report_text
        }
        success, msg = print_report_v2(report_data)
        if success:
            QMessageBox.information(self, "Success", f"Report printed successfully!\n{msg}")
        else:
            QMessageBox.warning(self, "Print Error", f"Failed to print report: {msg}")

    def export_report(self):
        # ── Logic unchanged ──
        if not hasattr(self, 'sales') or not self.sales:
            QMessageBox.warning(self, "Export", "No sales data to export.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Report",
            f"Sales-{self.date_edit.date().toString('yyyy-MM-dd')}.csv",
            "CSV Files (*.csv)"
        )
        if not filename: return

        data = []
        for s in self.sales:
            items_str = ", ".join([f"{i.get('qty',0)}x {i.get('name','')}" for i in s.get('items', [])])
            created = s.get('created_at')
            time_str = created.strftime('%H:%M:%S') if isinstance(created, datetime) else str(created)
            data.append({
                "Invoice": s.get('invoice_no', ''),
                "Time":    time_str,
                "Total":   s.get('grand_total', 0),
                "Method":  s.get('payment_method', ''),
                "Items":   items_str
            })

        success, msg = export_to_csv(data, filename)
        if success:
            QMessageBox.information(self, "Success", f"Exported successfully to:\n{filename}")
        else:
            QMessageBox.warning(self, "Error", f"Export failed: {msg}")