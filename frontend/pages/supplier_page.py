from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame,
                             QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView,
                             QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt
import qtawesome as qta
from backend.services.supplier_service import get_suppliers, add_supplier, update_supplier, delete_supplier
from frontend.dialogs.supplier_dialog import SupplierDialog
from frontend.shared_ui import GLOBAL_STYLE, C, make_btn

class SupplierPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(GLOBAL_STYLE)
        self.init_ui()
        self.load_suppliers()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Top bar with actions
        top_bar = QHBoxLayout()
        self.add_supplier_btn = make_btn("  Add Supplier", icon=qta.icon('fa5s.plus', color='white'), height=38)
        self.add_supplier_btn.clicked.connect(self.show_add_supplier_dialog)
        top_bar.addWidget(self.add_supplier_btn)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Suppliers table
        table_card = QFrame()
        table_card.setStyleSheet(f"QFrame {{ background: {C['surface']}; border-radius: 12px; border: 1.5px solid {C['border']}; }}")
        card_layout = QVBoxLayout(table_card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        self.supplier_table = QTableWidget()
        self.supplier_table.setColumnCount(4)
        self.supplier_table.setHorizontalHeaderLabels(["Name", "Contact Person", "Email", "Phone"])
        self.supplier_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.supplier_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.supplier_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.supplier_table.verticalHeader().setVisible(False)
        self.supplier_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.supplier_table.setAlternatingRowColors(True)
        self.supplier_table.setShowGrid(False)
        self.supplier_table.itemDoubleClicked.connect(self.show_edit_supplier_dialog)
        card_layout.addWidget(self.supplier_table)
        layout.addWidget(table_card)

    def load_suppliers(self):
        try:
            suppliers = get_suppliers()
            self.supplier_table.setRowCount(len(suppliers))
            for row, supplier in enumerate(suppliers):
                self.supplier_table.setItem(row, 0, QTableWidgetItem(supplier.get("name") or ""))
                self.supplier_table.setItem(row, 1, QTableWidgetItem(supplier.get("contact_person") or ""))
                self.supplier_table.setItem(row, 2, QTableWidgetItem(supplier.get("email") or ""))
                self.supplier_table.setItem(row, 3, QTableWidgetItem(supplier.get("phone") or ""))
                self.supplier_table.item(row, 0).setData(1, supplier.get("_id"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load suppliers: {str(e)}")

    def show_add_supplier_dialog(self):
        dialog = SupplierDialog()
        if dialog.exec():
            supplier_data = dialog.get_data()
            try:
                add_supplier(supplier_data)
                self.load_suppliers()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add supplier: {str(e)}")

    def show_edit_supplier_dialog(self, item):
        row = item.row()
        supplier_id = self.supplier_table.item(row, 0).data(1)
        
        # Fetch full supplier data
        # This assumes a get_supplier_by_id function exists
        # from backend.services.supplier_service import get_supplier_by_id
        # supplier = get_supplier_by_id(supplier_id)
        
        # For now, we'll just use the data from the table
        supplier_data = {
            "name": self.supplier_table.item(row, 0).text(),
            "contact_person": self.supplier_table.item(row, 1).text(),
            "email": self.supplier_table.item(row, 2).text(),
            "phone": self.supplier_table.item(row, 3).text(),
        }

        dialog = SupplierDialog(supplier_data)
        if dialog.exec():
            updated_data = dialog.get_data()
            try:
                update_supplier(supplier_id, updated_data)
                self.load_suppliers()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update supplier: {str(e)}")
