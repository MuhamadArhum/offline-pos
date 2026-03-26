from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
                             QLabel, QPushButton, QLineEdit, QComboBox,
                             QMessageBox, QTabWidget, QCheckBox, QGroupBox,
                             QRadioButton, QFormLayout, QSpinBox, QDoubleSpinBox,
                             QFileDialog, QScrollArea, QButtonGroup, QInputDialog,
                             QListWidget, QListWidgetItem, QDialog, QAbstractItemView)
from PyQt6.QtPrintSupport import QPrinterInfo
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QColor, QFont
import qtawesome as qta
import json
import os
import shutil
from datetime import datetime
from bson import ObjectId
from backend.core.config import load_config, save_config, DEFAULT_CONFIG
from backend.core.database import db
from backend.utils.print_utils import print_test_page_v2
from frontend.theme import Theme
from backend.services.category_service import (
    get_categories, add_category, update_category, delete_category, 
    get_category_names, seed_default_categories
)

# ─── Light Theme Constants ─────────────────────────────────────────────────────

BG          = "#F0F2F5"
SURFACE     = "#FFFFFF"
BORDER      = "#E2E8F0"
DIVIDER     = "#F1F5F9"
ACCENT      = "#059669"          # Emerald Green
ACCENT_LIGHT= "#D1FAE5"
SUCCESS     = "#22c55e"
DANGER      = "#ef4444"
WARNING     = "#f59e0b"
TEXT_PRI    = "#1e293b"
TEXT_SEC    = "#475569"
TEXT_MUTED  = "#94a3b8"

GLOBAL_STYLE = f"""
    QWidget {{
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
        color: {TEXT_PRI};
    }}
    QLabel {{ color: {TEXT_PRI}; background: transparent; }}
    QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
        background-color: {SURFACE};
        color: {TEXT_PRI};
        border: 1.5px solid {BORDER};
        border-radius: 7px;
        padding: 8px 12px;
        min-height: 36px;
        selection-background-color: {ACCENT};
        selection-color: white;
    }}
    QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
        border-color: {ACCENT};
        background-color: {ACCENT_LIGHT};
    }}
    QLineEdit:read-only {{
        background-color: {DIVIDER};
        color: {TEXT_SEC};
    }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox QAbstractItemView {{
        background-color: {SURFACE};
        color: {TEXT_PRI};
        selection-background-color: {ACCENT};
        selection-color: white;
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 4px;
    }}
    QCheckBox {{
        color: {TEXT_PRI};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px; height: 18px;
        border: 1.5px solid {BORDER};
        border-radius: 4px;
        background: {SURFACE};
    }}
    QCheckBox::indicator:checked {{
        background-color: {ACCENT};
        border-color: {ACCENT};
        image: url(:/icons/check-white.png);
    }}
    QGroupBox {{
        border: 1.5px solid {BORDER};
        border-radius: 8px;
        margin-top: 10px;
        font-weight: 600;
        color: {TEXT_SEC};
        font-size: 12px;
        letter-spacing: 0.5px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        background: {SURFACE};
    }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{
        background: {DIVIDER};
        width: 7px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical {{
        background: #CBD5E1;
        border-radius: 3px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QListWidget {{
        background: {SURFACE};
        border: 1.5px solid {BORDER};
        border-radius: 8px;
        outline: none;
        color: {TEXT_PRI};
    }}
    QListWidget::item {{
        padding: 12px 14px;
        border-bottom: 1px solid {DIVIDER};
    }}
    QListWidget::item:selected {{
        background-color: {ACCENT_LIGHT};
        color: {ACCENT};
        border-left: 3px solid {ACCENT};
    }}
    QListWidget::item:hover:!selected {{
        background-color: {DIVIDER};
    }}
    QTabWidget::pane {{
        border: none;
        background: {BG};
    }}
    QTabBar::tab {{
        background: {SURFACE};
        color: {TEXT_SEC};
        padding: 11px 20px;
        font-size: 13px;
        font-weight: 600;
        border: 1px solid {BORDER};
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        margin-right: 3px;
    }}
    QTabBar::tab:selected {{
        background: {ACCENT};
        color: white;
        border-color: {ACCENT};
    }}
    QTabBar::tab:hover:!selected {{
        background: {ACCENT_LIGHT};
        color: {ACCENT};
    }}
"""

def _lighten(hex_color, factor=15):
    c = QColor(hex_color)
    return QColor(min(c.red()+factor,255), min(c.green()+factor,255), min(c.blue()+factor,255)).name()

def _darken(hex_color, factor=15):
    c = QColor(hex_color)
    return QColor(max(c.red()-factor,0), max(c.green()-factor,0), max(c.blue()-factor,0)).name()

def make_btn(text, color=ACCENT, text_color="white", icon=None, height=40):
    btn = QPushButton(text)
    if icon: btn.setIcon(icon)
    btn.setMinimumHeight(height)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {color};
            color: {text_color};
            border: none;
            border-radius: 8px;
            padding: 8px 18px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background-color: {_lighten(color)}; }}
        QPushButton:pressed {{ background-color: {_darken(color)}; }}
    """)
    return btn

def make_ghost_btn(text, icon=None, height=38):
    btn = QPushButton(text)
    if icon: btn.setIcon(icon)
    btn.setMinimumHeight(height)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {SURFACE};
            color: {TEXT_SEC};
            border: 1.5px solid {BORDER};
            border-radius: 8px;
            padding: 7px 16px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {DIVIDER};
            color: {TEXT_PRI};
            border-color: #C7CFE2;
        }}
        QPushButton:pressed {{ background-color: #E2E6F0; }}
    """)
    return btn

def make_danger_btn(text, icon=None, height=38):
    return make_btn(text, color=DANGER, text_color="white", icon=icon, height=height)

def card(padding=20):
    f = QFrame()
    f.setStyleSheet(f"""
        QFrame {{
            background-color: {SURFACE};
            border: 1.5px solid {BORDER};
            border-radius: 12px;
        }}
    """)
    f.setContentsMargins(padding, padding, padding, padding)
    return f

def divider_line():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"background-color: {DIVIDER}; max-height: 1px; border: none;")
    return line

def section_header_lbl(text):
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(f"""
        color: {TEXT_SEC};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        padding-bottom: 2px;
    """)
    return lbl

def card_title(text, icon_name=None, icon_color=ACCENT):
    layout = QHBoxLayout()
    layout.setSpacing(10)
    if icon_name:
        ico = QLabel()
        ico.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(20, 20))
        layout.addWidget(ico)
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {TEXT_PRI};")
    layout.addWidget(lbl)
    layout.addStretch()
    return layout


# ─── Settings Page ─────────────────────────────────────────────────────────────

