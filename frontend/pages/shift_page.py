from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QPushButton, QTableWidget, QHeaderView,
                             QDoubleSpinBox, QMessageBox, QTableWidgetItem,
                             QDialog, QScrollArea, QAbstractItemView, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
from backend.services.shift_service import get_active_shift, open_shift, end_shift, get_all_shifts
from backend.services.report_service import get_shift_report_data
from backend.core.database import orders_col
import qtawesome as qta
from frontend.shared_ui import GLOBAL_STYLE, C, page_header

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _divider():
    f = QFrame(); f.setFrameShape(QFrame.Shape.HLine); f.setFixedHeight(1)
    f.setStyleSheet(f"background: {C['divider']}; border: none;"); return f

def _badge(text, bg, fg="white", radius=10):
    lbl = QLabel(text); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"background: {bg}; color: {fg}; font-size: 10px; font-weight: 700; "
                      f"padding: 3px 10px; border-radius: {radius}px; border: none;")
    return lbl

def _action_btn(text, icon_name, bg, hover_bg, fg="white", height=40):
    btn = QPushButton(f"  {text}")
    btn.setIcon(qta.icon(icon_name, color=fg))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
    btn.setStyleSheet(f"""
        QPushButton {{ background: {bg}; color: {fg}; border: none; border-radius: 8px;
            font-size: 13px; font-weight: 700; padding: 0 16px; text-align: left; }}
        QPushButton:hover {{ background: {hover_bg}; }}
    """)
    return btn

