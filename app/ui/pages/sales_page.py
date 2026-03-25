"""
Sales Page — Slim orchestrator that wires together the refactored sub-modules.

Before refactoring this file was ~3 700 lines.  All logic now lives in:
    app.ui.sales.helpers          – styles, widget factories, utilities
    app.ui.sales.dialogs          – every QDialog class
    app.ui.sales.kitchen_display  – KDS window
    app.ui.sales.table_view       – Table selection / management view
    app.ui.sales.order_view       – Billing / order-entry view
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PyQt6.QtCore import Qt

from app.services.table_service import init_tables
from app.ui.sales.helpers import IMPROVED_STYLE
from app.ui.sales.table_view import TableSelectionView
from app.ui.sales.order_view import OrderView
from app.ui.pages.daily_reports import ShiftReportDialog


class SalesPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet(IMPROVED_STYLE)
        init_tables()

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self._layout.addWidget(self.stack)

        self.table_view = TableSelectionView(self)
        self.order_view = OrderView(self)

        self.stack.addWidget(self.table_view)
        self.stack.addWidget(self.order_view)

    # -- Public API (called by child views) ------------------------------------

    def open_order_view(self, table_no, order_type, order_id=None):
        self.order_view.setup(table_no, order_type, order_id)
        self.stack.setCurrentWidget(self.order_view)

    def open_shift_report(self):
        ShiftReportDialog(self).exec()

    def edit_running_order(self, order):
        self.open_order_view(
            order.get('table_no'),
            order.get('order_type', 'Dine In'),
            order.get('_id'),
        )

    def show_tables(self):
        self.table_view.load_tables()
        self.stack.setCurrentWidget(self.table_view)

    # -- Keyboard Shortcuts ----------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F5:
            if self.stack.currentWidget() == self.table_view:
                self.table_view.load_tables()
            elif self.stack.currentWidget() == self.order_view:
                self.order_view.load_menu_data()
            event.accept()
            return
        if self.stack.currentWidget() == self.table_view:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier and event.key() == Qt.Key.Key_T:
                self.table_view.open_shift_dialog()
                event.accept()
                return
        if self.stack.currentWidget() == self.order_view:
            if event.key() == Qt.Key.Key_F1:
                self.order_view.search_input.setFocus()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Escape:
                self.order_view.go_back()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Delete:
                row = self.order_view.cart_table.currentRow()
                if row >= 0:
                    item_name = self.order_view.cart_table.item(row, 0).text()
                    self.order_view.remove_item(item_name)
                event.accept()
                return
        super().keyPressEvent(event)
