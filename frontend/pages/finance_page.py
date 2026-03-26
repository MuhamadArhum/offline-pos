from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QPushButton, QTableWidget, QHeaderView,
                             QLineEdit, QComboBox, QMessageBox, QTabWidget, QSpinBox,
                             QDoubleSpinBox, QDateEdit, QScrollArea, QTableWidgetItem,
                             QSizePolicy, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QDate, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont
import qtawesome as qta
from datetime import datetime
from backend.services.report_service import (
    today_sales, sales_by_date, get_item_sales_report, get_category_sales_report,
    get_low_stock_report, get_hourly_sales_report, get_payment_method_report,
    get_staff_performance_report, get_profit_loss_report, get_stock_valuation,
    get_dead_stock, get_theoretical_usage, get_void_orders, get_discount_report,
    get_audit_logs_report, get_sales_trend
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib
from backend.services.wastage_service import get_wastage_summary, get_top_wasted_items
from backend.core.database import expenses_col
from backend.services.shift_service import get_active_shift, update_shift_totals
from frontend.components.flow_layout import FlowLayout
from frontend.components.pagination import PaginationControl
from frontend.shared_ui import GLOBAL_STYLE, page_header

# ─────────────────────────────────────────────────────────────────────────────
#  DESIGN TOKENS  (Emerald-based, consistent across all pages)
# ─────────────────────────────────────────────────────────────────────────────
_PRIMARY    = "#059669"  # Emerald Green
_PRIMARY_DK = "#047857"
_PRIMARY_LT = "#ECFDF5"
_SUCCESS    = "#22c55e"
_SUCCESS_LT = "#DCFCE7"
_DANGER     = "#EF4444"
_DANGER_LT  = "#FEE2E2"
_WARNING    = "#F59E0B"
_WARNING_LT = "#FEF3C7"
_INFO       = "#14B8A6"
_INFO_LT    = "#CCFBF1"
_DARK1      = "#0F172A"
_DARK2      = "#1E293B"
_TEXT_PRI   = "#1E293B"
_TEXT_SEC   = "#64748B"
_TEXT_HINT  = "#94A3B8"
_BG         = "#F0F2F5"
_SURFACE    = "#FFFFFF"
_BORDER     = "#E2E8F0"
_DIVIDER    = "#F1F5F9"

# Keep legacy names for minimal disruption to original logic
DARK_BG        = _BG
PANEL_BG       = _SURFACE
CARD_BG        = _DIVIDER
BORDER_COLOR   = _BORDER
ACCENT         = _PRIMARY
SUCCESS        = _SUCCESS
INFO           = _INFO
DANGER         = _DANGER
WARNING        = _WARNING
TEXT_PRIMARY   = _TEXT_PRI
TEXT_SECONDARY = _TEXT_SEC
TEXT_MUTED     = _TEXT_HINT

# ─────────────────────────────────────────────────────────────────────────────
#  STYLESHEETS
# ─────────────────────────────────────────────────────────────────────────────
TAB_STYLE = f"""
QTabWidget::pane {{ border: none; background: {_BG}; }}
QTabBar::tab {{
    background: transparent;
    color: {_TEXT_SEC};
    padding: 12px 24px;
    font-size: 13px;
    font-weight: 700;
    border: none;
    border-bottom: 2px solid transparent;
    letter-spacing: 0.3px;
    min-width: 100px;
}}
QTabBar::tab:hover:!selected {{
    color: {_TEXT_PRI};
    background: rgba(5,150,105,0.06);
    border-radius: 8px 8px 0 0;
}}
QTabBar::tab:selected {{
    color: {_PRIMARY};
    border-bottom: 2px solid {_PRIMARY};
    background: transparent;
}}
"""

TABLE_STYLE = f"""
QTableWidget {{
    background: {_SURFACE};
    color: {_TEXT_PRI};
    border: none;
    border-radius: 12px;
    gridline-color: transparent;
    font-size: 13px;
    alternate-background-color: #FAFBFC;
    selection-background-color: {_PRIMARY_LT};
    selection-color: {_PRIMARY_DK};
    outline: none;
}}
QTableWidget::item {{
    padding: 12px 16px;
    border: none;
    border-bottom: 1px solid {_DIVIDER};
}}
QTableWidget::item:selected {{
    background: {_PRIMARY_LT};
    color: {_PRIMARY_DK};
}}
QTableWidget::item:hover {{
    background: #F8FAFC;
}}
QHeaderView::section {{
    background: {_DIVIDER};
    color: {_TEXT_SEC};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    padding: 14px 16px;
    border: none;
    border-bottom: 2px solid {_BORDER};
}}
QHeaderView::section:hover {{
    background: {_PRIMARY_LT};
    color: {_PRIMARY};
}}
QHeaderView {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; border-radius: 5px; }}
QScrollBar::handle:vertical {{ background: #CBD5E1; border-radius: 5px; min-height: 40px; }}
QScrollBar::handle:vertical:hover {{ background: #94A3B8; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; border-radius: 5px; }}
QScrollBar::handle:horizontal {{ background: #CBD5E1; border-radius: 5px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
"""

WIDGET_STYLE = f"""
QLineEdit, QDoubleSpinBox, QDateEdit, QComboBox, QSpinBox {{
    background: {_SURFACE};
    color: {_TEXT_PRI};
    border: 1.5px solid {_BORDER};
    border-radius: 10px;
    padding: 0 14px;
    font-size: 13px;
    font-weight: 600;
    min-height: 40px;
    selection-background-color: {_PRIMARY_LT};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QDateEdit:focus,
QComboBox:focus, QSpinBox:focus {{
    border: 2px solid {_PRIMARY};
    background: {_PRIMARY_LT};
    padding: 0 13px;
}}
QComboBox::drop-down {{ border: none; width: 32px; }}
QComboBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {_TEXT_SEC};
    margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background: {_SURFACE};
    color: {_TEXT_PRI};
    selection-background-color: {_PRIMARY_LT};
    selection-color: {_PRIMARY_DK};
    border: 1px solid {_BORDER};
    border-radius: 10px;
    padding: 6px;
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER WIDGETS  (same API as original, improved styling)
# ─────────────────────────────────────────────────────────────────────────────
def _lighten(hex_color, factor=20):
    c = QColor(hex_color)
    return QColor(min(c.red()+factor,255), min(c.green()+factor,255), min(c.blue()+factor,255)).name()

def _darken(hex_color, factor=20):
    c = QColor(hex_color)
    return QColor(max(c.red()-factor,0), max(c.green()-factor,0), max(c.blue()-factor,0)).name()

def styled_btn(text, color=_PRIMARY, text_color="white", icon=None):
    btn = QPushButton(text)
    if icon:
        btn.setIcon(icon)
    btn.setMinimumHeight(40)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"QPushButton {{ background:{color}; color:{text_color}; border:none; border-radius:9px;"
        f" padding:0 18px; font-size:13px; font-weight:700; letter-spacing:0.2px; }}"
        f"QPushButton:hover {{ background:{_darken(color, 15)}; }}"
        f"QPushButton:pressed {{ background:{_darken(color, 28)}; }}"
    )
    return btn

def card_frame(min_width=None):
    f = QFrame()
    f.setStyleSheet(
        f"QFrame {{ background:{_SURFACE}; border:1.5px solid {_BORDER}; border-radius:14px; }}"
    )
    if min_width:
        f.setMinimumWidth(min_width)
    return f

def section_label(text):
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color:{_TEXT_HINT}; font-size:10px; font-weight:800; letter-spacing:0.8px;"
        f" padding-bottom:2px; border:none; background:transparent;"
    )
    return lbl

def divider():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"background:{_BORDER}; max-height:1px; border:none;")
    return line

def total_label(text="Total: Rs. 0.00"):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size:16px; font-weight:800; color:{_PRIMARY};"
        f" padding:6px 0; letter-spacing:-0.3px; border:none; background:transparent;"
    )
    return lbl

def _ctrl_label(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color:{_TEXT_SEC}; font-weight:700; font-size:11px; letter-spacing:0.3px;"
        f" border:none; background:transparent;"
    )
    return lbl


# ─────────────────────────────────────────────────────────────────────────────
#  FINANCE PAGE  — same structure, improved chrome
# ─────────────────────────────────────────────────────────────────────────────
class FinancePage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet(GLOBAL_STYLE + TAB_STYLE + WIDGET_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(
            page_header("Finance & Reports",
                        subtitle="Text reports · Visual analytics · Expenses")
        )

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_STYLE)

        self.reports_tab  = ReportsTab()
        self.visuals_tab  = VisualsTab()
        self.expenses_tab = ExpensesTab(user)

        self.tabs.addTab(self.reports_tab,
                         qta.icon('fa5s.table',      color=_PRIMARY), "  Text Reports  ")
        self.tabs.addTab(self.visuals_tab,
                         qta.icon('fa5s.chart-line', color=_SUCCESS), "  Visual Analytics  ")
        self.tabs.addTab(self.expenses_tab,
                         qta.icon('fa5s.receipt',    color=_WARNING), "  Expenses  ")

        layout.addWidget(self.tabs)


# ─────────────────────────────────────────────────────────────────────────────
#  REPORTS TAB  — all original logic, improved layout
# ─────────────────────────────────────────────────────────────────────────────
class ReportsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{_BG};" + WIDGET_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # ── Controls bar ─────────────────────────────────────────────────
        ctrl = QFrame()
        ctrl.setStyleSheet(
            f"QFrame {{ background:{_SURFACE}; border-radius:12px; border:1.5px solid {_BORDER}; }}"
        )
        cl = QHBoxLayout(ctrl); cl.setContentsMargins(16, 10, 16, 10); cl.setSpacing(10)

        cl.addWidget(_ctrl_label("REPORT:"))
        self.combo_type = QComboBox()
        self.combo_type.setMinimumWidth(190)
        self.combo_type.addItems([
            "Sales List", "Item Sales", "Category Sales", "Low Stock",
            "Wastage Report", "Hourly Sales", "Payment Methods",
            "Staff Performance", "Profit & Loss",
            "Stock Valuation", "Dead Stock", "Theoretical Usage",
            "Void Orders", "Discount Report", "Audit Logs"
        ])
        self.combo_type.currentIndexChanged.connect(self.load_data)
        cl.addWidget(self.combo_type)

        # Separator
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1); sep.setStyleSheet(f"background:{_BORDER}; border:none;")
        cl.addWidget(sep)

        cl.addWidget(_ctrl_label("FROM:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setFixedWidth(132)
        cl.addWidget(self.start_date)

        cl.addWidget(_ctrl_label("TO:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setFixedWidth(132)
        cl.addWidget(self.end_date)

        cl.addSpacing(4)

        btn_filter = styled_btn("  Filter", _PRIMARY,
                                icon=qta.icon('fa5s.filter', color='white'))
        btn_filter.setFixedHeight(38); btn_filter.clicked.connect(self.load_data)
        cl.addWidget(btn_filter)

        btn_export = styled_btn("  Export CSV", _SUCCESS,
                                icon=qta.icon('fa5s.file-csv', color='white'))
        btn_export.setFixedHeight(38); btn_export.clicked.connect(self.export_csv)
        cl.addWidget(btn_export)

        cl.addStretch()
        layout.addWidget(ctrl)

        # ── Table card ────────────────────────────────────────────────────
        tbl_card = QFrame()
        tbl_card.setStyleSheet(
            f"QFrame {{ background:{_SURFACE}; border-radius:14px; border:1.5px solid {_BORDER}; }}"
        )
        tcl = QVBoxLayout(tbl_card); tcl.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tcl.addWidget(self.table)
        layout.addWidget(tbl_card, stretch=1)

        # ── Summary footer ────────────────────────────────────────────────
        footer_row = QHBoxLayout()
        footer_row.addStretch()
        self.lbl_total = total_label("Total: Rs. 0.00")
        footer_row.addWidget(self.lbl_total)
        layout.addLayout(footer_row)

        self.load_data()

    # ── ALL ORIGINAL LOGIC BELOW — 100% unchanged ─────────────────────────
    def load_data(self):
        start    = self.start_date.dateTime().toPyDateTime()
        end      = self.end_date.dateTime().addDays(1).toPyDateTime()
        rtype    = self.combo_type.currentText()
        total_val = 0

        self.table.setRowCount(0)

        def add_row(*values, colors=None):
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if colors and col < len(colors) and colors[col]:
                    item.setForeground(QColor(colors[col]))
                self.table.setItem(row, col, item)

        if rtype == "Sales List":
            self.table.setColumnCount(8)
            self.table.setHorizontalHeaderLabels([
                "Date", "Invoice", "Type",
                "Subtotal", "Svc Chg", "Tax", "Grand Total", "Payment"
            ])
            for sale in sales_by_date(start, end):
                subtotal   = sale.get('subtotal', 0)
                svc_chg    = sale.get('service_charge', 0)
                tax        = sale.get('tax', 0)
                grand      = sale.get('grand_total', 0)
                row = self.table.rowCount()
                self.table.insertRow(row)
                cells = [
                    sale['timestamp'].strftime("%Y-%m-%d %H:%M"),
                    sale.get('invoice_no', ''),
                    sale.get('order_type', ''),
                    f"Rs. {subtotal:,.2f}",
                    f"Rs. {svc_chg:,.2f}",
                    f"Rs. {tax:,.2f}",
                    f"Rs. {grand:,.2f}",
                    sale.get('payment_method', ''),
                ]
                for col, val in enumerate(cells):
                    item = QTableWidgetItem(str(val))
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if col == 6:  # Grand Total bold green
                        item.setForeground(QColor(_SUCCESS))
                        f = QFont(); f.setBold(True); item.setFont(f)
                    elif col in (3, 4, 5):  # financial cols muted
                        item.setForeground(QColor(_TEXT_SEC))
                    self.table.setItem(row, col, item)
                total_val += grand

        elif rtype == "Item Sales":
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Item Name", "Category", "Quantity Sold", "Total Revenue"])
            for item in get_item_sales_report(start, end):
                add_row(item['_id'], item.get('category','N/A'), item['qty'], f"Rs. {item['total']:.2f}")
                total_val += item.get('total', 0)

        elif rtype == "Category Sales":
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["Category", "Qty Sold", "Total Revenue"])
            for cat in get_category_sales_report(start, end):
                add_row(cat['_id'], cat['total_qty'], f"Rs. {cat['total_revenue']:.2f}")
                total_val += cat.get('total_revenue', 0)

        elif rtype == "Low Stock":
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Item Name", "Current Qty", "Threshold", "Unit"])
            items = get_low_stock_report()
            for item in items:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(item.get('item_name',''))))
                qty_item = QTableWidgetItem(str(item.get('qty', 0)))
                qty_item.setForeground(QColor(DANGER))
                qty_item.setFlags(qty_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 1, qty_item)
                self.table.setItem(row, 2, QTableWidgetItem(str(item.get('threshold', 0))))
                self.table.setItem(row, 3, QTableWidgetItem(str(item.get('unit', ''))))
            self.lbl_total.setText(f"Low Stock Items: {len(items)}")
            return

        elif rtype == "Wastage Report":
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Item Name", "Total Qty Wasted", "Total Cost Loss", "Count"])
            delta = end - start
            days  = max(1, delta.days)
            for w in get_top_wasted_items(limit=100, days=days):
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(w['_id'])))
                self.table.setItem(row, 1, QTableWidgetItem(str(w['total_quantity'])))
                cost_item = QTableWidgetItem(f"Rs. {w['total_cost']:.2f}")
                cost_item.setForeground(QColor(DANGER))
                cost_item.setFlags(cost_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 2, cost_item)
                self.table.setItem(row, 3, QTableWidgetItem(str(w['count'])))
                total_val += w.get('total_cost', 0)

        elif rtype == "Hourly Sales":
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["Hour (24h)", "Transactions", "Total Revenue"])
            for h in get_hourly_sales_report(start, end):
                add_row(f"{h['_id']}:00 - {h['_id']+1}:00", h['count'], f"Rs. {h['total_revenue']:.2f}")
                total_val += h.get('total_revenue', 0)

        elif rtype == "Payment Methods":
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["Method", "Transactions", "Total Revenue"])
            for m in get_payment_method_report(start, end):
                add_row(m['_id'], m['count'], f"Rs. {m['total_revenue']:.2f}")
                total_val += m.get('total_revenue', 0)

        elif rtype == "Staff Performance":
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["Staff Name", "Orders Processed", "Total Sales"])
            for s in get_staff_performance_report(start, end):
                name = str(s['_id']) if s['_id'] else "Unknown"
                add_row(name, s['count'], f"Rs. {s['total_revenue']:.2f}")
                total_val += s.get('total_revenue', 0)

        elif rtype == "Profit & Loss":
            self.table.setColumnCount(2)
            self.table.setHorizontalHeaderLabels(["Metric", "Value"])
            pnl = get_profit_loss_report(start, end)
            metrics = [
                ("Total Revenue",             pnl['revenue'],    _SUCCESS),
                ("Cost of Goods Sold (COGS)", -pnl['cogs'],      _DANGER),
                ("Wastage Cost",              -pnl['wastage'],   _DANGER),
                ("Operating Expenses",        -pnl['expenses'],  _DANGER),
                ("NET PROFIT",                 pnl['net_profit'], _PRIMARY),
            ]
            for name, val, color in metrics:
                row = self.table.rowCount()
                self.table.insertRow(row)
                n_item = QTableWidgetItem(name)
                v_item = QTableWidgetItem(f"Rs. {val:,.2f}")
                if name == "NET PROFIT":
                    font = n_item.font(); font.setBold(True)
                    n_item.setFont(font); v_item.setFont(font)
                n_item.setFlags(n_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                v_item.setForeground(QColor(color))
                v_item.setFlags(v_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 0, n_item)
                self.table.setItem(row, 1, v_item)
            self.lbl_total.setText(f"Net Profit: Rs. {pnl['net_profit']:,.2f}")
            return

        elif rtype == "Stock Valuation":
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Item Name", "Qty", "Cost", "Total Value"])
            for item in get_stock_valuation():
                add_row(item['item_name'], item['qty'], f"Rs. {item['cost_per_unit']:.2f}", f"Rs. {item['total_value']:.2f}")
                total_val += item['total_value']

        elif rtype == "Dead Stock":
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Item Name", "Last Sold", "Stock", "Value Tied Up"])
            for item in get_dead_stock(days=30):
                add_row(item['item_name'], item['last_sold'], item['current_stock'], f"Rs. {item['value']:.2f}")
                total_val += item['value']

        elif rtype == "Theoretical Usage":
            self.table.setColumnCount(2)
            self.table.setHorizontalHeaderLabels(["Ingredient", "Theoretical Usage"])
            for item in get_theoretical_usage(start, end):
                add_row(item['ingredient'], f"{item['theoretical_usage']:.2f}")

        elif rtype == "Void Orders":
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Date", "Order #", "Amount", "Reason"])
            for item in get_void_orders(start, end):
                add_row(
                    str(item.get('updated_at','')), str(item.get('order_no','')),
                    f"Rs. {item.get('grand_total',0):.2f}", str(item.get('void_reason','Cancelled'))
                )
                total_val += item.get('grand_total', 0)

        elif rtype == "Discount Report":
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Date", "Order #", "Discount", "Total"])
            for item in get_discount_report(start, end):
                disc = item.get('discount_amount', 0) or item.get('discount', 0)
                add_row(
                    str(item.get('updated_at','')), str(item.get('order_no','')),
                    f"Rs. {disc:.2f}", f"Rs. {item.get('grand_total',0):.2f}"
                )
                total_val += disc

        elif rtype == "Audit Logs":
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Date", "User", "Action", "Details"])
            for item in get_audit_logs_report(start, end):
                add_row(
                    str(item.get('timestamp','')), str(item.get('username','Unknown')),
                    str(item.get('action','')), str(item.get('details',''))
                )

        self.lbl_total.setText(f"Total: Rs. {total_val:,.2f}")

    def export_csv(self):
        import pandas as pd
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export Report", "report.csv", "CSV Files (*.csv)")
        if not path: return
        try:
            rows    = self.table.rowCount()
            cols    = self.table.columnCount()
            headers = [self.table.horizontalHeaderItem(c).text() for c in range(cols)]
            data    = []
            for r in range(rows):
                row_data = {}
                for c in range(cols):
                    item = self.table.item(r, c)
                    row_data[headers[c]] = item.text() if item else ""
                data.append(row_data)
            import pandas as pd
            pd.DataFrame(data).to_csv(path, index=False)
            QMessageBox.information(self, "Success", "Report exported successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
#  EXPENSES TAB  — original logic, improved layout
# ─────────────────────────────────────────────────────────────────────────────
class ExpensesTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet(f"background:{_BG};" + WIDGET_STYLE)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(16)

        # ── Two-column layout (form left, list right) ─────────────────────
        cols = QHBoxLayout(); cols.setSpacing(16)

        # ── LEFT: Add Expense form ────────────────────────────────────────
        form_card = QFrame()
        form_card.setMinimumWidth(260)
        form_card.setMaximumWidth(360)
        form_card.setStyleSheet(
            f"QFrame {{ background:{_SURFACE}; border-radius:14px; border:1.5px solid {_BORDER}; }}"
        )
        fl = QVBoxLayout(form_card); fl.setContentsMargins(22, 20, 22, 22); fl.setSpacing(0)

        # Form header
        fhdr = QFrame(); fhdr.setFixedHeight(50)
        fhdr.setStyleSheet(
            f"QFrame {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {_DARK1},stop:1 {_DARK2}); border-radius:10px; border:none; }}"
        )
        fhl = QHBoxLayout(fhdr); fhl.setContentsMargins(14, 0, 14, 0); fhl.setSpacing(8)
        ico = QLabel(); ico.setPixmap(qta.icon('fa5s.plus-circle', color=_PRIMARY).pixmap(20, 20))
        ttl = QLabel("Add Expense")
        ttl.setStyleSheet("color:white; font-size:15px; font-weight:900; border:none; background:transparent;")
        fhl.addWidget(ico); fhl.addWidget(ttl); fhl.addStretch()
        fl.addWidget(fhdr)
        fl.addSpacing(16)

        def _flbl(text):
            l = section_label(text); fl.addWidget(l); fl.addSpacing(4)

        _flbl("DESCRIPTION")
        self.desc_input = QLineEdit()
        self.desc_input.setFixedHeight(40)
        self.desc_input.setPlaceholderText("e.g. Office supplies, electricity...")
        fl.addWidget(self.desc_input)
        fl.addSpacing(12)

        _flbl("CATEGORY")
        self.cat_input = QComboBox()
        self.cat_input.setFixedHeight(40)
        self.cat_input.addItems(["Supplies", "Utilities", "Maintenance", "Staff", "Other"])
        fl.addWidget(self.cat_input)
        fl.addSpacing(12)

        _flbl("AMOUNT")
        self.amt_input = QDoubleSpinBox()
        self.amt_input.setFixedHeight(40)
        self.amt_input.setRange(0, 100_000)
        self.amt_input.setPrefix("Rs. ")
        fl.addWidget(self.amt_input)
        fl.addSpacing(20)

        add_btn = QPushButton("  Save Expense")
        add_btn.setIcon(qta.icon('fa5s.save', color='white'))
        add_btn.setFixedHeight(44); add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {_PRIMARY},stop:1 #818CF8); color:white; border:none; border-radius:10px;"
            f" font-size:13px; font-weight:800; }}"
            f"QPushButton:hover {{ background:{_PRIMARY_DK}; }}"
        )
        add_btn.clicked.connect(self.save_expense)
        fl.addWidget(add_btn)
        fl.addStretch()
        cols.addWidget(form_card)

        # ── RIGHT: Expenses list ──────────────────────────────────────────
        list_card = QFrame()
        list_card.setStyleSheet(
            f"QFrame {{ background:{_SURFACE}; border-radius:14px; border:1.5px solid {_BORDER}; }}"
        )
        ll = QVBoxLayout(list_card); ll.setContentsMargins(0, 0, 0, 0); ll.setSpacing(0)

        # List header
        lhdr = QFrame(); lhdr.setFixedHeight(52)
        lhdr.setStyleSheet(
            f"QFrame {{ background:{_BG}; border-radius:14px 14px 0 0;"
            f" border-bottom:1.5px solid {_BORDER}; border-top:none; border-left:none; border-right:none; }}"
        )
        lhl = QHBoxLayout(lhdr); lhl.setContentsMargins(18, 0, 18, 0); lhl.setSpacing(10)
        lico = QLabel(); lico.setPixmap(qta.icon('fa5s.receipt', color=_WARNING).pixmap(18, 18))
        ltitle = QLabel("Recent Expenses")
        ltitle.setStyleSheet(
            f"font-size:15px; font-weight:900; color:{_TEXT_PRI}; border:none; background:transparent;"
        )
        lhl.addWidget(lico); lhl.addWidget(ltitle); lhl.addStretch()
        ll.addWidget(lhdr)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Date", "Category", "Description", "Amount"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        ll.addWidget(self.table, stretch=1)

        # Pagination footer
        pag_footer = QFrame()
        pag_footer.setStyleSheet(
            f"QFrame {{ background:{_BG}; border-top:1px solid {_BORDER}; border-radius: 0 0 14px 14px; }}"
        )
        pfl = QHBoxLayout(pag_footer); pfl.setContentsMargins(14, 8, 14, 8)
        self.pagination = PaginationControl()
        self.pagination.page_changed.connect(self.load_data)
        self.pagination.limit_changed.connect(self.load_data)
        pfl.addWidget(self.pagination)
        ll.addWidget(pag_footer)

        cols.addWidget(list_card, stretch=1)
        main_layout.addLayout(cols)

        self.load_data()

    # ── original logic ─────────────────────────────────────────────────────
    def load_data(self, *args):
        skip    = (self.pagination.current_page - 1) * self.pagination.page_size
        limit   = self.pagination.page_size
        total   = expenses_col.count_documents({})
        self.pagination.set_total_records(total)
        expenses = list(expenses_col.find().sort("timestamp", -1).skip(skip).limit(limit))
        self.table.setRowCount(0)
        for ex in expenses:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(ex['timestamp'].strftime("%Y-%m-%d")))
            self.table.setItem(row, 1, QTableWidgetItem(ex['category']))
            self.table.setItem(row, 2, QTableWidgetItem(ex['description']))
            amt_item = QTableWidgetItem(f"Rs. {ex['amount']:.2f}")
            amt_item.setForeground(QColor(DANGER))
            self.table.setItem(row, 3, amt_item)

    def save_expense(self):
        desc = self.desc_input.text()
        amt  = self.amt_input.value()
        if not desc or amt <= 0:
            return
        shift = get_active_shift(self.user.get('username'))
        if not shift:
            QMessageBox.warning(self, "No Shift", "Please open a shift first.")
            return
        doc = {
            "description": desc,
            "category": self.cat_input.currentText(),
            "amount": amt,
            "user_id": self.user['_id'],
            "username": self.user['username'],
            "shift_id": shift['_id'],
            "timestamp": datetime.now()
        }
        expenses_col.insert_one(doc)
        update_shift_totals(shift['_id'], expense_inc=amt)
        self.load_data()
        self.desc_input.clear()
        self.amt_input.setValue(0)
        QMessageBox.information(self, "Success", "Expense Recorded")


# ─────────────────────────────────────────────────────────────────────────────
#  VISUALS TAB  — original logic, improved chrome + matplotlib theme
# ─────────────────────────────────────────────────────────────────────────────
class VisualsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{_BG};" + WIDGET_STYLE)

        # Refined matplotlib theme  — matches design system
        matplotlib.rcParams.update({
            'figure.facecolor':  _SURFACE,
            'axes.facecolor':    _BG,
            'axes.edgecolor':    _BORDER,
            'axes.labelcolor':   _TEXT_SEC,
            'axes.titlecolor':   _TEXT_PRI,
            'xtick.color':       _TEXT_HINT,
            'ytick.color':       _TEXT_HINT,
            'text.color':        _TEXT_PRI,
            'grid.color':        _BORDER,
            'grid.alpha':        0.7,
            'font.family':       'sans-serif',
            'axes.spines.top':   False,
            'axes.spines.right': False,
        })

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # ── Controls bar ─────────────────────────────────────────────────
        ctrl = QFrame()
        ctrl.setStyleSheet(
            f"QFrame {{ background:{_SURFACE}; border-radius:12px; border:1.5px solid {_BORDER}; }}"
        )
        cl = QHBoxLayout(ctrl); cl.setContentsMargins(16, 10, 16, 10); cl.setSpacing(10)

        cl.addWidget(_ctrl_label("FROM:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setFixedWidth(132)
        cl.addWidget(self.start_date)

        cl.addWidget(_ctrl_label("TO:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setFixedWidth(132)
        cl.addWidget(self.end_date)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1); sep.setStyleSheet(f"background:{_BORDER}; border:none;")
        cl.addWidget(sep)

        cl.addWidget(_ctrl_label("CHART:"))
        self.combo_chart = QComboBox()
        self.combo_chart.setMinimumWidth(170)
        self.combo_chart.addItems([
            "Sales Trend", "Hourly Sales", "Top Categories", "Top Items"
        ])
        cl.addWidget(self.combo_chart)

        btn_plot = styled_btn("  Generate", _PRIMARY,
                              icon=qta.icon('fa5s.chart-bar', color='white'))
        btn_plot.setFixedHeight(38); btn_plot.clicked.connect(self.plot_graph)
        cl.addWidget(btn_plot)

        cl.addStretch()
        layout.addWidget(ctrl)

        # ── Plot card ─────────────────────────────────────────────────────
        plot_card = QFrame()
        plot_card.setStyleSheet(
            f"QFrame {{ background:{_SURFACE}; border-radius:14px; border:1.5px solid {_BORDER}; }}"
        )
        pcl = QVBoxLayout(plot_card); pcl.setContentsMargins(16, 16, 16, 16)

        self.figure = Figure(figsize=(9, 5), dpi=100)
        self.figure.patch.set_facecolor(_SURFACE)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setStyleSheet("background:transparent; border:none;")
        pcl.addWidget(self.canvas)

        layout.addWidget(plot_card, stretch=1)

    # ── original logic ─────────────────────────────────────────────────────
    def plot_graph(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(_BG)
        for spine in ax.spines.values():
            spine.set_edgecolor(_BORDER)

        chart_type = self.combo_chart.currentText()
        start = datetime.combine(self.start_date.date().toPyDate(), datetime.min.time())
        end   = datetime.combine(self.end_date.date().toPyDate(), datetime.max.time())

        CHART_COLORS = [_PRIMARY, _SUCCESS, _INFO, _DANGER, _WARNING, '#F472B6', '#A78BFA']

        try:
            if chart_type == "Sales Trend":
                data = get_sales_trend(start, end)
                if data:
                    dates  = [d['_id'] for d in data]
                    values = [d['total_revenue'] for d in data]
                    ax.plot(dates, values, marker='o', linestyle='-', color=_PRIMARY,
                            linewidth=2.5, markersize=7, markerfacecolor=_PRIMARY,
                            markeredgecolor=_SURFACE, markeredgewidth=2)
                    ax.fill_between(dates, values, alpha=0.12, color=_PRIMARY)
                    ax.set_title("Daily Sales Trend", fontsize=14, fontweight='bold', pad=14)
                    ax.set_ylabel("Revenue (Rs.)")
                    ax.grid(True, linestyle='--', alpha=0.4)
                    if len(dates) > 5:
                        plt.setp(ax.get_xticklabels(), rotation=38, ha="right")
                else:
                    ax.text(0.5, 0.5, "No Data Available", ha='center', va='center',
                            fontsize=14, color=_TEXT_HINT)

            elif chart_type == "Hourly Sales":
                data = get_hourly_sales_report(start, end)
                if data:
                    hours  = [d['_id'] for d in data]
                    values = [d['total_revenue'] for d in data]
                    ax.bar(hours, values, color=_SUCCESS, alpha=0.80, width=0.7, zorder=2)
                    ax.bar(hours, values, color=_SUCCESS, alpha=0.12, width=0.7)
                    ax.set_title("Sales by Hour of Day", fontsize=14, fontweight='bold', pad=14)
                    ax.set_xlabel("Hour (24h)")
                    ax.set_ylabel("Revenue (Rs.)")
                    ax.set_xticks(range(0, 24))
                    ax.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
                else:
                    ax.text(0.5, 0.5, "No Data Available", ha='center', va='center',
                            fontsize=14, color=_TEXT_HINT)

            elif chart_type == "Top Categories":
                data = get_category_sales_report(start, end)
                if data:
                    labels = [d['_id'] for d in data]
                    sizes  = [d['total_revenue'] for d in data]
                    wedges, texts, autotexts = ax.pie(
                        sizes, labels=labels, autopct='%1.1f%%', startangle=90,
                        colors=CHART_COLORS[:len(labels)],
                        wedgeprops=dict(linewidth=2, edgecolor=_SURFACE),
                        pctdistance=0.82
                    )
                    for at in autotexts:
                        at.set_color(_TEXT_PRI); at.set_fontsize(11)
                    ax.set_title("Sales by Category", fontsize=14, fontweight='bold', pad=14)
                else:
                    ax.text(0.5, 0.5, "No Data Available", ha='center', va='center',
                            fontsize=14, color=_TEXT_HINT)

            elif chart_type == "Top Items":
                data = get_item_sales_report(start, end)
                if data:
                    data   = data[:10]
                    items  = [d['_id'] for d in data]
                    values = [d['qty'] for d in data]
                    y_pos  = range(len(items))
                    ax.barh(y_pos, values, color=_PRIMARY, alpha=0.80, height=0.65)
                    ax.set_yticks(y_pos)
                    ax.set_yticklabels(items, fontsize=11)
                    ax.invert_yaxis()
                    ax.set_title("Top 10 Selling Items (Qty)", fontsize=14, fontweight='bold', pad=14)
                    ax.set_xlabel("Quantity Sold")
                    ax.grid(axis='x', linestyle='--', alpha=0.4)
                else:
                    ax.text(0.5, 0.5, "No Data Available", ha='center', va='center',
                            fontsize=14, color=_TEXT_HINT)

            self.figure.tight_layout()
            self.canvas.draw()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Plotting failed: {str(e)}")