from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFormLayout
from app.utils.helpers import create_button, get_color

class SupplierDialog(QDialog):
    def __init__(self, supplier=None):
        super().__init__()
        self.supplier = supplier
        self.setWindowTitle("Add Supplier" if supplier is None else "Edit Supplier")
        self.setFixedSize(400, 300)
        self.setStyleSheet(f"background-color: {get_color('bg')}; color: {get_color('text')};")

        self.init_ui()
        if supplier:
            self.populate_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.name_input = QLineEdit()
        self.contact_person_input = QLineEdit()
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()

        form_layout.addRow(QLabel("Name:"), self.name_input)
        form_layout.addRow(QLabel("Contact Person:"), self.contact_person_input)
        form_layout.addRow(QLabel("Email:"), self.email_input)
        form_layout.addRow(QLabel("Phone:"), self.phone_input)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_btn = create_button("Save", "save")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = create_button("Cancel", "cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)

    def populate_data(self):
        self.name_input.setText(self.supplier.get("name", ""))
        self.contact_person_input.setText(self.supplier.get("contact_person", ""))
        self.email_input.setText(self.supplier.get("email", ""))
        self.phone_input.setText(self.supplier.get("phone", ""))

    def get_data(self):
        return {
            "name": self.name_input.text(),
            "contact_person": self.contact_person_input.text(),
            "email": self.email_input.text(),
            "phone": self.phone_input.text(),
        }
