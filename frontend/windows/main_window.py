import sys
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFrame, QStackedWidget,
                             QLineEdit, QApplication, QSizeGrip, QGraphicsDropShadowEffect,
                             QDialog, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QColor, QFont, QPixmap, QKeySequence, QShortcut
import qtawesome as qta

class MainWindow(QMainWindow):
    def __init__(self, user=None):
        super().__init__()
        self.user = user
        self.setWindowTitle(f"Abyte POS - {user['username'] if user else 'Guest'}")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)
        
        # Main Container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. Top Navigation Bar
        self.create_navbar()
        
        # 2. Main Content Area
        self.content_area = QStackedWidget()
        self.main_layout.addWidget(self.content_area)
        
        # Add Pages
        from frontend.pages.dashboard_page import DashboardPage
        from frontend.pages.sales_page import SalesPage
        from frontend.pages.inventory_page import InventoryPage
        from frontend.pages.finance_page import FinancePage
        from frontend.pages.admin_page import AdminPage
        from frontend.pages.shift_page import ShiftPage
        from frontend.pages.settings_page import SettingsPage
        from frontend.pages.delivery_page import DeliveryPage
        
        self.dashboard_page = DashboardPage()
        self.sales_page = SalesPage(self.user)
        self.inventory_page = InventoryPage(self.user)
        self.finance_page = FinancePage(self.user)
        self.admin_page = AdminPage(self.user)
        self.shift_page = ShiftPage(self.user)
        self.settings_page = SettingsPage(self.user)
        self.delivery_page = DeliveryPage()
        
        self.content_area.addWidget(self.dashboard_page) # Index 0
        self.content_area.addWidget(self.sales_page)     # Index 1
        self.content_area.addWidget(self.inventory_page) # Index 2
        self.content_area.addWidget(self.finance_page)   # Index 3
        self.content_area.addWidget(self.admin_page)     # Index 4
        self.content_area.addWidget(self.shift_page)     # Index 5
        self.content_area.addWidget(self.settings_page)  # Index 6
        self.content_area.addWidget(self.delivery_page)  # Index 7
        
        # Set default page
        self.content_area.setCurrentWidget(self.dashboard_page)

        # F2 shortcut: Quick Bill by Table Number
        sc = QShortcut(QKeySequence("F2"), self)
        sc.activated.connect(self.quick_bill_shortcut)

    def quick_bill_shortcut(self):
        """F2: Table number aur payment method le kar bill process karo."""
        from backend.core.database import orders_col
        from backend.utils.print_utils import print_receipt
        from backend.services.table_service import set_table_status

        dlg = QDialog(self)
        dlg.setWindowTitle("Quick Bill  —  F2")
        dlg.setFixedSize(340, 210)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(QLabel("<b>Table Number</b> (case insensitive):"))
        tbl_input = QLineEdit()
        tbl_input.setPlaceholderText("e.g.  t1  or  T1  or  t12")
        tbl_input.setFixedHeight(36)
        layout.addWidget(tbl_input)

        layout.addWidget(QLabel("<b>Payment Method:</b>"))
        pay_combo = QComboBox()
        pay_combo.addItems(["Cash", "Card", "Online"])
        pay_combo.setFixedHeight(36)
        layout.addWidget(pay_combo)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("Process Bill")
        btn_ok.setFixedHeight(38)
        btn_ok.setStyleSheet(
            "background:#059669;color:white;border:none;border-radius:8px;font-weight:700;font-size:13px;"
        )
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(38)
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        tbl_input.setFocus()
        tbl_input.returnPressed.connect(btn_ok.click)

        def process():
            raw = tbl_input.text().strip()
            if not raw:
                QMessageBox.warning(dlg, "Error", "Table number daalo.")
                return
            # Case insensitive: T1, t1, T01 sab same
            table_no = raw.upper()
            method = pay_combo.currentText()

            order = orders_col.find_one({
                "table_no": table_no,
                "status": {"$in": ["Running", "Kitchen"]}
            })
            if not order:
                QMessageBox.warning(dlg, "Not Found",
                    f"Table {table_no} par koi running order nahi mila.")
                return

            # Mark completed
            from datetime import datetime
            orders_col.update_one(
                {"_id": order["_id"]},
                {"$set": {
                    "status": "Completed",
                    "payment_method": method,
                    "completed_at": datetime.now(),
                    "updated_at": datetime.now(),
                }}
            )
            set_table_status(table_no, "Free")
            updated_order = orders_col.find_one({"_id": order["_id"]})
            print_receipt(updated_order)
            QMessageBox.information(dlg, "Done",
                f"Table {table_no} — Bill ({method}) process ho gaya!")
            dlg.accept()

        btn_ok.clicked.connect(process)
        dlg.exec()
        
    def create_navbar(self):
        from frontend.theme import Theme

        # Navbar Container - Dark professional look
        self.navbar = QFrame()
        self.navbar.setObjectName("Header")
        self.navbar.setFixedHeight(56)
        self.navbar.setStyleSheet(f"""
            QFrame#Header {{
                background-color: {Theme.NAVBAR_BG};
                border-bottom: 1px solid {Theme.NAVBAR_BORDER};
            }}
        """)

        nav_layout = QHBoxLayout(self.navbar)
        nav_layout.setContentsMargins(16, 0, 16, 0)
        nav_layout.setSpacing(4)

        # --- Left: Logo ---
        from backend.core.config import load_config, resolve_resource_path
        config = load_config()
        logo_path = resolve_resource_path(config.get("logo_path"))

        logo_icon = QLabel()
        if logo_path and os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaledToHeight(28, Qt.TransformationMode.SmoothTransformation)
            logo_icon.setPixmap(pixmap)
        else:
            logo_icon.setPixmap(qta.icon('fa5s.utensils', color=Theme.PRIMARY).pixmap(22, 22))

        logo_text = QLabel("ABYTE POS")
        logo_text.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 800;
            color: {Theme.NAVBAR_TEXT_ACTIVE};
            letter-spacing: 1.5px;
            background: transparent;
        """)

        nav_layout.addWidget(logo_icon)
        nav_layout.addWidget(logo_text)
        nav_layout.addSpacing(20)

        # Vertical separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        sep.setFixedHeight(24)
        sep.setStyleSheet(f"background: {Theme.NAVBAR_BORDER}; border: none;")
        nav_layout.addWidget(sep)
        nav_layout.addSpacing(8)

        # --- Center: Navigation Links ---
        self.nav_buttons_group = []

        def add_nav_btn(text, icon_name, page_idx=0):
            btn = QPushButton(f" {text}")
            btn._nav_label = text
            btn.setIcon(qta.icon(icon_name, color=Theme.NAVBAR_TEXT))
            btn.setIconSize(QSize(15, 15))
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumWidth(85)
            btn.setFixedHeight(36)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 8px;
                    color: {Theme.NAVBAR_TEXT};
                    font-size: 12px;
                    font-weight: 500;
                    padding: 0 10px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: rgba(255,255,255,0.08);
                    color: {Theme.NAVBAR_TEXT_ACTIVE};
                }}
                QPushButton:checked {{
                    background: {Theme.PRIMARY};
                    color: white;
                    font-weight: 700;
                }}
            """)
            if len(self.nav_buttons_group) == 0:
                btn.setChecked(True)
                btn.setIcon(qta.icon(icon_name, color='white'))

            btn.clicked.connect(lambda checked, b=btn, ico=icon_name, idx=page_idx: self.handle_nav_click(b, ico, idx))
            nav_layout.addWidget(btn)
            self.nav_buttons_group.append((btn, icon_name))

        from backend.core.permissions import has_permission

        add_nav_btn("Dashboard", "fa5s.th-large", 0)
        if has_permission(self.user, "billing"):
            add_nav_btn("Sales", "fa5s.shopping-cart", 1)
        if has_permission(self.user, "inventory"):
            add_nav_btn("Inventory", "fa5s.box-open", 2)
        if has_permission(self.user, "orders"):
            add_nav_btn("Delivery", "fa5s.motorcycle", 7)
        if has_permission(self.user, "shifts"):
            add_nav_btn("Shifts", "fa5s.clock", 5)
        if has_permission(self.user, "reports"):
            add_nav_btn("Reports", "fa5s.chart-line", 3)
        if has_permission(self.user, "admin") or self.user.get('role') == 'admin':
            add_nav_btn("Admin", "fa5s.user-shield", 4)
        if has_permission(self.user, "settings") or self.user.get('role') == 'admin':
            add_nav_btn("Settings", "fa5s.cog", 6)

        nav_layout.addStretch()

        # --- Right: User Info + Logout ---
        # Role badge
        role = self.user.get('role', 'staff').capitalize() if self.user else 'Staff'
        role_badge = QLabel(role)
        role_badge.setStyleSheet(f"""
            background: rgba(5,150,105,0.18);
            color: {Theme.PRIMARY_LIGHT};
            border: 1px solid rgba(52,211,153,0.3);
            border-radius: 10px;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 10px;
        """)
        nav_layout.addWidget(role_badge)
        nav_layout.addSpacing(8)

        # User name
        username = self.user['username'].capitalize() if self.user else "User"
        user_icon = QLabel()
        user_icon.setPixmap(qta.icon('fa5s.user-circle', color=Theme.NAVBAR_TEXT).pixmap(18, 18))
        user_lbl = QLabel(username)
        user_lbl.setStyleSheet(f"""
            color: {Theme.NAVBAR_TEXT_ACTIVE};
            font-size: 12px;
            font-weight: 600;
            background: transparent;
        """)
        nav_layout.addWidget(user_icon)
        nav_layout.addWidget(user_lbl)
        nav_layout.addSpacing(12)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFixedWidth(1)
        sep2.setFixedHeight(20)
        sep2.setStyleSheet(f"background: {Theme.NAVBAR_BORDER}; border: none;")
        nav_layout.addWidget(sep2)
        nav_layout.addSpacing(8)

        # Logout
        logout_btn = QPushButton()
        logout_btn.setIcon(qta.icon('fa5s.sign-out-alt', color='#EF4444'))
        logout_btn.setIconSize(QSize(16, 16))
        logout_btn.setToolTip("Logout")
        logout_btn.setFixedSize(34, 34)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(239,68,68,0.15);
            }
        """)
        logout_btn.clicked.connect(self.close)
        nav_layout.addWidget(logout_btn)

        self.main_layout.addWidget(self.navbar)

        # Subtle bottom shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 2)
        self.navbar.setGraphicsEffect(shadow)
        
    def resizeEvent(self, event):
        """Handle window resize for responsive behavior"""
        super().resizeEvent(event)
        width = self.width()

        for btn, _ico in self.nav_buttons_group:
            if width < 1000:
                btn.setText("")
                btn.setMinimumWidth(40)
            elif width < 1200:
                btn.setText(f" {btn._nav_label}")
                btn.setMinimumWidth(85)
            else:
                btn.setText(f" {btn._nav_label}")
                btn.setMinimumWidth(95)
        
    def handle_nav_click(self, clicked_btn, icon_name, page_idx):
        from frontend.theme import Theme
        for btn, ico in self.nav_buttons_group:
            btn.setChecked(False)
            btn.setIcon(qta.icon(ico, color=Theme.NAVBAR_TEXT))
        clicked_btn.setChecked(True)
        clicked_btn.setIcon(qta.icon(icon_name, color='white'))

        if page_idx < self.content_area.count():
            self.content_area.setCurrentIndex(page_idx)
        else:
            print(f"Page index {page_idx} not implemented yet")