class SettingsPage(QWidget):
    def __init__(self, user=None):
        super().__init__()
        self.user = user
        self.setStyleSheet(GLOBAL_STYLE + f"QWidget {{ background-color: {BG}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE};
                border-bottom: 1.5px solid {BORDER};
            }}
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(28, 0, 28, 0)

        title = QLabel("System Settings")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {TEXT_PRI};")
        h_layout.addWidget(title)
        h_layout.addStretch()
        layout.addWidget(header)

        # ── Tabs ──
        self.tabs = QTabWidget()

        self.general_tab     = GeneralSettingsTab()
        self.printer_tab     = PrinterSettingsTab()
        self.database_tab    = DatabaseSettingsTab()
        self.print_design_tab = PrintDesignTab()

        self.tabs.addTab(self.general_tab,      qta.icon('fa5s.cog',         color=TEXT_SEC), "General")
        self.tabs.addTab(self.printer_tab,      qta.icon('fa5s.print',       color=TEXT_SEC), "Printers")
        self.tabs.addTab(self.print_design_tab, qta.icon('fa5s.file-invoice',color=TEXT_SEC), "Print Design")
        self.tabs.addTab(self.database_tab,     qta.icon('fa5s.database',    color=TEXT_SEC), "Database")

        layout.addWidget(self.tabs)


# ─── General Settings Tab ──────────────────────────────────────────────────────

class GeneralSettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {BG};")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background-color: {BG};")

        self.content = QWidget()
        self.content.setStyleSheet(f"background-color: {BG};")
        self.scroll_layout = QVBoxLayout(self.content)
        self.scroll_layout.setContentsMargins(28, 24, 28, 24)
        self.scroll_layout.setSpacing(18)

        self.create_restaurant_info_card()
        self.create_financial_card()
        self.create_appearance_card()
        self.create_security_card()
        self.scroll_layout.addStretch()

        scroll.setWidget(self.content)
        outer.addWidget(scroll, stretch=1)

        # ── Save Footer ──
        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE};
                border-top: 1.5px solid {BORDER};
            }}
        """)
        footer.setFixedHeight(64)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(28, 0, 28, 0)
        f_layout.addStretch()
        btn_save = make_btn("  Save Changes", ACCENT,
                            icon=qta.icon('fa5s.save', color='white'), height=42)
        btn_save.setMinimumWidth(160)
        btn_save.clicked.connect(self.save_settings)
        f_layout.addWidget(btn_save)
        outer.addWidget(footer)

        self.load_settings()

    def _card(self):
        f = QFrame()
        f.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE};
                border: 1.5px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        return f

    def create_restaurant_info_card(self):
        c = self._card()
        lay = QVBoxLayout(c)
        lay.setContentsMargins(20, 18, 20, 20)
        lay.setSpacing(14)
        lay.addLayout(card_title("Restaurant Details", 'fa5s.store', ACCENT))
        lay.addWidget(divider_line())

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.input_name    = QLineEdit(); self.input_name.setPlaceholderText("e.g. Tasty Bites Restaurant")
        self.input_address = QLineEdit(); self.input_address.setPlaceholderText("e.g. 123 Main St, City")
        self.input_phone   = QLineEdit(); self.input_phone.setPlaceholderText("e.g. 0300-1234567")
        self.input_footer  = QLineEdit(); self.input_footer.setPlaceholderText("e.g. Thank you for dining with us!")

        for lbl, widget in [("Restaurant Name:", self.input_name), ("Address:", self.input_address),
                              ("Phone:", self.input_phone), ("Footer Message:", self.input_footer)]:
            l = QLabel(lbl)
            l.setStyleSheet(f"color: {TEXT_SEC}; font-weight: 600; font-size: 12px;")
            form.addRow(l, widget)

        lay.addLayout(form)
        self.scroll_layout.addWidget(c)

    def create_financial_card(self):
        c = self._card()
        lay = QVBoxLayout(c)
        lay.setContentsMargins(20, 18, 20, 20)
        lay.setSpacing(16)
        lay.addLayout(card_title("Financial Settings", 'fa5s.coins', "#F59E0B"))
        lay.addWidget(divider_line())

        # ── Basic ──────────────────────────────────────────────────────
        basic_form = QFormLayout()
        basic_form.setSpacing(10)
        basic_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.input_currency = QLineEdit(); self.input_currency.setPlaceholderText("e.g. PKR, $, €")
        self.input_delivery = QDoubleSpinBox(); self.input_delivery.setRange(0, 5000); self.input_delivery.setPrefix("Rs. ")

        for lbl, widget in [("Currency Symbol:", self.input_currency),
                             ("Delivery Charge:", self.input_delivery)]:
            l = QLabel(lbl)
            l.setStyleSheet(f"color: {TEXT_SEC}; font-weight: 600; font-size: 12px;")
            basic_form.addRow(l, widget)
        lay.addLayout(basic_form)

        # ── Per-Category Tax & Service Charge ──────────────────────────
        lay.addWidget(divider_line())
        cat_title = QLabel("Tax & Service Charge per Order Type")
        cat_title.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 800; font-size: 13px;")
        lay.addWidget(cat_title)

        # Header row
        hdr = QHBoxLayout()
        for txt, w in [("Order Type", 120), ("Tax Rate", 110), ("Service Charge", 130)]:
            h = QLabel(txt)
            h.setFixedWidth(w)
            h.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
            hdr.addWidget(h)
        hdr.addStretch()
        lay.addLayout(hdr)

        self._cat_spins = {}   # {category: {"tax": spin, "svc": spin}}
        for cat in ["Dine In", "Takeaway", "Delivery"]:
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = QLabel(cat)
            lbl.setFixedWidth(120)
            lbl.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 700; font-size: 13px;")

            spin_tax = QDoubleSpinBox()
            spin_tax.setRange(0, 100); spin_tax.setSuffix("%"); spin_tax.setFixedWidth(110)

            spin_svc = QDoubleSpinBox()
            spin_svc.setRange(0, 100); spin_svc.setSuffix("%"); spin_svc.setFixedWidth(130)

            row.addWidget(lbl)
            row.addWidget(spin_tax)
            row.addWidget(spin_svc)
            row.addStretch()
            lay.addLayout(row)
            self._cat_spins[cat] = {"tax": spin_tax, "svc": spin_svc}

        # ── Per-Payment Tax ────────────────────────────────────────────
        lay.addWidget(divider_line())
        pay_title = QLabel("Tax Rate per Payment Method")
        pay_title.setStyleSheet(f"color: {TEXT_PRI}; font-weight: 800; font-size: 13px;")
        lay.addWidget(pay_title)

        pay_sub = QLabel("Overrides per-category tax when payment method is known.")
        pay_sub.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        lay.addWidget(pay_sub)

        pay_form = QFormLayout()
        pay_form.setSpacing(10)
        pay_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.spin_tax_cash = QDoubleSpinBox(); self.spin_tax_cash.setRange(0, 100); self.spin_tax_cash.setSuffix("%")
        self.spin_tax_card = QDoubleSpinBox(); self.spin_tax_card.setRange(0, 100); self.spin_tax_card.setSuffix("%")

        for lbl_txt, widget in [("Cash Tax Rate:", self.spin_tax_cash), ("Card Tax Rate:", self.spin_tax_card)]:
            l = QLabel(lbl_txt)
            l.setStyleSheet(f"color: {TEXT_SEC}; font-weight: 600; font-size: 12px;")
            pay_form.addRow(l, widget)
        lay.addLayout(pay_form)

        # Keep hidden legacy spinboxes so load/save logic doesn't break
        self.input_tax     = QDoubleSpinBox(); self.input_tax.hide()
        self.input_service = QDoubleSpinBox(); self.input_service.hide()
        lay.addWidget(self.input_tax)
        lay.addWidget(self.input_service)

        self.scroll_layout.addWidget(c)

    def create_appearance_card(self):
        c = self._card()
        lay = QVBoxLayout(c)
        lay.setContentsMargins(20, 18, 20, 20)
        lay.setSpacing(14)
        lay.addLayout(card_title("Appearance & Logo", 'fa5s.paint-brush', "#8B5CF6"))
        lay.addWidget(divider_line())

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Light", "Dark"])

        logo_row = QHBoxLayout()
        logo_row.setSpacing(8)
        self.input_logo_path = QLineEdit(); self.input_logo_path.setReadOnly(True)
        self.input_logo_path.setPlaceholderText("Select logo image...")
        btn_browse = make_ghost_btn("Browse", icon=qta.icon('fa5s.folder-open', color=TEXT_SEC), height=36)
        btn_browse.clicked.connect(self.browse_logo)
        logo_row.addWidget(self.input_logo_path)
        logo_row.addWidget(btn_browse)

        self.chk_print_logo = QCheckBox("Print Logo on Receipt")

        for lbl, widget in [("App Theme:", self.combo_theme), ("Receipt Logo:", None), ("", self.chk_print_logo)]:
            l = QLabel(lbl)
            l.setStyleSheet(f"color: {TEXT_SEC}; font-weight: 600; font-size: 12px;")
            if lbl == "Receipt Logo:":
                w = QWidget(); w.setLayout(logo_row); w.setStyleSheet("background: transparent; border: none;")
                form.addRow(l, w)
            else:
                form.addRow(l, widget)

        lay.addLayout(form)
        self.scroll_layout.addWidget(c)

    def create_security_card(self):
        c = self._card()
        lay = QVBoxLayout(c)
        lay.setContentsMargins(20, 18, 20, 20)
        lay.setSpacing(14)
        lay.addLayout(card_title("Security", 'fa5s.lock', DANGER))
        lay.addWidget(divider_line())

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.input_pin = QLineEdit()
        self.input_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_pin.setPlaceholderText("Admin PIN (Default: 1234)")

        self.chk_show_pin = QCheckBox("Show PIN")
        self.chk_show_pin.stateChanged.connect(
            lambda s: self.input_pin.setEchoMode(
                QLineEdit.EchoMode.Normal if s else QLineEdit.EchoMode.Password
            )
        )

        for lbl, widget in [("Admin PIN:", self.input_pin), ("", self.chk_show_pin)]:
            l = QLabel(lbl)
            l.setStyleSheet(f"color: {TEXT_SEC}; font-weight: 600; font-size: 12px;")
            form.addRow(l, widget)

        lay.addLayout(form)
        self.scroll_layout.addWidget(c)

    def browse_logo(self):
        # ── Logic unchanged ──
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Logo", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.input_logo_path.setText(file_path)

    def load_settings(self):
        # ── Logic unchanged ──
        config = load_config()
        r_info = config.get("restaurant_info", {})
        self.input_name.setText(r_info.get("name", ""))
        self.input_address.setText(r_info.get("address", ""))
        self.input_phone.setText(r_info.get("phone", ""))
        self.input_footer.setText(r_info.get("footer", ""))
        self.input_currency.setText(config.get("currency", "PKR"))
        self.input_delivery.setValue(config.get("delivery_charge", 150.0))

        # Per-category charges
        cat_charges = config.get("category_charges", {})
        for cat, spins in self._cat_spins.items():
            cat_cfg = cat_charges.get(cat, {})
            spins["tax"].setValue(cat_cfg.get("tax_rate", 0.0))
            spins["svc"].setValue(cat_cfg.get("service_charge", 0.0))

        # Per-payment tax
        pay_tax = config.get("payment_tax", {})
        self.spin_tax_cash.setValue(pay_tax.get("Cash", 0.0))
        self.spin_tax_card.setValue(pay_tax.get("Card", 0.0))
        self.combo_theme.setCurrentText(config.get("theme", "light").capitalize())
        self.input_logo_path.setText(config.get("logo_path", ""))
        self.chk_print_logo.setChecked(config.get("print_logo", True))
        self.input_pin.setText(config.get("admin_pin", "1234"))

    def save_settings(self):
        # ── Logic unchanged ──
        config = load_config()
        config["restaurant_info"] = {
            "name": self.input_name.text(),
            "address": self.input_address.text(),
            "phone": self.input_phone.text(),
            "footer": self.input_footer.text()
        }
        config["currency"]        = self.input_currency.text()
        config["delivery_charge"] = self.input_delivery.value()

        # Per-category charges
        cat_charges = {}
        for cat, spins in self._cat_spins.items():
            cat_charges[cat] = {
                "tax_rate": spins["tax"].value(),
                "service_charge": spins["svc"].value(),
            }
        config["category_charges"] = cat_charges

        # Per-payment tax
        config["payment_tax"] = {
            "Cash": self.spin_tax_cash.value(),
            "Card": self.spin_tax_card.value(),
        }

        # Keep legacy keys in sync with Dine In defaults
        config["tax_rate"]       = cat_charges.get("Dine In", {}).get("tax_rate", 0.0)
        config["service_charge"] = cat_charges.get("Dine In", {}).get("service_charge", 0.0)
        config["admin_pin"]        = self.input_pin.text()
        config["theme"]            = self.combo_theme.currentText().lower()
        config["print_logo"]       = self.chk_print_logo.isChecked()

        new_logo_path = self.input_logo_path.text()
        if new_logo_path and os.path.exists(new_logo_path) and "app/resources" not in new_logo_path.replace("\\", "/"):
            try:
                resources_dir = os.path.join(os.getcwd(), "app", "resources")
                os.makedirs(resources_dir, exist_ok=True)
                ext = os.path.splitext(new_logo_path)[1]
                dest_path = os.path.join(resources_dir, f"custom_logo{ext}")
                shutil.copy2(new_logo_path, dest_path)
                config["logo_path"] = f"app/resources/custom_logo{ext}"
            except Exception as e:
                print(f"Error copying logo: {e}")
                config["logo_path"] = new_logo_path
        else:
            config["logo_path"] = new_logo_path

        if save_config(config):
            QMessageBox.information(self, "Success", "Settings saved successfully!")
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings.")


# ─── Printer Dialog ────────────────────────────────────────────────────────────

class PrinterDialog(QDialog):
    def __init__(self, parent=None, printer_data=None):
        super().__init__(parent)
        self.setWindowTitle("Add Printer" if not printer_data else "Edit Printer")
        self.setModal(True)
        self.resize(420, 520)
        self.setStyleSheet(GLOBAL_STYLE + f"QDialog {{ background-color: {SURFACE}; }}")
        self.printer_data = printer_data or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title_lbl = QLabel("Printer" if not printer_data else "Edit Printer")
        title_lbl.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {TEXT_PRI};")
        layout.addWidget(title_lbl)
        layout.addWidget(divider_line())
        layout.addSpacing(4)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def lbl(t):
            l = QLabel(t)
            l.setStyleSheet(f"color: {TEXT_SEC}; font-weight: 600; font-size: 12px;")
            return l

        self.name_input = QLineEdit(self.printer_data.get("name", ""))
        self.name_input.setPlaceholderText("e.g. Kitchen Printer")

        self.type_combo = QComboBox()
        self.type_combo.addItems(["USB / System Printer", "Network Printer (ESC/POS)"])
        self.type_combo.setCurrentIndex(0 if self.printer_data.get("type", "usb") == "usb" else 1)
        self.type_combo.currentIndexChanged.connect(self.toggle_fields)

        form.addRow(lbl("Printer Label:"), self.name_input)
        form.addRow(lbl("Connection Type:"), self.type_combo)
        layout.addLayout(form)

        # USB
        self.usb_container = QWidget()
        self.usb_container.setStyleSheet("background: transparent; border: none;")
        usb_layout = QFormLayout(self.usb_container)
        usb_layout.setContentsMargins(0, 0, 0, 0)
        self.usb_combo = QComboBox()
        self.usb_combo.addItems(QPrinterInfo.availablePrinterNames())
        if self.printer_data.get("type") == "usb":
            self.usb_combo.setCurrentText(self.printer_data.get("usb_name", ""))
        usb_layout.addRow(lbl("Select Printer:"), self.usb_combo)
        layout.addWidget(self.usb_container)

        # Network
        self.net_container = QWidget()
        self.net_container.setStyleSheet("background: transparent; border: none;")
        net_layout = QFormLayout(self.net_container)
        net_layout.setContentsMargins(0, 0, 0, 0)
        self.ip_input = QLineEdit(self.printer_data.get("ip", ""))
        self.ip_input.setPlaceholderText("192.168.1.x")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(self.printer_data.get("port", 9100))
        net_layout.addRow(lbl("IP Address:"), self.ip_input)
        net_layout.addRow(lbl("Port:"), self.port_input)
        layout.addWidget(self.net_container)

        # Roles
        role_group = QGroupBox("Printer Roles")
        role_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1.5px solid {BORDER};
                border-radius: 8px;
                margin-top: 10px;
                font-weight: 600;
                color: {TEXT_SEC};
                font-size: 12px;
                background: {SURFACE};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                background: {SURFACE};
            }}
        """)
        role_layout = QVBoxLayout(role_group)
        role_layout.setContentsMargins(12, 14, 12, 12)
        self.role_receipt = QCheckBox("Receipt Printer (Cashier)")
        self.role_kot     = QCheckBox("Kitchen Order Ticket (KOT)")
        roles = self.printer_data.get("roles", [])
        if "receipt" in roles: self.role_receipt.setChecked(True)
        if "kot"     in roles: self.role_kot.setChecked(True)
        role_layout.addWidget(self.role_receipt)
        role_layout.addWidget(self.role_kot)
        layout.addWidget(role_group)

        # Test
        btn_test = make_ghost_btn("  Test Connection", icon=qta.icon('fa5s.plug', color=TEXT_SEC))
        btn_test.clicked.connect(self.test_connection)
        layout.addWidget(btn_test)

        layout.addStretch()

        # Footer Buttons
        layout.addWidget(divider_line())
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel_btn = make_ghost_btn("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = make_btn("  Save Printer", ACCENT, icon=qta.icon('fa5s.save', color='white'), height=42)
        save_btn.clicked.connect(self.validate_and_accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        self.toggle_fields()

    def toggle_fields(self):
        # ── Logic unchanged ──
        is_usb = self.type_combo.currentIndex() == 0
        self.usb_container.setVisible(is_usb)
        self.net_container.setVisible(not is_usb)

    def test_connection(self):
        # ── Logic unchanged ──
        data = self.get_temp_data()
        temp_config = {
            "printer_config": data,
            "restaurant_info": load_config().get("restaurant_info", {})
        }
        p_type = "kot" if "kot" in data["roles"] and "receipt" not in data["roles"] else "receipt"
        success, msg = print_test_page_v2(temp_config, print_type=p_type)
        if success:
            QMessageBox.information(self, "Success", f"Test print sent to {data['name']}.")
        else:
            QMessageBox.warning(self, "Error", f"Test print failed: {msg}")

    def get_temp_data(self):
        # ── Logic unchanged ──
        roles = []
        if self.role_receipt.isChecked(): roles.append("receipt")
        if self.role_kot.isChecked():     roles.append("kot")
        return {
            "name":     self.name_input.text(),
            "type":     "usb" if self.type_combo.currentIndex() == 0 else "network",
            "usb_name": self.usb_combo.currentText(),
            "ip":       self.ip_input.text(),
            "port":     self.port_input.value(),
            "roles":    roles
        }

    def validate_and_accept(self):
        # ── Logic unchanged ──
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Error", "Printer Label is required.")
            return
        self.accept()

    def get_data(self):
        return self.get_temp_data()


# ─── Printer Settings Tab ──────────────────────────────────────────────────────

class PrinterSettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {BG};")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Content
        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {BG};")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # ── Top Bar ──
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        title_lbl = QLabel("Printer Management")
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {TEXT_PRI};")
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.print', color=ACCENT).pixmap(20, 20))
        top_bar.addWidget(icon_label)
        top_bar.addWidget(title_lbl)
        top_bar.addStretch()
        btn_add = make_btn("  Add Printer", ACCENT, icon=qta.icon('fa5s.plus', color='white'), height=40)
        btn_add.clicked.connect(self.add_printer)
        top_bar.addWidget(btn_add)
        layout.addLayout(top_bar)

        # ── List Card ──
        list_card_frame = QFrame()
        list_card_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE};
                border: 1.5px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        list_card_lay = QVBoxLayout(list_card_frame)
        list_card_lay.setContentsMargins(0, 0, 0, 0)

        self.printer_list = QListWidget()
        self.printer_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.printer_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 14px 18px;
                border-bottom: 1px solid {DIVIDER};
                color: {TEXT_PRI};
                font-size: 13px;
            }}
            QListWidget::item:selected {{
                background-color: {ACCENT_LIGHT};
                color: {ACCENT};
                border-left: 3px solid {ACCENT};
            }}
            QListWidget::item:hover:!selected {{
                background-color: {DIVIDER};
            }}
        """)
        self.printer_list.itemDoubleClicked.connect(self.edit_printer)
        list_card_lay.addWidget(self.printer_list)
        layout.addWidget(list_card_frame, stretch=1)

        # ── Action Row ──
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        btn_edit   = make_ghost_btn("  Edit Selected", icon=qta.icon('fa5s.edit', color=TEXT_SEC))
        btn_remove = make_danger_btn("  Remove", icon=qta.icon('fa5s.trash', color='white'))
        btn_edit.clicked.connect(self.edit_selected)
        btn_remove.clicked.connect(self.remove_printer)
        action_row.addWidget(btn_edit)
        action_row.addWidget(btn_remove)
        action_row.addStretch()
        layout.addLayout(action_row)

        outer.addWidget(content_widget, stretch=1)

        # ── Save Footer ──
        footer = QFrame()
        footer.setFixedHeight(64)
        footer.setStyleSheet(f"background-color: {SURFACE}; border-top: 1.5px solid {BORDER};")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(28, 0, 28, 0)
        f_layout.addStretch()
        btn_save = make_btn("  Save Printer Settings", ACCENT,
                            icon=qta.icon('fa5s.save', color='white'), height=42)
        btn_save.setMinimumWidth(200)
        btn_save.clicked.connect(self.save_settings)
        f_layout.addWidget(btn_save)
        outer.addWidget(footer)

        self.printers = []
        self.load_settings()

    def refresh_list(self):
        # ── Logic unchanged ──
        self.printer_list.clear()
        for p in self.printers:
            item = QListWidgetItem()
            roles_str  = ", ".join([r.upper() for r in p.get("roles", [])])
            details    = p.get("usb_name") if p.get("type") == "usb" else f"{p.get('ip')}:{p.get('port')}"
            item.setText(f"{p.get('name')}  ·  {p.get('type','').upper()} — {details}\nRoles: {roles_str}")
            item.setData(Qt.ItemDataRole.UserRole, p)
            icon_name = 'fa5s.receipt' if 'receipt' in p.get('roles', []) else 'fa5s.print'
            item.setIcon(qta.icon(icon_name, color=ACCENT))
            self.printer_list.addItem(item)

    def add_printer(self):
        # ── Logic unchanged ──
        dialog = PrinterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.printers.append(dialog.get_data())
            self.refresh_list()

    def edit_selected(self):
        if not self.printer_list.selectedItems(): return
        self.edit_printer(self.printer_list.selectedItems()[0])

    def edit_printer(self, item):
        # ── Logic unchanged ──
        idx  = self.printer_list.row(item)
        data = item.data(Qt.ItemDataRole.UserRole)
        dialog = PrinterDialog(self, data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.printers[idx] = dialog.get_data()
            self.refresh_list()

    def remove_printer(self):
        # ── Logic unchanged ──
        if not self.printer_list.selectedItems(): return
        row   = self.printer_list.currentRow()
        reply = QMessageBox.question(self, "Confirm", "Remove this printer configuration?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.printers.pop(row)
            self.refresh_list()

    def load_settings(self):
        # ── Logic unchanged ──
        config = load_config()
        self.printers = config.get("printers", [])
        if not self.printers:
            old_receipt = config.get("receipt_printer")
            old_kot     = config.get("kot_printer")
            if old_receipt:
                self.printers.append({
                    "name": "Receipt Printer", "type": old_receipt.get("type","usb"),
                    "usb_name": old_receipt.get("name"), "ip": old_receipt.get("ip"),
                    "port": old_receipt.get("port"), "roles": ["receipt"]
                })
            if old_kot and not old_kot.get("use_same"):
                self.printers.append({
                    "name": "Kitchen Printer", "type": old_kot.get("type","usb"),
                    "usb_name": old_kot.get("name"), "ip": old_kot.get("ip"),
                    "port": old_kot.get("port"), "roles": ["kot"]
                })
            elif old_kot and old_kot.get("use_same") and self.printers:
                if "kot" not in self.printers[0]["roles"]:
                    self.printers[0]["roles"].append("kot")
        self.refresh_list()

    def save_settings(self):
        # ── Logic unchanged ──
        config = load_config()
        config["printers"] = self.printers
        if save_config(config):
            QMessageBox.information(self, "Success", "Printer settings saved!")
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings.")


# ─── Database Settings Tab ─────────────────────────────────────────────────────

class DatabaseSettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {BG};")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        # ── Card ──
        c = QFrame()
        c.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE};
                border: 1.5px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        lay = QVBoxLayout(c)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)

        lay.addLayout(card_title("Database Management", 'fa5s.database', DANGER))
        lay.addWidget(divider_line())

        info_lbl = QLabel("⚠️  Manage your data carefully. Some actions are irreversible.")
        info_lbl.setStyleSheet(f"""
            color: {WARNING};
            font-size: 13px;
            font-style: italic;
            background-color: #FFF8EC;
            border: 1px solid #FDE68A;
            border-radius: 7px;
            padding: 10px 14px;
        """)
        info_lbl.setWordWrap(True)
        lay.addWidget(info_lbl)

        lay.addSpacing(6)

        btn_backup = make_btn("  Backup Data (JSON)", SUCCESS,
                              icon=qta.icon('fa5s.download', color='white'), height=44)
        btn_backup.clicked.connect(self.backup_data)
        lay.addWidget(btn_backup)

        btn_restore = make_danger_btn("  Restore Data (JSON)",
                                      icon=qta.icon('fa5s.upload', color='white'), height=44)
        btn_restore.clicked.connect(self.restore_data)
        lay.addWidget(btn_restore)

        lay.addStretch()
        outer.addWidget(c)
        outer.addStretch()

    def backup_data(self):
        # ── Logic unchanged ──
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Directory")
        if not folder: return
        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(folder, f"pos_backup_{timestamp}")
        os.makedirs(backup_path, exist_ok=True)
        try:
            collections = ["users","products","orders","inventory","expenses","shifts","customers","recipes","wastage"]
            for col_name in collections:
                data = list(db[col_name].find())
                for item in data:
                    item["_id"] = str(item["_id"])
                    for k, v in item.items():
                        if isinstance(v, datetime):
                            item[k] = v.isoformat()
                with open(os.path.join(backup_path, f"{col_name}.json"), "w") as f:
                    json.dump(data, f, indent=4, default=str)
            QMessageBox.information(self, "Success", f"Backup created at:\n{backup_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Backup failed: {str(e)}")

    def restore_data(self):
        # ── Logic unchanged ──
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Directory (containing JSON files)")
        if not folder: return
        reply = QMessageBox.question(self, "Confirm Restore",
                                     "Restoring will OVERWRITE existing data.\nAre you sure?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        try:
            collections = ["users","products","orders","inventory","expenses","shifts","customers","recipes","wastage"]
            restored_count = 0
            for col_name in collections:
                file_path = os.path.join(folder, f"{col_name}.json")
                if not os.path.exists(file_path): continue
                with open(file_path, "r") as f:
                    data = json.load(f)
                if not data: continue
                formatted_data = []
                for item in data:
                    if "_id" in item and isinstance(item["_id"], str):
                        try: item["_id"] = ObjectId(item["_id"])
                        except: pass
                    for k, v in item.items():
                        if isinstance(v, str) and len(v) > 10:
                            if "date" in k or "_at" in k or "timestamp" in k:
                                try: item[k] = datetime.fromisoformat(v)
                                except: pass
                    formatted_data.append(item)
                db[col_name].delete_many({})
                if formatted_data:
                    db[col_name].insert_many(formatted_data)
                restored_count += 1
            QMessageBox.information(self, "Success", f"Restore completed!\nRestored {restored_count} collections.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Restore failed: {str(e)}")


# ─── Categories Settings Tab ───────────────────────────────────────────────────

class CategoriesSettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {BG};")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        # ── Top Bar ──
        top_bar = QHBoxLayout()
        title_lbl = QLabel("Categories Management")
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {TEXT_PRI};")
        top_bar.addWidget(title_lbl)
        top_bar.addStretch()
        self.btn_add = make_btn("  Add Category", ACCENT,
                                icon=qta.icon('fa5s.plus', color='white'), height=38)
        self.btn_add.clicked.connect(self.add_category)
        top_bar.addWidget(self.btn_add)
        outer.addLayout(top_bar)

        # ── List Card ──
        list_card_frame = QFrame()
        list_card_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE};
                border: 1.5px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        lc_lay = QVBoxLayout(list_card_frame)
        lc_lay.setContentsMargins(0, 0, 0, 0)

        self.categories_list = QListWidget()
        self.categories_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.categories_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 13px 18px;
                border-bottom: 1px solid {DIVIDER};
                color: {TEXT_PRI};
            }}
            QListWidget::item:selected {{
                background-color: {ACCENT_LIGHT};
                color: {ACCENT};
                border-left: 3px solid {ACCENT};
            }}
            QListWidget::item:hover:!selected {{
                background-color: {DIVIDER};
            }}
        """)
        self.categories_list.itemDoubleClicked.connect(self.edit_category)
        lc_lay.addWidget(self.categories_list)
        outer.addWidget(list_card_frame, stretch=1)

        # ── Action Row ──
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.btn_edit   = make_ghost_btn("  Edit", icon=qta.icon('fa5s.edit', color=TEXT_SEC))
        self.btn_delete = make_danger_btn("  Delete", icon=qta.icon('fa5s.trash', color='white'))
        self.btn_refresh= make_ghost_btn("  Refresh", icon=qta.icon('fa5s.sync', color=TEXT_SEC))
        self.btn_edit.clicked.connect(self.edit_category)
        self.btn_delete.clicked.connect(self.delete_category)
        self.btn_refresh.clicked.connect(self.load_categories)
        action_row.addWidget(self.btn_edit)
        action_row.addWidget(self.btn_delete)
        action_row.addStretch()
        action_row.addWidget(self.btn_refresh)
        outer.addLayout(action_row)

        hint = QLabel("Double-click a row to edit")
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        outer.addWidget(hint)

        self.load_categories()

    def load_categories(self):
        # ── Logic unchanged ──
        self.categories_list.clear()
        seed_default_categories()
        categories = get_categories()
        for category in categories:
            item_text = category['name']
            if category.get('description'): item_text += f"  —  {category['description']}"
            if category.get('section'):     item_text += f"  [{category['section']}]"
            list_item = QListWidgetItem(item_text)
            list_item.setData(Qt.ItemDataRole.UserRole, category)
            self.categories_list.addItem(list_item)

    def add_category(self):
        # ── Logic unchanged ──
        dialog = CategoryDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name         = dialog.name_edit.text().strip()
            description  = dialog.desc_edit.text().strip()
            section      = dialog.section_combo.currentText()
            color        = dialog.color_edit.text().strip()
            printer_role = dialog.printer_role_edit.text().strip() or f"kot-{section}"
            if not name:
                QMessageBox.warning(self, "Error", "Category name is required!"); return
            success = add_category(name, description, color, section, printer_role)
            if success:
                QMessageBox.information(self, "Success", "Category added successfully!")
                self.load_categories()
            else:
                QMessageBox.warning(self, "Error", "Category with this name already exists!")

    def edit_category(self):
        # ── Logic unchanged ──
        current_item = self.categories_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a category to edit!"); return
        category = current_item.data(Qt.ItemDataRole.UserRole)
        dialog   = CategoryDialog(self, category)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name         = dialog.name_edit.text().strip()
            description  = dialog.desc_edit.text().strip()
            section      = dialog.section_combo.currentText()
            color        = dialog.color_edit.text().strip()
            printer_role = dialog.printer_role_edit.text().strip() or f"kot-{section}"
            if not name:
                QMessageBox.warning(self, "Error", "Category name is required!"); return
            success = update_category(str(category['_id']), name, description, color, section, printer_role)
            if success:
                QMessageBox.information(self, "Success", "Category updated!")
                self.load_categories()
            else:
                QMessageBox.warning(self, "Error", "Category with this name already exists!")

    def delete_category(self):
        # ── Logic unchanged ──
        current_item = self.categories_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a category to delete!"); return
        category = current_item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Delete '{category['name']}'?\n\nProducts using this category must be updated manually.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            success = delete_category(str(category['_id']))
            if success:
                QMessageBox.information(self, "Success", "Category deleted!")
                self.load_categories()
            else:
                QMessageBox.warning(self, "Error", "Cannot delete: Products still using this category!")