TABLE_STYLE = f"""
    QTableWidget {{
        background: {C['surface']};
        alternate-background-color: #FAFBFC;
        border: none;
        font-size: 13px;
        color: {C['text_primary']};
        outline: none;
    }}
    QTableWidget::item {{
        padding: 6px 10px;
        border: none;
        border-bottom: 1px solid {C['divider']};
    }}
    QTableWidget::item:selected {{
        background: {C['primary_lt']};
        color: {C['primary']};
    }}
    QHeaderView::section {{
        background: {C['bg']};
        color: {C['text_sec']};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
        padding: 10px;
        border: none;
        border-bottom: 2px solid {C['divider']};
    }}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  SHIFT REPORT DIALOG  (original logic, upgraded UI)
# ─────────────────────────────────────────────────────────────────────────────
class ShiftReportDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shift Report")
        self.setFixedSize(460, 580)
        self.setStyleSheet(GLOBAL_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setFixedHeight(70)
        hdr.setStyleSheet(f"QFrame {{ background: {C['surface']}; border-bottom: 1.5px solid {C['border']}; border-radius: 0px; }}")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(22, 0, 22, 0); hl.setSpacing(12)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon('fa5s.file-invoice-dollar', color=C['primary']).pixmap(28, 28))
        title_col = QVBoxLayout(); title_col.setSpacing(2)
        ttl = QLabel("Shift Report")
        ttl.setStyleSheet(f"color: {C['text_primary']}; font-size: 17px; font-weight: 900;")
        start_str = data['shift']['start_time'].strftime("%b %d, %Y  %H:%M")
        sub = QLabel(f"Started  {start_str}")
        sub.setStyleSheet(f"color: {C['text_hint']}; font-size: 11px;")
        title_col.addWidget(ttl); title_col.addWidget(sub)
        hl.addWidget(icon_lbl); hl.addLayout(title_col); hl.addStretch()

        # Status badge in header
        s_status = data['shift'].get('status', 'Active')
        badge_bg = C['success'] if s_status == 'Active' else C['text_sec']
        status_pill = _badge(s_status.upper(), badge_bg, "white", radius=12)
        hl.addWidget(status_pill)
        layout.addWidget(hdr)

        # ── Body scroll ──────────────────────────────────────────────────────
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        body = QWidget(); body.setStyleSheet(f"background: {C['bg']};")
        bl = QVBoxLayout(body); bl.setContentsMargins(22, 18, 22, 22); bl.setSpacing(14)

        # Shift meta card
        meta_card = QFrame()
        meta_card.setStyleSheet(f"QFrame {{ background: {C['surface']}; border-radius: 10px; border: 1px solid {C['border']}; }}")
        ml = QGridLayout(meta_card); ml.setContentsMargins(16, 14, 16, 14); ml.setSpacing(10)

        def _meta(label, value, col_start):
            lbl = QLabel(label); lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {C['text_hint']}; letter-spacing: 0.5px;")
            val = QLabel(str(value)); val.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {C['text_primary']};")
            ml.addWidget(lbl, 0, col_start); ml.addWidget(val, 1, col_start)

        end = data['shift'].get('end_time')
        end_str = end.strftime("%b %d  %H:%M") if end else "Still Active"
        _meta("STARTED",  data['shift']['start_time'].strftime("%b %d, %Y  %H:%M"), 0)
        _meta("ENDED",    end_str,                                                   1)
        _meta("CASHIER",  data['shift'].get('user', 'Unknown'),                     2)
        bl.addWidget(meta_card)

        # Financial summary card
        fin_card = QFrame()
        fin_card.setStyleSheet(f"QFrame {{ background: {C['surface']}; border-radius: 10px; border: 1px solid {C['border']}; }}")
        fl = QVBoxLayout(fin_card); fl.setContentsMargins(16, 14, 16, 14); fl.setSpacing(0)

        section_lbl = QLabel("FINANCIAL SUMMARY")
        section_lbl.setStyleSheet(f"font-size: 10px; font-weight: 800; color: {C['text_hint']}; letter-spacing: 1px; margin-bottom: 10px;")
        fl.addWidget(section_lbl)

        def _fin_row(label, value, color=C['text_primary'], bold=False, top_sep=False):
            if top_sep:
                sep = QFrame(); sep.setFixedHeight(1)
                sep.setStyleSheet(f"background: {C['divider']}; border: none; margin: 6px 0;")
                fl.addWidget(sep)
            row = QHBoxLayout(); row.setContentsMargins(0, 4, 0, 4)
            lbl = QLabel(label)
            weight = "700" if bold else "500"
            lbl.setStyleSheet(f"font-size: 13px; font-weight: {weight}; color: {C['text_sec']};")
            val = QLabel(str(value))
            val.setStyleSheet(f"font-size: 13px; font-weight: {'800' if bold else '600'}; color: {color};")
            row.addWidget(lbl); row.addStretch(); row.addWidget(val)
            fl.addLayout(row)

        _fin_row("Opening Cash",   f"Rs {data['shift'].get('opening_cash', 0):,.2f}")
        _fin_row("Total Sales",    f"Rs {data['total_sales']:,.2f}",    C['primary'], bold=True)
        _fin_row("  ↳ Cash",       f"Rs {data['cash_sales']:,.2f}")
        _fin_row("  ↳ Card",       f"Rs {data['card_sales']:,.2f}")
        _fin_row("Total Expenses", f"Rs {data['total_expenses']:,.2f}", C['danger'],  bold=True, top_sep=True)
        bl.addWidget(fin_card)

        # Net cash highlight
        net_card = QFrame()
        net_cash = data['net_cash']
        net_card.setStyleSheet(f"QFrame {{ background: {C['success_lt']}; border-radius: 10px; border: 1.5px solid {C['success']}; }}")
        nl = QVBoxLayout(net_card); nl.setContentsMargins(16, 14, 16, 14); nl.setSpacing(4)
        net_lbl = QLabel("Net Cash in Drawer")
        net_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {C['success']}; letter-spacing: 0.5px;")
        net_val = QLabel(f"Rs {net_cash:,.2f}")
        net_val.setStyleSheet(f"font-size: 26px; font-weight: 900; color: {C['success']};")
        nl.addWidget(net_lbl); nl.addWidget(net_val)
        bl.addWidget(net_card)

        # Difference card (if closed)
        if data['shift'].get('status') == 'Closed':
            diff = data['shift'].get('cash_difference', 0)
            diff_bg   = C['danger_lt']  if diff < 0 else C['success_lt']
            diff_fg   = C['danger']     if diff < 0 else C['success']
            diff_border = C['danger']   if diff < 0 else C['success']
            diff_card = QFrame()
            diff_card.setStyleSheet(f"QFrame {{ background: {diff_bg}; border-radius: 10px; border: 1.5px solid {diff_border}; }}")
            dl = QVBoxLayout(diff_card); dl.setContentsMargins(16, 12, 16, 12); dl.setSpacing(2)
            diff_lbl = QLabel("Cash Difference")
            diff_lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {diff_fg}; letter-spacing: 0.5px;")
            diff_val = QLabel(f"{'−' if diff < 0 else '+'} Rs {abs(diff):,.2f}")
            diff_val.setStyleSheet(f"font-size: 20px; font-weight: 900; color: {diff_fg};")
            dl.addWidget(diff_lbl); dl.addWidget(diff_val)
            bl.addWidget(diff_card)

        bl.addStretch()
        scroll.setWidget(body); layout.addWidget(scroll)

        # Footer
        footer = QFrame()
        footer.setFixedHeight(64)
        footer.setStyleSheet(f"QFrame {{ background: {C['surface']}; border-top: 1px solid {C['border']}; border: none; border-top: 1px solid {C['border']}; }}")
        fl2 = QHBoxLayout(footer); fl2.setContentsMargins(22, 0, 22, 0)
        btn_close = _action_btn("Close", "fa5s.times", C['text_sec'], C['bg'], "white", height=42)
        btn_close.setStyleSheet(f"QPushButton {{ background: {C['bg']}; color: {C['text_sec']}; border: 1.5px solid {C['border']}; border-radius: 8px; font-size: 13px; font-weight: 600; padding: 0 20px; }} QPushButton:hover {{ background: {C['divider']}; }}")
        btn_close.clicked.connect(self.accept)
        fl2.addStretch(); fl2.addWidget(btn_close)
        layout.addWidget(footer)


# ─────────────────────────────────────────────────────────────────────────────
#  SHIFT PAGE
# ─────────────────────────────────────────────────────────────────────────────
class ShiftPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.active_shift = None
        self.setStyleSheet(GLOBAL_STYLE)
        self._build_ui()
        self.refresh_ui()

    # ── UI BUILD ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())

        # Main content area
        content = QWidget(); content.setStyleSheet(f"background: {C['bg']};")
        cl = QHBoxLayout(content); cl.setContentsMargins(24, 20, 24, 24); cl.setSpacing(20)
        cl.addWidget(self._build_status_panel(), stretch=0)
        cl.addWidget(self._build_history_panel(), stretch=1)
        root.addWidget(content)

    # ── TOP BAR ───────────────────────────────────────────────────────────────
    def _build_top_bar(self):
        return page_header("Shift Management", subtitle="Open · Close · Track cash & sales per shift")

    # ── STATUS PANEL (left) ───────────────────────────────────────────────────
    def _build_status_panel(self):
        panel = QFrame()
        panel.setMinimumWidth(240)
        panel.setMaximumWidth(340)
        panel.setStyleSheet(f"QFrame {{ background: {C['surface']}; border-radius: 14px; border: 1px solid {C['border']}; }}")
        layout = QVBoxLayout(panel); layout.setContentsMargins(22, 22, 22, 22); layout.setSpacing(0)

        # Section label
        sec_lbl = QLabel("CURRENT STATUS")
        sec_lbl.setStyleSheet(f"font-size: 10px; font-weight: 800; color: {C['text_hint']}; letter-spacing: 1.5px;")
        layout.addWidget(sec_lbl)
        layout.addSpacing(16)

        # Status indicator (big)
        self.status_frame = QFrame()
        self.status_frame.setFixedHeight(90)
        self.status_frame.setStyleSheet(f"QFrame {{ background: {C['success_lt']}; border-radius: 12px; border: 2px solid {C['success']}; }}")
        sf_layout = QVBoxLayout(self.status_frame); sf_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status = QLabel("CHECKING...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet(f"font-size: 22px; font-weight: 900; color: {C['success']};")
        self.lbl_status_sub = QLabel("Loading shift data...")
        self.lbl_status_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status_sub.setStyleSheet(f"font-size: 11px; color: {C['text_hint']};")
        sf_layout.addWidget(self.lbl_status); sf_layout.addWidget(self.lbl_status_sub)
        layout.addWidget(self.status_frame)
        layout.addSpacing(22)

        layout.addWidget(_divider())
        layout.addSpacing(18)

        # Balance input
        self.bal_label = QLabel("Opening Balance")
        self.bal_label.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {C['text_sec']}; margin-bottom: 4px;")
        layout.addWidget(self.bal_label)
        layout.addSpacing(6)

        self.bal_input = QDoubleSpinBox()
        self.bal_input.setRange(0, 100000)
        self.bal_input.setPrefix("Rs ")
        self.bal_input.setFixedHeight(46)
        self.bal_input.setStyleSheet(f"""
            QDoubleSpinBox {{
                font-size: 20px;
                font-weight: 700;
                color: {C['primary']};
                border: 2px solid {C['primary']};
                border-radius: 10px;
                padding: 6px 12px;
                background: {C['primary_lt']};
            }}
            QDoubleSpinBox:focus {{ border-color: {C['primary_dk']}; }}
        """)
        layout.addWidget(self.bal_input)
        layout.addSpacing(16)

        # Action button
        self.btn_action = QPushButton("Open Shift")
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setFixedHeight(48)
        self.btn_action.setStyleSheet(f"""
            QPushButton {{
                background: {C['success']};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{ background: #24874c; }}
            QPushButton:pressed {{ background: {C['success']}; }}
        """)
        self.btn_action.clicked.connect(self.toggle_shift)
        layout.addWidget(self.btn_action)
        layout.addStretch()

        # Helper tip
        tip = QLabel("💡  Double-click a row in history\nto view the full shift report.")
        tip.setStyleSheet(f"font-size: 11px; color: {C['text_hint']}; line-height: 1.5;")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip.setWordWrap(True)
        layout.addWidget(tip)

        return panel

    # ── HISTORY PANEL (right) ─────────────────────────────────────────────────
    def _build_history_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f"QFrame {{ background: {C['surface']}; border-radius: 14px; border: 1px solid {C['border']}; }}")
        layout = QVBoxLayout(panel); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)

        # Header bar
        hdr = QFrame(); hdr.setFixedHeight(52)
        hdr.setStyleSheet(f"QFrame {{ background: {C['bg']}; border-radius: 14px 14px 0 0; border-bottom: 1px solid {C['border']}; border-top: none; border-left: none; border-right: none; }}")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(18, 0, 18, 0)
        icon_lbl = QLabel(); icon_lbl.setPixmap(qta.icon('fa5s.history', color=C['primary']).pixmap(16, 16))
        hdr_title = QLabel("Shift History")
        hdr_title.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {C['text_primary']};")
        hl.addWidget(icon_lbl); hl.addSpacing(8); hl.addWidget(hdr_title); hl.addStretch()
        layout.addWidget(hdr)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Start Time", "End Time", "Cash Sales", "Expenses", "Status", "Action"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(5, 130)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.itemDoubleClicked.connect(self._on_row_double_click)
        layout.addWidget(self.table)

        return panel

    # ── ORIGINAL LOGIC ────────────────────────────────────────────────────────
    def refresh_ui(self):
        self.active_shift = get_active_shift(self.user.get('username'))

        if self.active_shift:
            # Active state
            self.lbl_status.setText("🟢  ACTIVE")
            self.lbl_status.setStyleSheet(f"font-size: 22px; font-weight: 900; color: {C['success']};")
            started = self.active_shift.get('start_time')
            if isinstance(started, datetime):
                self.lbl_status_sub.setText(f"Started  {started.strftime('%H:%M  ·  %b %d')}")
            self.status_frame.setStyleSheet(f"QFrame {{ background: {C['success_lt']}; border-radius: 12px; border: 2px solid {C['success']}; }}")
            self.btn_action.setText("  Close Shift")
            self.btn_action.setIcon(qta.icon('fa5s.stop-circle', color='white'))
            self.btn_action.setStyleSheet(f"""
                QPushButton {{
                    background: {C['danger']};
                    color: white; border: none; border-radius: 10px;
                    font-size: 14px; font-weight: 800; letter-spacing: 0.5px;
                }}
                QPushButton:hover {{ background: #c0303c; }}
            """)
            self.bal_label.setText("Closing Cash (Physical Count)")
            self.bal_input.setValue(0)
            self.bal_input.setStyleSheet(f"""
                QDoubleSpinBox {{
                    font-size: 20px; font-weight: 700; color: {C['danger']};
                    border: 2px solid {C['danger']}; border-radius: 10px;
                    padding: 6px 12px; background: {C['danger_lt']};
                }}
            """)
        else:
            # Closed state
            self.lbl_status.setText("🔴  CLOSED")
            self.lbl_status.setStyleSheet(f"font-size: 22px; font-weight: 900; color: {C['danger']};")
            self.lbl_status_sub.setText("No active shift  ·  Ready to open")
            self.status_frame.setStyleSheet(f"QFrame {{ background: {C['danger_lt']}; border-radius: 12px; border: 2px solid {C['danger']}; }}")
            self.btn_action.setText("  Open Shift")
            self.btn_action.setIcon(qta.icon('fa5s.play-circle', color='white'))
            self.btn_action.setStyleSheet(f"""
                QPushButton {{
                    background: {C['success']};
                    color: white; border: none; border-radius: 10px;
                    font-size: 14px; font-weight: 800; letter-spacing: 0.5px;
                }}
                QPushButton:hover {{ background: #24874c; }}
            """)
            self.bal_label.setText("Opening Balance")
            self.bal_input.setValue(0)
            self.bal_input.setStyleSheet(f"""
                QDoubleSpinBox {{
                    font-size: 20px; font-weight: 700; color: {C['primary']};
                    border: 2px solid {C['primary']}; border-radius: 10px;
                    padding: 6px 12px; background: {C['primary_lt']};
                }}
            """)

        # ── Load shift history table ──────────────────────────────────────────
        shifts = get_all_shifts()
        self.table.setRowCount(0)
        self._shift_ids = []

        for s in shifts:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._shift_ids.append(s['_id'])

            start = s['start_time'].strftime("%Y-%m-%d  %H:%M")
            end = s.get('end_time').strftime("%H:%M") if s.get('end_time') else "—"

            start_item = QTableWidgetItem(start)
            start_item.setFont(QFont("Consolas", 10))
            self.table.setItem(row, 0, start_item)

            end_item = QTableWidgetItem(end)
            end_item.setFont(QFont("Consolas", 10))
            end_item.setForeground(QColor(C['text_hint']))
            self.table.setItem(row, 1, end_item)

            cash_item = QTableWidgetItem(f"Rs {s.get('total_cash_sales', 0):,.2f}")
            cash_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            cash_item.setForeground(QColor(C['primary']))
            cash_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.table.setItem(row, 2, cash_item)

            exp_item = QTableWidgetItem(f"Rs {s.get('total_expenses', 0):,.2f}")
            exp_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            exp_item.setForeground(QColor(C['danger']))
            self.table.setItem(row, 3, exp_item)

            # Status badge cell
            status_text = s['status']
            status_bg   = C['success'] if status_text == 'Active' else C['text_hint']
            badge = _badge(status_text, status_bg, "white", radius=8)
            bw = QWidget(); bl_w = QHBoxLayout(bw); bl_w.setContentsMargins(8, 3, 8, 3); bl_w.addWidget(badge)
            self.table.setCellWidget(row, 4, bw)

            # View report button
            btn_view = QPushButton("  Report")
            btn_view.setIcon(qta.icon('fa5s.chart-bar', color='white'))
            btn_view.setFixedHeight(30)
            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_view.setStyleSheet(f"""
                QPushButton {{
                    background: {C['info']}; color: white; border: none;
                    border-radius: 6px; font-size: 11px; font-weight: 700; padding: 0 10px;
                }}
                QPushButton:hover {{ background: {C['primary_dk']}; }}
            """)
            btn_view.clicked.connect(lambda ch, sid=s['_id']: self.view_report(sid))
            cw = QWidget(); cw_l = QHBoxLayout(cw); cw_l.setContentsMargins(6, 3, 6, 3); cw_l.addWidget(btn_view)
            self.table.setCellWidget(row, 5, cw)
            self.table.setCellWidget(row, 5, cw)
            self.table.setRowHeight(row, 48)

    def _on_row_double_click(self, item):
        row = item.row()
        if row < len(self._shift_ids):
            self.view_report(self._shift_ids[row])

    def view_report(self, shift_id):
        data = get_shift_report_data(shift_id)
        if not data:
            QMessageBox.warning(self, "Error", "Could not load report data."); return
        dlg = ShiftReportDialog(data, self)
        dlg.exec()

    def toggle_shift(self):
        val = self.bal_input.value()
        if self.active_shift:
            # Block close if any Running/Kitchen/Pending/Delivery orders exist
            open_orders = list(orders_col.find({
                "status": {"$in": ["Running", "Kitchen", "Pending", "Delivery"]}
            }))
            if open_orders:
                details = ""
                for o in open_orders[:10]:
                    t = o.get('table_no') or o.get('order_type', '?')
                    inv = o.get('invoice_no', '—')
                    st = o.get('status', '')
                    details += f"• {t}  |  {inv}  |  {st}\n"
                if len(open_orders) > 10:
                    details += f"...aur {len(open_orders) - 10} orders\n"
                QMessageBox.warning(
                    self, "Shift Close Blocked",
                    f"Shift band nahi ho sakti!\n\n"
                    f"{len(open_orders)} pending/running order(s) hain:\n\n"
                    f"{details}\n"
                    f"Pehle sab orders complete/pay karein."
                )
                return
            end_shift(self.active_shift['_id'], val)
            QMessageBox.information(self, "Shift Closed", "Shift has been closed successfully.")
        else:
            open_shift(self.user['_id'], self.user['username'], val)
            QMessageBox.information(self, "Shift Opened", "Shift started successfully.")
        self.refresh_ui()
