"""
Table Selection / Management view for the Sales module.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QLabel, QPushButton, QScrollArea,
    QMessageBox, QInputDialog, QDialog,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
import qtawesome as qta
import os
from datetime import datetime

from backend.core.config import get_setting, resolve_resource_path
from backend.core.database import orders_col
from backend.core.permissions import has_permission
from backend.services.table_service import (
    get_all_tables, set_table_status, init_tables, add_table, delete_table,
)
from backend.services.shift_service import (
    start_shift, end_shift, get_active_shift,
)

from frontend.modules.sales.helpers import IMPROVED_STYLE, _action_btn
from frontend.dialogs.sales_dialogs import (
    PinDialog, RunningOrdersDialog, DoneOrdersDialog,
    MergeTablesDialog, ShiftTableDialog, StartShiftDialog, EndShiftDialog,
    ShortcutsDialog,
)
from frontend.modules.sales.kitchen_display import KitchenDisplay
from frontend.pages.reports_page import ExpenseDialog, DayCloseDialog, ShiftReportDialog


class TableSelectionView(QWidget):
    def __init__(self, parent_page):
        super().__init__()
        self.parent_page = parent_page

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(12)

        # -- Header ---------------------------------------------------------
        header_card = QFrame()
        header_card.setProperty("class", "table-header-card")
        header_card.setObjectName("table-header-card")
        header_card.setMinimumHeight(50)
        header_card.setMaximumHeight(70)
        header_inner = QHBoxLayout(header_card)
        header_inner.setContentsMargins(15, 8, 15, 8)
        header_inner.setSpacing(8)

        logo_path = resolve_resource_path(get_setting("logo_path", "app/resources/POS.png"))
        if logo_path and os.path.exists(logo_path):
            logo_lbl = QLabel()
            try:
                pixmap = QPixmap(logo_path)
                logo_lbl.setPixmap(pixmap.scaled(
                    32, 32,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
                header_inner.addWidget(logo_lbl)
            except Exception:
                pass

        title = QLabel("Table Management")
        title.setProperty("class", "table-title")
        title.setStyleSheet("font-size: 18px;")
        header_inner.addWidget(title)
        header_inner.addSpacing(16)

        self.btn_notifications = QPushButton("0 Ready")
        self.btn_notifications.setMinimumHeight(28)
        self.btn_notifications.setMaximumHeight(34)
        self.btn_notifications.setProperty("class", "table-notify-btn")
        self.btn_notifications.clicked.connect(self.show_notifications)
        self.btn_notifications.hide()
        header_inner.addWidget(self.btn_notifications)

        header_inner.addStretch()

        def _hbtn(label, icon_n, hover_color):
            b = QPushButton(f"  {label}")
            b.setIcon(qta.icon(icon_n, color='#94a3b8'))
            b.setMinimumHeight(28)
            b.setMaximumHeight(36)
            b.setToolTip(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setProperty("class", "table-action-btn")
            b.setStyleSheet(
                f"QPushButton:hover {{ background: {hover_color}; border-color: {hover_color}; color: white; }}"
            )
            return b

        btn_add_table = _hbtn("Add Table",  "fa5s.plus",                "#059669")
        btn_del_table = _hbtn("Del Table",  "fa5s.trash",               "#ef4444")
        btn_kds       = _hbtn("Kitchen",    "fa5s.utensils",            "#f59e0b")
        btn_running   = _hbtn("Running",    "fa5s.clock",               "#059669")
        btn_done      = _hbtn("History",    "fa5s.history",             "#0ea5e9")
        btn_merge     = _hbtn("Merge",      "fa5s.object-group",        "#ef4444")
        btn_shift_t   = _hbtn("Shift Tbl",  "fa5s.exchange-alt",        "#0ea5e9")
        btn_shift_rep = _hbtn("Shift Rpt",  "fa5s.chart-bar",           "#059669")
        btn_expense   = _hbtn("Expenses",   "fa5s.receipt",             "#ef4444")
        btn_close_day = _hbtn("Z-Report",   "fa5s.file-invoice-dollar", "#059669")
        btn_refresh   = _hbtn("Refresh",    "fa5s.sync-alt",            "#0ea5e9")
        btn_help      = _hbtn("Help",       "fa5s.question-circle",     "#64748b")

        btn_add_table.clicked.connect(self.add_table_action)
        btn_del_table.clicked.connect(self.delete_table_action)
        btn_kds.clicked.connect(self.open_kds)
        btn_running.clicked.connect(self.open_running_orders)
        btn_done.clicked.connect(self.open_done_orders)
        btn_merge.clicked.connect(self.open_merge_dialog)
        btn_shift_t.clicked.connect(self.open_shift_dialog)
        btn_shift_rep.clicked.connect(self.parent_page.open_shift_report)
        btn_expense.clicked.connect(self.open_expense_dialog)
        btn_close_day.clicked.connect(self.open_day_close)
        btn_refresh.clicked.connect(self.load_tables)
        btn_help.clicked.connect(self.open_help_dialog)

        self._header_buttons = [
            btn_add_table, btn_del_table, btn_kds, btn_running, btn_done,
            btn_merge, btn_shift_t, btn_shift_rep, btn_expense, btn_close_day,
            btn_refresh, btn_help,
        ]
        for b in self._header_buttons:
            header_inner.addWidget(b)

        layout.addWidget(header_card)

        # -- Legend ---------------------------------------------------------
        legend = QHBoxLayout()
        legend.setSpacing(24)
        for color, text in [("#10b981", "Available"), ("#ef4444", "Occupied"), ("#f59e0b", "Reserved")]:
            row = QHBoxLayout()
            row.setSpacing(6)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 16px;")
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 700;")
            row.addWidget(dot)
            row.addWidget(lbl)
            legend.addLayout(row)
        legend.addStretch()
        layout.addLayout(legend)

        # -- Table Grid -----------------------------------------------------
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: #f8fafc;")
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background: #f8fafc;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(14)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.scroll.setWidget(self.grid_widget)
        layout.addWidget(self.scroll)

        # -- Takeaway Button ------------------------------------------------
        btn_takeaway = QPushButton("  Takeaway / Delivery Order")
        btn_takeaway.setMinimumHeight(42)
        btn_takeaway.setMaximumHeight(54)
        btn_takeaway.setProperty("class", "btn-takeaway")
        btn_takeaway.clicked.connect(lambda: self.parent_page.open_order_view(None, "Takeaway"))
        layout.addWidget(btn_takeaway)

        self.notif_timer = QTimer(self)
        self.notif_timer.timeout.connect(self.check_kitchen_updates)
        self.notif_timer.start(5000)

        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.toggle_blink)
        self.blink_state = False

        self.load_tables()

    # -- Kitchen Notifications -------------------------------------------------

    def check_kitchen_updates(self):
        try:
            count = orders_col.count_documents({"kitchen_status": "Ready", "waiter_notified": False})
            if count > 0:
                self.btn_notifications.setText(f"{count} Ready!")
                self.btn_notifications.show()
                if not self.blink_timer.isActive():
                    self.blink_timer.start(600)
            else:
                self.btn_notifications.hide()
                self.blink_timer.stop()
        except Exception:
            pass

    def toggle_blink(self):
        if self.blink_state:
            self.btn_notifications.setStyleSheet(
                "background: #ef4444; color: white; border: none; border-radius: 8px; "
                "font-weight: 800; font-size: 12px; padding: 0 14px;"
            )
        else:
            self.btn_notifications.setStyleSheet(
                "background: #f59e0b; color: #1e293b; border: none; border-radius: 8px; "
                "font-weight: 800; font-size: 12px; padding: 0 14px;"
            )
        self.blink_state = not self.blink_state

    def show_notifications(self):
        orders = list(orders_col.find({"kitchen_status": "Ready", "waiter_notified": False}))
        if not orders:
            self.btn_notifications.hide()
            return
        msg = "<b>Orders READY:</b><br><br>"
        ids = []
        for o in orders:
            msg += f"* Table {o.get('table_no', 'TKW')} ({o.get('invoice_no')})<br>"
            ids.append(o['_id'])
        reply = QMessageBox.information(
            self, "Kitchen Updates", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            orders_col.update_many({"_id": {"$in": ids}}, {"$set": {"waiter_notified": True}})
            self.check_kitchen_updates()

    # -- Table Loading ---------------------------------------------------------

    def load_tables(self):
        QTimer.singleShot(500, self.check_start_shift)
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tables = get_all_tables()
        if not tables:
            init_tables()
            tables = get_all_tables()

        running_orders = list(orders_col.find({"status": {"$in": ["Running", "Kitchen"]}}))
        table_times = {}
        for o in running_orders:
            t_no = o.get('table_no')
            created = o.get('created_at')
            if t_no and created:
                if isinstance(created, str):
                    try:
                        created = datetime.fromisoformat(created)
                    except Exception:
                        continue
                table_times[t_no] = int((datetime.now() - created).total_seconds() / 60)

        row, col = 0, 0
        for table in tables:
            self.grid_layout.addWidget(self.create_table_card(table, table_times), row, col)
            col += 1
            if col >= 6:
                col = 0
                row += 1

    def create_table_card(self, table, table_times):
        t_no   = table['table_no']
        status = table['status']

        if status == "Running":
            border_c, bg_c   = "#ef4444", "#fef2f2"
            icon_n, status_t = 'fa5s.utensils', "Occupied"
            text_c, bg_top   = "#b91c1c", "#fee2e2"
        elif status == "Reserved":
            border_c, bg_c   = "#f59e0b", "#fffbeb"
            icon_n, status_t = 'fa5s.clock', "Reserved"
            text_c, bg_top   = "#b45309", "#fef3c7"
        else:
            border_c, bg_c   = "#10b981", "#f0fdf4"
            icon_n, status_t = 'fa5s.check-circle', "Available"
            text_c, bg_top   = "#047857", "#dcfce7"

        card = QFrame()
        card.setMinimumSize(140, 130)
        card.setMaximumSize(200, 170)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setProperty("class", "table-card")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_c};
                border: 2px solid {border_c};
                border-radius: 14px;
            }}
            QFrame:hover {{
                background-color: white;
                border-width: 3px;
                border-color: {border_c};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_strip = QWidget()
        top_strip.setFixedHeight(32)
        top_strip.setStyleSheet(f"background: {bg_top}; border-radius: 12px 12px 0 0;")
        top_l = QHBoxLayout(top_strip)
        top_l.setContentsMargins(10, 0, 10, 0)
        status_badge = QLabel(status_t.upper())
        status_badge.setStyleSheet(
            f"color: {text_c}; font-size: 10px; font-weight: 800; "
            f"letter-spacing: 0.5px; background: transparent;"
        )
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_n, color=text_c).pixmap(14, 14))
        icon_lbl.setStyleSheet("background: transparent;")
        top_l.addWidget(status_badge)
        top_l.addStretch()
        top_l.addWidget(icon_lbl)
        layout.addWidget(top_strip)

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_l = QVBoxLayout(body)
        body_l.setContentsMargins(8, 8, 8, 8)
        body_l.setSpacing(6)
        body_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_no = QLabel(t_no)
        lbl_no.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_no.setStyleSheet(
            "font-size: 26px; font-weight: 900; color: #1e293b; "
            "background: transparent; letter-spacing: -1px;"
        )
        body_l.addWidget(lbl_no)

        if status == "Running" and t_no in table_times:
            mins = table_times[t_no]
            time_bg = "#fee2e2" if mins > 45 else "#fef3c7" if mins > 20 else "#dcfce7"
            time_fg = "#ef4444" if mins > 45 else "#d97706" if mins > 20 else "#16a34a"
            time_lbl = QLabel(f"{mins} min")
            time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            time_lbl.setStyleSheet(
                f"background: {time_bg}; color: {time_fg}; border-radius: 6px; "
                f"font-size: 11px; font-weight: 800; padding: 3px 8px;"
            )
            body_l.addWidget(time_lbl)
        else:
            cap_lbl = QLabel(f"{table.get('capacity', 4)} Seats")
            cap_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cap_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; background: transparent;")
            body_l.addWidget(cap_lbl)

        layout.addWidget(body, stretch=1)

        card.mousePressEvent = lambda e: self.parent_page.open_order_view(t_no, "Dine In")
        return card

    # -- Action Slots ----------------------------------------------------------

    def edit_running_order(self, order):
        self.parent_page.edit_running_order(order)

    def open_expense_dialog(self):
        ExpenseDialog(self.parent_page.user, self).exec()

    def open_shift_report(self):
        ShiftReportDialog(self).exec()

    def open_day_close(self):
        if not has_permission(self.parent_page.user, 'day_close'):
            QMessageBox.warning(self, "Access Denied", "No permission.")
            return

        # Block shift close if any orders are still running
        running = list(orders_col.find({"status": {"$in": ["Running", "Kitchen"]}}))
        if running:
            table_list = ", ".join(
                o.get("table_no") or o.get("invoice_no", "?") for o in running
            )
            QMessageBox.warning(
                self, "Running Orders Exist",
                f"Cannot close shift.\n\n"
                f"{len(running)} order(s) still open:\n{table_list}\n\n"
                f"Complete or void all orders before closing the shift."
            )
            return

        pin_dlg = PinDialog(self)
        if pin_dlg.exec() != QDialog.DialogCode.Accepted:
            return
        shift = get_active_shift(self.parent_page.user.get('username'))
        if shift:
            dlg = EndShiftDialog(shift, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                end_shift(shift['_id'], dlg.get_closing_cash())
                DayCloseDialog(self).exec()
        else:
            DayCloseDialog(self).exec()

    def check_start_shift(self):
        user = self.parent_page.user.get('username')
        if not get_active_shift(user):
            dlg = StartShiftDialog(self.parent_page.user, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                start_shift(user, dlg.get_opening_cash())

    def open_merge_dialog(self):
        dlg = MergeTablesDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_tables()

    def open_running_orders(self):
        RunningOrdersDialog(self).exec()

    def open_done_orders(self):
        DoneOrdersDialog(self).exec()

    def open_kds(self):
        if hasattr(self, 'kds_window') and self.kds_window.isVisible():
            self.kds_window.raise_()
            self.kds_window.activateWindow()
            return
        self.kds_window = KitchenDisplay()
        self.kds_window.show()

    def open_shift_dialog(self):
        dlg = ShiftTableDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_tables()

    def add_table_action(self):
        if not has_permission(self.parent_page.user, 'tables'):
            QMessageBox.warning(self, "Access Denied", "No permission.")
            return
        t_no, ok = QInputDialog.getText(self, "Add Table", "Enter Table Number (e.g., T11):")
        if ok and t_no:
            success, msg = add_table(t_no.strip())
            if success:
                QMessageBox.information(self, "Success", msg)
                self.load_tables()
            else:
                QMessageBox.warning(self, "Error", msg)

    def delete_table_action(self):
        if not has_permission(self.parent_page.user, 'tables'):
            QMessageBox.warning(self, "Access Denied", "No permission.")
            return
        t_no, ok = QInputDialog.getText(self, "Delete Table", "Enter Table Number:")
        if ok and t_no:
            if QMessageBox.question(
                self, "Confirm", f"Delete {t_no}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes:
                success, msg = delete_table(t_no.strip())
                if success:
                    QMessageBox.information(self, "Success", msg)
                    self.load_tables()
                else:
                    QMessageBox.warning(self, "Error", msg)

    def open_help_dialog(self):
        ShortcutsDialog(self).exec()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = self.width()
        if width < 1200:
            for btn in getattr(self, "_header_buttons", []):
                btn.setText("")
                btn.setMinimumWidth(40)
                btn.setMaximumWidth(40)
        else:
            for btn in getattr(self, "_header_buttons", []):
                btn.setText(f"  {btn.toolTip()}")
                btn.setMinimumWidth(0)
                btn.setMaximumWidth(16777215)