# ─── Category Dialog ───────────────────────────────────────────────────────────

class CategoryDialog(QDialog):
    def __init__(self, parent=None, category=None):
        super().__init__(parent)
        self.setWindowTitle("Category Details")
        self.setModal(True)
        self.setFixedSize(420, 400)
        self.setStyleSheet(GLOBAL_STYLE + f"QDialog {{ background-color: {SURFACE}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_lbl = QLabel("Add Category" if not category else "Edit Category")
        title_lbl.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {TEXT_PRI};")
        layout.addWidget(title_lbl)
        layout.addWidget(divider_line())
        layout.addSpacing(4)

        def row_lbl(t):
            l = QLabel(t)
            l.setStyleSheet(f"color: {TEXT_SEC}; font-weight: 600; font-size: 12px; margin-bottom: 3px;")
            return l

        layout.addWidget(row_lbl("Category Name *"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Burger, Pizza, Drink")
        layout.addWidget(self.name_edit)

        layout.addWidget(row_lbl("Description"))
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Brief description of the category")
        layout.addWidget(self.desc_edit)

        layout.addWidget(row_lbl("Kitchen Section *"))
        self.section_combo = QComboBox()
        self.section_combo.addItems(["kitchen", "bar", "pizza", "dessert", "grill", "salad"])
        layout.addWidget(self.section_combo)

        layout.addWidget(row_lbl("Display Color"))
        self.color_edit = QLineEdit("#4F46E5")
        self.color_edit.setPlaceholderText("#4F46E5")
        layout.addWidget(self.color_edit)

        layout.addWidget(row_lbl("Printer Role (Optional)"))
        self.printer_role_edit = QLineEdit()
        self.printer_role_edit.setPlaceholderText("e.g. kot-bar  (auto-generated if empty)")
        layout.addWidget(self.printer_role_edit)

        layout.addStretch()
        layout.addWidget(divider_line())

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel_btn = make_ghost_btn("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn   = make_btn("  Save", ACCENT, icon=qta.icon('fa5s.check', color='white'), height=42)
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        if category:
            self.name_edit.setText(category.get('name', ''))
            self.desc_edit.setText(category.get('description', ''))
            self.section_combo.setCurrentText(category.get('section', 'kitchen'))
            self.color_edit.setText(category.get('color', '#4F46E5'))
            self.printer_role_edit.setText(category.get('printer_role', ''))


# ─── Print Design Tab ──────────────────────────────────────────────────────────

class PrintDesignTab(QWidget):
    """Settings tab for customising KOT and Bill print layouts."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {BG};")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background-color: {BG};")

        content = QWidget()
        content.setStyleSheet(f"background-color: {BG};")
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(28, 24, 28, 24)
        self._layout.setSpacing(18)

        self._build_bill_card()
        self._build_kot_card()
        self._build_misc_card()
        self._layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        # ── Save footer ──
        footer = QFrame()
        footer.setFixedHeight(64)
        footer.setStyleSheet(f"QFrame {{ background-color: {SURFACE}; border-top: 1.5px solid {BORDER}; }}")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(28, 0, 28, 0)

        btn_preview_both = make_ghost_btn("  Preview Both", icon=qta.icon('fa5s.eye', color=TEXT_SEC))
        btn_preview_both.clicked.connect(self._open_preview_both)
        fl.addWidget(btn_preview_both)
        fl.addStretch()
        btn_save = make_btn("  Save Design Settings", ACCENT,
                            icon=qta.icon('fa5s.save', color='white'), height=42)
        btn_save.setMinimumWidth(200)
        btn_save.clicked.connect(self._save)
        fl.addWidget(btn_save)
        outer.addWidget(footer)

        self._load()

    # ── Cards ──────────────────────────────────────────────────────────────────

    def _card(self):
        f = QFrame()
        f.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE};
                border: 1.5px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        return f

    def _row_lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {TEXT_SEC}; font-weight: 600; font-size: 12px;")
        return l

    def _chk(self, text):
        cb = QCheckBox(text)
        cb.setStyleSheet(f"font-size: 13px; color: {TEXT_PRI};")
        return cb

    def _build_bill_card(self):
        c = self._card()
        lay = QVBoxLayout(c)
        lay.setContentsMargins(20, 18, 20, 20)
        lay.setSpacing(12)
        lay.addLayout(card_title("Bill / Receipt Design", 'fa5s.file-invoice', ACCENT))
        lay.addWidget(divider_line())

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.bill_font_size = QSpinBox()
        self.bill_font_size.setRange(8, 18)
        self.bill_font_size.setValue(11)
        self.bill_font_size.setSuffix(" px")

        self.bill_paper_size = QComboBox()
        self.bill_paper_size.addItems(["58mm", "80mm"])
        self.bill_paper_size.setCurrentText("80mm")

        self.bill_copy = QComboBox()
        self.bill_copy.addItems(["(None)", "ORIGINAL", "DUPLICATE", "TRIPLICATE"])

        self.bill_header_extra = QLineEdit()
        self.bill_header_extra.setPlaceholderText("Extra header line (e.g. GST# 123456)")

        self.bill_footer_extra = QLineEdit()
        self.bill_footer_extra.setPlaceholderText("Extra footer line (e.g. WhatsApp: 0300-XXXXXXX)")

        for lbl_text, widget in [
            ("Font Size:", self.bill_font_size),
            ("Paper Size:", self.bill_paper_size),
            ("Bill Copy Label:", self.bill_copy),
            ("Extra Header:", self.bill_header_extra),
            ("Extra Footer:", self.bill_footer_extra),
        ]:
            form.addRow(self._row_lbl(lbl_text), widget)
        lay.addLayout(form)
        lay.addWidget(divider_line())

        # Checkboxes grid
        chk_lbl = QLabel("Show / Hide Fields:")
        chk_lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {TEXT_PRI};")
        lay.addWidget(chk_lbl)

        self.bill_show_logo     = self._chk("Show Logo")
        self.bill_show_token    = self._chk("Show Token Number")
        self.bill_show_customer = self._chk("Show Customer Name")
        self.bill_show_waiter   = self._chk("Show Waiter Name")
        self.bill_show_tax      = self._chk("Show Tax / GST")
        self.bill_show_service  = self._chk("Show Service Charge")
        self.bill_show_discount = self._chk("Show Discount")

        grid = QGridLayout()
        grid.setSpacing(6)
        chks = [
            self.bill_show_logo, self.bill_show_token,
            self.bill_show_customer, self.bill_show_waiter,
            self.bill_show_tax, self.bill_show_service,
            self.bill_show_discount,
        ]
        for i, chk in enumerate(chks):
            grid.addWidget(chk, i // 2, i % 2)
        lay.addLayout(grid)

        self._layout.addWidget(c)

    def _build_kot_card(self):
        c = self._card()
        lay = QVBoxLayout(c)
        lay.setContentsMargins(20, 18, 20, 20)
        lay.setSpacing(12)
        lay.addLayout(card_title("KOT — Kitchen Order Ticket Design", 'fa5s.utensils', "#f97316"))
        lay.addWidget(divider_line())

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.kot_font_size = QSpinBox()
        self.kot_font_size.setRange(10, 24)
        self.kot_font_size.setValue(14)
        self.kot_font_size.setSuffix(" px")

        self.kot_title = QLineEdit()
        self.kot_title.setPlaceholderText("e.g. KITCHEN ORDER TICKET")

        for lbl_text, widget in [
            ("Font Size:", self.kot_font_size),
            ("KOT Title:", self.kot_title),
        ]:
            form.addRow(self._row_lbl(lbl_text), widget)
        lay.addLayout(form)
        lay.addWidget(divider_line())

        chk_lbl = QLabel("Show / Hide Fields:")
        chk_lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {TEXT_PRI};")
        lay.addWidget(chk_lbl)

        self.kot_show_table    = self._chk("Show Table Number")
        self.kot_show_token    = self._chk("Show Token Number")
        self.kot_show_type     = self._chk("Show Order Type Badge")
        self.kot_show_waiter   = self._chk("Show Waiter Name")
        self.kot_show_notes    = self._chk("Show Item Notes")
        self.kot_show_cat_hdr  = self._chk("Show Category Headers")

        grid = QGridLayout()
        grid.setSpacing(6)
        chks = [
            self.kot_show_table, self.kot_show_token,
            self.kot_show_type, self.kot_show_waiter,
            self.kot_show_notes, self.kot_show_cat_hdr,
        ]
        for i, chk in enumerate(chks):
            grid.addWidget(chk, i // 2, i % 2)
        lay.addLayout(grid)

        self._layout.addWidget(c)

    def _build_misc_card(self):
        c = self._card()
        lay = QVBoxLayout(c)
        lay.setContentsMargins(20, 18, 20, 20)
        lay.setSpacing(12)
        lay.addLayout(card_title("Print Behaviour", 'fa5s.cogs', TEXT_SEC))
        lay.addWidget(divider_line())

        self.chk_preview = self._chk(
            "Show Print Preview before printing (KOT & Bill)"
        )
        lay.addWidget(self.chk_preview)
        note = QLabel("When enabled, a preview window appears before every print job so you can confirm or cancel.")
        note.setStyleSheet(f"font-size: 11px; color: {TEXT_SEC}; padding-left: 26px;")
        note.setWordWrap(True)
        lay.addWidget(note)

        self._layout.addWidget(c)

    # ── Load / Save ────────────────────────────────────────────────────────────

    def _load(self):
        try:
            config = load_config()
            pd = config.get("print_design", {})
            bill = pd.get("bill", {})
            kot  = pd.get("kot", {})

            self.bill_font_size.setValue(int(bill.get("font_size", 11)))
            self.bill_paper_size.setCurrentText(bill.get("paper_size", "80mm"))
            copy_val = bill.get("bill_copy", "")
            self.bill_copy.setCurrentText(copy_val if copy_val else "(None)")
            self.bill_header_extra.setText(bill.get("header_extra", ""))
            self.bill_footer_extra.setText(bill.get("footer_extra", ""))
            self.bill_show_logo.setChecked(bill.get("show_logo", True))
            self.bill_show_token.setChecked(bill.get("show_token", True))
            self.bill_show_customer.setChecked(bill.get("show_customer", True))
            self.bill_show_waiter.setChecked(bill.get("show_waiter", True))
            self.bill_show_tax.setChecked(bill.get("show_tax", True))
            self.bill_show_service.setChecked(bill.get("show_service_charge", True))
            self.bill_show_discount.setChecked(bill.get("show_discount", True))

            self.kot_font_size.setValue(int(kot.get("font_size", 14)))
            self.kot_title.setText(kot.get("kot_title", "KITCHEN ORDER TICKET"))
            self.kot_show_table.setChecked(kot.get("show_table", True))
            self.kot_show_token.setChecked(kot.get("show_token", True))
            self.kot_show_type.setChecked(kot.get("show_order_type", True))
            self.kot_show_waiter.setChecked(kot.get("show_waiter", True))
            self.kot_show_notes.setChecked(kot.get("show_notes", True))
            self.kot_show_cat_hdr.setChecked(kot.get("show_category_headers", True))

            self.chk_preview.setChecked(pd.get("preview_before_print", False))
        except Exception as e:
            print(f"PrintDesignTab load error: {e}")

    def _save(self):
        try:
            config = load_config()
            copy_val = self.bill_copy.currentText()
            if copy_val == "(None)":
                copy_val = ""
            config["print_design"] = {
                "bill": {
                    "font_size": self.bill_font_size.value(),
                    "paper_size": self.bill_paper_size.currentText(),
                    "bill_copy": copy_val,
                    "header_extra": self.bill_header_extra.text().strip(),
                    "footer_extra": self.bill_footer_extra.text().strip(),
                    "show_logo": self.bill_show_logo.isChecked(),
                    "show_token": self.bill_show_token.isChecked(),
                    "show_customer": self.bill_show_customer.isChecked(),
                    "show_waiter": self.bill_show_waiter.isChecked(),
                    "show_tax": self.bill_show_tax.isChecked(),
                    "show_service_charge": self.bill_show_service.isChecked(),
                    "show_discount": self.bill_show_discount.isChecked(),
                },
                "kot": {
                    "font_size": self.kot_font_size.value(),
                    "kot_title": self.kot_title.text().strip() or "KITCHEN ORDER TICKET",
                    "show_table": self.kot_show_table.isChecked(),
                    "show_token": self.kot_show_token.isChecked(),
                    "show_order_type": self.kot_show_type.isChecked(),
                    "show_waiter": self.kot_show_waiter.isChecked(),
                    "show_notes": self.kot_show_notes.isChecked(),
                    "show_category_headers": self.kot_show_cat_hdr.isChecked(),
                },
                "preview_before_print": self.chk_preview.isChecked(),
            }
            save_config(config)
            QMessageBox.information(self, "Saved", "Print design settings saved successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not save: {e}")

    def _open_preview_both(self):
        from frontend.dialogs.print_preview_dialog import PrintPreviewDialog
        dummy = {
            "invoice_no": "PREVIEW-001",
            "token_no": "42",
            "table_no": "Table 5",
            "order_type": "Dine In",
            "customer_name": "Test Customer",
            "waiter": "Ahmed",
            "items": [
                {"name": "Zinger Burger", "qty": 2, "price": 450, "category": "Burgers", "note": "Extra spicy"},
                {"name": "Classic Burger", "qty": 1, "price": 350, "category": "Burgers", "note": ""},
                {"name": "Coke 500ml",    "qty": 3, "price": 120, "category": "Drinks",  "note": ""},
                {"name": "Garlic Bread",  "qty": 1, "price": 180, "category": "Sides",   "note": ""},
            ],
            "subtotal": 1690, "discount": 100, "service_charge": 84,
            "tax": 270, "grand_total": 1944, "created_at": __import__('datetime').datetime.now(),
        }
        dlg = PrintPreviewDialog(dummy, mode="both", parent=self)
        dlg.exec()
