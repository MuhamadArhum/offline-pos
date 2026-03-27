from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QPushButton, QGridLayout, QScrollArea,
                             QTableWidget, QHeaderView, QLineEdit, QComboBox,
                             QMessageBox, QStackedWidget, QDialog, QRadioButton,
                             QButtonGroup, QDoubleSpinBox, QAbstractItemView,
                             QTableWidgetItem, QTabWidget, QInputDialog, QSizePolicy,
                             QCheckBox, QDateEdit, QProgressBar, QSpinBox)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QDate
from PyQt6.QtGui import QColor, QIcon, QFont, QPixmap, QPainter, QBrush, QPen, QLinearGradient
import qtawesome as qta
from datetime import datetime, timedelta
from bson.objectid import ObjectId
import os
from backend.core.config import get_setting, resolve_resource_path
from frontend.pages.supplier_page import SupplierPage
from backend.services.supplier_service import get_suppliers
from backend.services.menu_service import get_items as get_menu_items, add_item as add_menu_item
from backend.services.recipe_service import get_recipe, add_recipe
from backend.services.wastage_service import get_wastage_reasons, record_wastage, get_wastage_paginated
from backend.services.category_service import get_category_names
from frontend.pages.settings_page import CategoriesSettingsTab

from backend.services.inventory_service import (
    get_inventory, get_inventory_item, add_stock, deduct_stock,
    update_inventory_item, delete_inventory_item, low_stock_items,
    get_stock_history, get_inventory_value, reconcile_stock, get_batches, remove_batch
)
from backend.core.permissions import has_permission
from frontend.theme import Theme
from frontend.shared_ui import (
    GLOBAL_STYLE, BG, SURFACE, BORDER, DIVIDER, ACCENT, ACCENT_DARK, ACCENT_LIGHT,
    SUCCESS, DANGER, WARNING, INFO, TEXT_PRI, TEXT_SEC, TEXT_MUTED,
    make_btn, make_ghost_btn, make_danger_btn, card, divider_line,
    section_header_lbl, card_title, page_header, C
)

import time
import random

# ─────────────────────────────────────────────────────────────────────────────
#  ULTRA‑MODERN DESIGN TOKENS (refined)
# ─────────────────────────────────────────────────────────────────────────────
_PRIMARY     = "#6366F1"      # indigo
_PRIMARY_DK  = "#4F46E5"
_PRIMARY_LT  = "#EEF2FF"
_SUCCESS     = "#10B981"      # emerald
_SUCCESS_LT  = "#D1FAE5"
_DANGER      = "#EF4444"      # red
_DANGER_LT   = "#FEE2E2"
_WARNING     = "#F59E0B"      # amber
_WARNING_LT  = "#FEF3C7"
_INFO        = "#0EA5E9"      # sky
_INFO_LT     = "#E0F2FE"
_DARK1       = "#0F172A"      # slate-900
_DARK2       = "#1E293B"      # slate-800
_TEXT_PRI    = "#0F172A"
_TEXT_SEC    = "#475569"
_TEXT_HINT   = "#94A3B8"
_BG          = "#F8FAFC"
_SURFACE     = "#FFFFFF"
_BORDER      = "#E2E8F0"
_DIVIDER     = "#F1F5F9"
_SHADOW      = "0 4px 12px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.1)"
_SHADOW_HOVER = "0 8px 24px rgba(0, 0, 0, 0.12), 0 2px 4px rgba(0, 0, 0, 0.08)"

# ─────────────────────────────────────────────────────────────────────────────
#  MASTER STYLESHEET (modern, refined)
# ─────────────────────────────────────────────────────────────────────────────
INV_STYLE = f"""
* {{
    font-family: 'Segoe UI', 'SF Pro Display', system-ui, -apple-system, sans-serif;
}}

/* ── TABS ───────────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background: {_BG};
}}
QTabBar::tab {{
    background: transparent;
    color: {_TEXT_SEC};
    border: none;
    border-bottom: 3px solid transparent;
    padding: 12px 24px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.3px;
    text-transform: uppercase;
}}
QTabBar::tab:hover {{
    color: {_PRIMARY};
    background: rgba(99, 102, 241, 0.04);
    border-radius: 8px 8px 0 0;
}}
QTabBar::tab:selected {{
    color: {_PRIMARY};
    border-bottom: 3px solid {_PRIMARY};
    background: transparent;
}}

/* ── TABLES ─────────────────────────────────────────────────────────────── */
QTableWidget {{
    background: {_SURFACE};
    border: none;
    gridline-color: transparent;
    selection-background-color: {_PRIMARY_LT};
    selection-color: {_PRIMARY_DK};
    alternate-background-color: #FAFCFE;
    outline: none;
    font-size: 13px;
}}
QTableWidget::item {{
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid {_DIVIDER};
    color: {_TEXT_PRI};
}}
QTableWidget::item:selected {{
    background: {_PRIMARY_LT};
    color: {_PRIMARY_DK};
}}
QHeaderView::section {{
    background: {_BG};
    color: {_TEXT_SEC};
    font-size: 11px;
    font-weight: 800;
    padding: 12px 8px;
    border: none;
    border-bottom: 2px solid {_BORDER};
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}
QHeaderView::section:hover {{
    background: {_PRIMARY_LT};
    color: {_PRIMARY};
}}
QHeaderView {{
    border: none;
}}

/* ── INPUTS ─────────────────────────────────────────────────────────────── */
QLineEdit {{
    background: {_SURFACE};
    border: 1.5px solid {_BORDER};
    border-radius: 10px;
    padding: 0 14px;
    color: {_TEXT_PRI};
    font-size: 13px;
    selection-background-color: {_PRIMARY_LT};
}}
QLineEdit:focus {{
    border-color: {_PRIMARY};
    box-shadow: 0 0 0 3px {_PRIMARY_LT};
}}

QDoubleSpinBox, QSpinBox {{
    background: {_SURFACE};
    border: 1.5px solid {_BORDER};
    border-radius: 10px;
    padding: 0 8px;
    color: {_TEXT_PRI};
    font-size: 13px;
    font-weight: 600;
}}
QDoubleSpinBox:focus, QSpinBox:focus {{
    border-color: {_PRIMARY};
    box-shadow: 0 0 0 3px {_PRIMARY_LT};
}}

QComboBox {{
    background: {_SURFACE};
    border: 1.5px solid {_BORDER};
    border-radius: 10px;
    padding: 0 12px;
    color: {_TEXT_PRI};
    font-size: 13px;
    font-weight: 600;
}}
QComboBox:focus {{
    border-color: {_PRIMARY};
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox QAbstractItemView {{
    background: {_SURFACE};
    border: 1.5px solid {_BORDER};
    border-radius: 10px;
    selection-background-color: {_PRIMARY_LT};
    selection-color: {_PRIMARY_DK};
    padding: 6px;
    outline: none;
}}

QDateEdit {{
    background: {_SURFACE};
    border: 1.5px solid {_BORDER};
    border-radius: 10px;
    padding: 0 12px;
    color: {_TEXT_PRI};
    font-size: 13px;
}}
QDateEdit:focus {{
    border-color: {_PRIMARY};
}}

QCheckBox {{
    font-size: 13px;
    font-weight: 600;
    color: {_TEXT_SEC};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1.5px solid {_BORDER};
    border-radius: 5px;
    background: {_SURFACE};
}}
QCheckBox::indicator:checked {{
    background: {_PRIMARY};
    border-color: {_PRIMARY};
}}

/* ── SCROLLBARS ─────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #CBD5E1;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #94A3B8;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: #CBD5E1;
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #94A3B8;
}}

/* ── DIALOGS ────────────────────────────────────────────────────────────── */
QDialog {{
    background: {_BG};
    border-radius: 24px;
}}
QMessageBox {{
    background: {_SURFACE};
    border-radius: 16px;
}}
QMessageBox QPushButton {{
    background: {_PRIMARY};
    color: white;
    border: none;
    border-radius: 10px;
    padding: 8px 28px;
    font-weight: 700;
    min-width: 90px;
}}
QMessageBox QPushButton:hover {{
    background: {_PRIMARY_DK};
}}
QToolTip {{
    background: {_DARK2};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 600;
}}
"""

# ─────────────────────────────────────────────────────────────────────────────
#  EXTENDED HELPERS (even more polish)
# ─────────────────────────────────────────────────────────────────────────────
def _divider():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background:{_BORDER}; border:none; margin:8px 0;")
    return f

def _card(radius=16, with_shadow=False):
    f = QFrame()
    shadow = f"box-shadow:{_SHADOW};" if with_shadow else ""
    f.setStyleSheet(f"QFrame {{ background:{_SURFACE}; border-radius:{radius}px; border:1px solid {_BORDER}; {shadow} }}")
    return f

def _badge(text, bg, fg="white", radius=20, bold=True):
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    weight = "800" if bold else "600"
    lbl.setStyleSheet(
        f"background:{bg}; color:{fg}; font-size:11px; font-weight:{weight};"
        f" padding:4px 14px; border-radius:{radius}px; border:none; letter-spacing:0.3px;"
    )
    return lbl

def _icon_widget(icon_name, color, size=20, bg=None, radius=10, padding=4):
    """Square container with icon, optionally with background."""
    container = QLabel()
    container.setFixedSize(size + 2*padding, size + 2*padding)
    container.setAlignment(Qt.AlignmentFlag.AlignCenter)
    container.setPixmap(qta.icon(icon_name, color=color).pixmap(size, size))
    if bg:
        container.setStyleSheet(f"background:{bg}; border-radius:{radius}px;")
    return container

def _action_btn(text, icon_name, bg, hover_bg, fg="white", height=40, radius=10):
    btn = QPushButton(f"  {text}")
    btn.setIcon(qta.icon(icon_name, color=fg))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
    btn.setStyleSheet(
        f"QPushButton {{ background:{bg}; color:{fg}; border:none; border-radius:{radius}px;"
        f" font-size:13px; font-weight:700; padding:0 18px; }}"
        f"QPushButton:hover {{ background:{hover_bg}; }}"
        f"QPushButton:pressed {{ background:{hover_bg}; opacity:0.8; }}"
    )
    return btn

def _flat_btn(text, color, hover_bg, height=36, radius=9):
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
    btn.setStyleSheet(
        f"QPushButton {{ background:transparent; color:{color}; border:1.5px solid {color};"
        f" border-radius:{radius}px; font-size:12px; font-weight:600; padding:0 14px; }}"
        f"QPushButton:hover {{ background:{hover_bg}; }}"
    )
    return btn

def _icon_btn(icon_name, icon_color, bg, hover_bg, tooltip="", fixed_size=(32, 32), radius=8):
    btn = QPushButton()
    btn.setIcon(qta.icon(icon_name, color=icon_color))
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedSize(*fixed_size)
    btn.setStyleSheet(
        f"QPushButton {{ background:{bg}; border:1px solid {_BORDER}; border-radius:{radius}px; }}"
        f"QPushButton:hover {{ background:{hover_bg}; border-color:{icon_color}; }}"
    )
    return btn

def _section_title(text):
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"font-size:11px; font-weight:800; color:{_TEXT_HINT};"
        f" letter-spacing:0.8px; background:transparent; border:none;"
    )
    return lbl

def _field_lbl(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size:11px; font-weight:700; color:{_TEXT_SEC};"
        f" letter-spacing:0.3px; background:transparent; border:none;"
    )
    return lbl

def _gradient_header(title, subtitle=None, icon_name='fa5s.boxes', icon_color=_PRIMARY):
    """Creates a consistent gradient header for dialogs/pages."""
    hdr = QFrame()
    hdr.setFixedHeight(80)
    hdr.setStyleSheet(
        f"QFrame {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        f"stop:0 {_DARK1}, stop:1 {_DARK2}); border-top-left-radius:24px; border-top-right-radius:24px; }}"
    )
    layout = QHBoxLayout(hdr)
    layout.setContentsMargins(24, 0, 24, 0)
    layout.setSpacing(14)

    icon = _icon_widget(icon_name, icon_color, size=30, bg=_PRIMARY_LT, radius=12, padding=8)
    text_col = QVBoxLayout()
    text_col.setSpacing(2)
    title_lbl = QLabel(title)
    title_lbl.setStyleSheet("color:white; font-size:20px; font-weight:800; border:none; background:transparent;")
    text_col.addWidget(title_lbl)
    if subtitle:
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet(f"color:{_TEXT_HINT}; font-size:12px; font-weight:500; border:none; background:transparent;")
        text_col.addWidget(sub_lbl)
    layout.addWidget(icon)
    layout.addLayout(text_col)
    layout.addStretch()
    return hdr

def _dialog_footer(accept_text="Save", reject_text="Cancel", accept_icon="fa5s.check", reject_icon="fa5s.times"):
    """Returns a footer frame with accept/reject buttons, to be added to a dialog layout."""
    footer = QFrame()
    footer.setStyleSheet(f"QFrame {{ background:{_SURFACE}; border-top:1px solid {_BORDER}; "
                         f"border-bottom-left-radius:24px; border-bottom-right-radius:24px; }}")
    layout = QHBoxLayout(footer)
    layout.setContentsMargins(24, 16, 24, 16)

    btn_cancel = QPushButton(f"  {reject_text}")
    btn_cancel.setIcon(qta.icon(reject_icon, color=_TEXT_SEC))
    btn_cancel.setFixedHeight(44)
    btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_cancel.setStyleSheet(
        f"QPushButton {{ background:transparent; border:1.5px solid {_BORDER}; border-radius:12px;"
        f" color:{_TEXT_SEC}; font-weight:600; padding:0 24px; font-size:13px; }}"
        f"QPushButton:hover {{ background:{_BG}; }}"
    )

    btn_accept = QPushButton(f"  {accept_text}")
    btn_accept.setIcon(qta.icon(accept_icon, color='white'))
    btn_accept.setFixedHeight(44)
    btn_accept.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_accept.setStyleSheet(
        f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        f"stop:0 {_PRIMARY}, stop:1 #818CF8); color:white; border:none; border-radius:12px;"
        f" font-size:14px; font-weight:700; padding:0 32px; }}"
        f"QPushButton:hover {{ background:{_PRIMARY_DK}; }}"
    )

    layout.addWidget(btn_cancel)
    layout.addStretch()
    layout.addWidget(btn_accept)
    return footer, btn_cancel, btn_accept


# ─────────────────────────────────────────────────────────────────────────────
#  ADD STOCK DIALOG (refined)
# ─────────────────────────────────────────────────────────────────────────────
class AddStockDialog(QDialog):
    def __init__(self, item_name=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Stock")
        self.setMinimumSize(500, 700)
        self.setMaximumSize(600, 850)
        self.setStyleSheet(INV_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        layout.addWidget(_gradient_header("Add Stock", "Record incoming inventory", 'fa5s.plus-circle', _SUCCESS))

        # Body
        body = QWidget()
        body.setStyleSheet(f"background:{_BG};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 24, 28, 24)
        bl.setSpacing(16)

        def _row(label_text, widget):
            bl.addWidget(_field_lbl(label_text))
            bl.addWidget(widget)

        self.item_name = QLineEdit(item_name or "")
        self.item_name.setPlaceholderText("e.g. Chicken Breast")
        _row("ITEM NAME *", self.item_name)

        row_qty_cost = QHBoxLayout()
        row_qty_cost.setSpacing(16)
        qty_box = QVBoxLayout(); qty_box.setSpacing(4)
        qty_box.addWidget(_field_lbl("QUANTITY *"))
        self.qty = QDoubleSpinBox()
        self.qty.setRange(0, 1_000_000); self.qty.setValue(1); self.qty.setDecimals(3)
        self.qty.setMinimumHeight(38)
        self.qty.setMaximumHeight(42)
        qty_box.addWidget(self.qty)
        cost_box = QVBoxLayout(); cost_box.setSpacing(4)
        cost_box.addWidget(_field_lbl("COST PER UNIT"))
        self.cost = QDoubleSpinBox()
        self.cost.setRange(0, 1_000_000); self.cost.setValue(0); self.cost.setDecimals(2); self.cost.setPrefix("Rs ")
        self.cost.setMinimumHeight(38)
        self.cost.setMaximumHeight(42)
        cost_box.addWidget(self.cost)
        row_qty_cost.addLayout(qty_box); row_qty_cost.addLayout(cost_box)
        bl.addLayout(row_qty_cost)

        row_batch_expiry = QHBoxLayout()
        row_batch_expiry.setSpacing(16)
        batch_box = QVBoxLayout(); batch_box.setSpacing(4)
        batch_box.addWidget(_field_lbl("BATCH NO (OPTIONAL)"))
        self.batch_no = QLineEdit()
        self.batch_no.setPlaceholderText("e.g. BATCH-001")
        self.batch_no.setMinimumHeight(38)
        self.batch_no.setMaximumHeight(42)
        batch_box.addWidget(self.batch_no)
        expiry_box = QVBoxLayout(); expiry_box.setSpacing(4)
        expiry_box.addWidget(_field_lbl("EXPIRY DATE"))
        self.expiry = QDateEdit()
        self.expiry.setCalendarPopup(True)
        self.expiry.setDate(QDate.currentDate().addDays(30))
        self.expiry.setMinimumHeight(38)
        self.expiry.setMaximumHeight(42)
        expiry_box.addWidget(self.expiry)
        row_batch_expiry.addLayout(batch_box); row_batch_expiry.addLayout(expiry_box)
        bl.addLayout(row_batch_expiry)

        self.category = QComboBox()
        self.category.addItems(["General", "Food", "Beverages", "Supplies", "Equipment"])
        self.category.setMinimumHeight(38)
        self.category.setMaximumHeight(42)
        _row("CATEGORY", self.category)

        self.supplier = QComboBox()
        self.supplier.setMinimumHeight(38)
        self.supplier.setMaximumHeight(42)
        self._supplier_ids = []
        try:
            sups = get_suppliers()
            self.supplier.addItem("None"); self._supplier_ids.append(None)
            for s in sups:
                label = s.get("name") or str(s.get("_id"))
                self.supplier.addItem(label); self._supplier_ids.append(str(s.get("_id")))
        except Exception:
            self.supplier.addItem("None"); self._supplier_ids.append(None)
        _row("SUPPLIER (OPTIONAL)", self.supplier)

        row_unit_conv = QHBoxLayout()
        row_unit_conv.setSpacing(16)
        unit_box = QVBoxLayout(); unit_box.setSpacing(4)
        unit_box.addWidget(_field_lbl("PURCHASE UNIT"))
        self.purchase_unit = QLineEdit()
        self.purchase_unit.setPlaceholderText("e.g. kg, litre")
        self.purchase_unit.setMinimumHeight(38)
        self.purchase_unit.setMaximumHeight(42)
        unit_box.addWidget(self.purchase_unit)
        conv_box = QVBoxLayout(); conv_box.setSpacing(4)
        conv_box.addWidget(_field_lbl("CONVERSION FACTOR"))
        self.conversion = QDoubleSpinBox()
        self.conversion.setRange(1, 1_000_000); self.conversion.setValue(1); self.conversion.setDecimals(4)
        self.conversion.setMinimumHeight(38)
        self.conversion.setMaximumHeight(42)
        conv_box.addWidget(self.conversion)
        row_unit_conv.addLayout(unit_box); row_unit_conv.addLayout(conv_box)
        bl.addLayout(row_unit_conv)

        layout.addWidget(body, stretch=1)

        # Footer
        footer, btn_cancel, btn_save = _dialog_footer("Add Stock", "Cancel", "fa5s.check-circle", "fa5s.times")
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self.accept)
        layout.addWidget(footer)


# ─────────────────────────────────────────────────────────────────────────────
#  ADD MENU ITEM DIALOG (refined)
# ─────────────────────────────────────────────────────────────────────────────
class AddMenuItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Menu Item")
        self.setMinimumSize(440, 440)
        self.setMaximumSize(520, 520)
        self.setStyleSheet(INV_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(_gradient_header("Add Menu Item", "Create new menu item", 'fa5s.utensils', _SUCCESS))

        body = QWidget()
        body.setStyleSheet(f"background:{_BG};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 24, 28, 24)
        bl.setSpacing(16)

        def _row(lbl_text, widget):
            bl.addWidget(_field_lbl(lbl_text))
            bl.addWidget(widget)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Menu item name")
        self.name.setMinimumHeight(38)
        self.name.setMaximumHeight(42)
        _row("ITEM NAME *", self.name)

        self.price = QDoubleSpinBox()
        self.price.setRange(0, 10_000_000); self.price.setDecimals(2); self.price.setValue(0)
        self.price.setPrefix("Rs "); self.price.setMinimumHeight(38)
        self.price.setMaximumHeight(42)
        _row("PRICE *", self.price)

        self.category = QComboBox()
        self.category.setMinimumHeight(38)
        self.category.setMaximumHeight(42)
        try:
            cats = get_category_names()
            if cats: self.category.addItems(cats)
        except Exception:
            self.category.addItems(["General", "Food", "Beverages", "Supplies", "Equipment"])
        _row("CATEGORY", self.category)

        self.code = QLineEdit()
        self.code.setPlaceholderText("Optional short code")
        self.code.setMinimumHeight(38)
        self.code.setMaximumHeight(42)
        _row("CODE (OPTIONAL)", self.code)

        layout.addWidget(body, stretch=1)

        footer, btn_cancel, btn_save = _dialog_footer("Add Item", "Cancel", "fa5s.plus-circle", "fa5s.times")
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self.accept)
        layout.addWidget(footer)


# ─────────────────────────────────────────────────────────────────────────────
#  RECONCILE STOCK DIALOG (refined)
# ─────────────────────────────────────────────────────────────────────────────
class ReconcileStockDialog(QDialog):
    def __init__(self, item_name, current_qty, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reconcile Stock")
        self.setFixedSize(440, 380)
        self.setStyleSheet(INV_STYLE)
        self.item_name = item_name
        self._current_qty = current_qty

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with warning color
        hdr = QFrame()
        hdr.setFixedHeight(70)
        hdr.setStyleSheet(
            f"QFrame {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {_WARNING}, stop:1 #FBBF24); border-top-left-radius:24px; border-top-right-radius:24px; }}"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(24, 0, 24, 0); hl.setSpacing(14)
        ico = _icon_widget('fa5s.balance-scale', 'white', size=28, bg='#F59E0B50', radius=12, padding=6)
        ttl = QLabel("Reconcile Stock")
        ttl.setStyleSheet("color:white; font-size:20px; font-weight:800; border:none; background:transparent;")
        hl.addWidget(ico); hl.addWidget(ttl); hl.addStretch()
        layout.addWidget(hdr)

        body = QWidget()
        body.setStyleSheet(f"background:{_BG};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 24, 28, 24)
        bl.setSpacing(16)

        # Item chip
        chip = QFrame()
        chip.setStyleSheet(f"background:{_WARNING_LT}; border-radius:12px; border:1px solid {_WARNING};")
        ch_lay = QHBoxLayout(chip); ch_lay.setContentsMargins(16, 10, 16, 10)
        ch_icon = _icon_widget('fa5s.box', _WARNING, size=16)
        ch_lbl = QLabel(item_name)
        ch_lbl.setStyleSheet(f"font-size:14px; font-weight:800; color:#B45309; background:transparent;")
        ch_lay.addWidget(ch_icon); ch_lay.addSpacing(8); ch_lay.addWidget(ch_lbl); ch_lay.addStretch()
        bl.addWidget(chip)

        # Current stock
        curr_row = QHBoxLayout()
        curr_row.addWidget(_field_lbl("SYSTEM STOCK:"))
        curr_row.addStretch()
        curr_val = QLabel(f"{current_qty:.3f}")
        curr_val.setStyleSheet(f"font-size:28px; font-weight:900; color:{_TEXT_PRI};")
        curr_row.addWidget(curr_val)
        bl.addLayout(curr_row)

        bl.addWidget(_field_lbl("PHYSICAL COUNT"))
        self.physical_qty = QDoubleSpinBox()
        self.physical_qty.setRange(0, 1_000_000); self.physical_qty.setValue(current_qty); self.physical_qty.setDecimals(4)
        self.physical_qty.setFixedHeight(50)
        self.physical_qty.setStyleSheet(
            f"font-size:20px; font-weight:800; border:2px solid {_WARNING}; border-radius:12px;"
            f" padding:4px 16px; color:{_TEXT_PRI}; background:#FFFBEB;"
        )
        bl.addWidget(self.physical_qty)

        self.variance_label = QLabel("=  No Change")
        self.variance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.variance_label.setStyleSheet(
            f"font-size:14px; font-weight:800; color:{_TEXT_SEC}; background:{_DIVIDER};"
            f" padding:10px 16px; border-radius:12px;"
        )
        bl.addWidget(self.variance_label)
        self.physical_qty.valueChanged.connect(self.update_variance)
        self.update_variance()

        layout.addWidget(body, stretch=1)

        # Footer
        footer = QFrame()
        footer.setStyleSheet(f"QFrame {{ background:{_SURFACE}; border-top:1px solid {_BORDER}; "
                             f"border-bottom-left-radius:24px; border-bottom-right-radius:24px; }}")
        fl = QHBoxLayout(footer); fl.setContentsMargins(24, 16, 24, 16)

        btn_cancel = QPushButton("  Cancel")
        btn_cancel.setIcon(qta.icon('fa5s.times', color=_TEXT_SEC))
        btn_cancel.setFixedHeight(44)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1.5px solid {_BORDER}; border-radius:12px;"
            f" color:{_TEXT_SEC}; font-weight:600; padding:0 24px; font-size:13px; }}"
            f"QPushButton:hover {{ background:{_BG}; }}"
        )
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("  Reconcile")
        btn_save.setIcon(qta.icon('fa5s.check', color=_DARK1))
        btn_save.setFixedHeight(44)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(
            f"QPushButton {{ background:{_WARNING}; color:{_DARK1}; border:none; border-radius:12px;"
            f" font-size:14px; font-weight:800; padding:0 32px; }}"
            f"QPushButton:hover {{ background:#D97706; color:white; }}"
        )
        btn_save.clicked.connect(self.accept)

        fl.addWidget(btn_cancel); fl.addStretch(); fl.addWidget(btn_save)
        layout.addWidget(footer)

    def update_variance(self):
        diff = self.physical_qty.value() - self._current_qty
        if diff > 0:
            self.variance_label.setText(f"▲  +{diff:.3f}  Surplus")
            self.variance_label.setStyleSheet(
                f"font-size:14px; font-weight:800; color:{_SUCCESS}; background:{_SUCCESS_LT};"
                f" padding:10px 16px; border-radius:12px;"
            )
        elif diff < 0:
            self.variance_label.setText(f"▼  {diff:.3f}  Shortage")
            self.variance_label.setStyleSheet(
                f"font-size:14px; font-weight:800; color:{_DANGER}; background:{_DANGER_LT};"
                f" padding:10px 16px; border-radius:12px;"
            )
        else:
            self.variance_label.setText("=  No Change")
            self.variance_label.setStyleSheet(
                f"font-size:14px; font-weight:800; color:{_TEXT_SEC}; background:{_DIVIDER};"
                f" padding:10px 16px; border-radius:12px;"
            )


# ─────────────────────────────────────────────────────────────────────────────
#  EDIT INVENTORY ITEM DIALOG (refined)
# ─────────────────────────────────────────────────────────────────────────────
class EditInventoryItemDialog(QDialog):
    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit: {item_data.get('item_name')}")
        self.setFixedSize(440, 500)
        self.setStyleSheet(INV_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(_gradient_header(f"Edit Item", item_data.get('item_name', ''), 'fa5s.edit', _PRIMARY))

        body = QWidget()
        body.setStyleSheet(f"background:{_BG};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 24, 28, 24)
        bl.setSpacing(16)

        def _field(lbl_text, widget):
            bl.addWidget(_field_lbl(lbl_text))
            bl.addWidget(widget)

        self.category = QComboBox()
        self.category.addItems(["General", "Food", "Beverages", "Supplies", "Equipment"])
        self.category.setCurrentText(item_data.get('category', 'General'))
        self.category.setFixedHeight(42)
        _field("CATEGORY", self.category)

        self.threshold = QSpinBox()
        self.threshold.setRange(0, 100_000)
        self.threshold.setValue(int(item_data.get('threshold', 5)))
        self.threshold.setFixedHeight(42)
        _field("LOW STOCK THRESHOLD", self.threshold)

        self.unit = QLineEdit(item_data.get('unit', 'pcs'))
        self.unit.setFixedHeight(42)
        _field("UNIT", self.unit)

        self.cost = QDoubleSpinBox()
        self.cost.setRange(0, 1_000_000); self.cost.setDecimals(2)
        self.cost.setValue(float(item_data.get('cost_per_unit', 0)))
        self.cost.setPrefix("Rs "); self.cost.setFixedHeight(42)
        _field("COST PER UNIT (MANUAL OVERRIDE)", self.cost)

        layout.addWidget(body, stretch=1)

        footer, btn_cancel, btn_save = _dialog_footer("Save Changes", "Cancel", "fa5s.save", "fa5s.times")
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self.accept)
        layout.addWidget(footer)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN INVENTORY PAGE – ULTRA‑MODERN LAYOUT (final refinements)
# ─────────────────────────────────────────────────────────────────────────────
class InventoryPage(QWidget):
    def __init__(self, user=None):
        super().__init__()
        self.user = user
        self.setStyleSheet(INV_STYLE)
        self.init_ui()
        self.load_inventory()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar (customized header)
        main_layout.addWidget(self._build_top_bar())

        # Stats cards (now with equal stretch)
        self._stats_container = self._build_stats_row()
        main_layout.addWidget(self._stats_container)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # Stock Tab
        stock_widget = QWidget(); stock_widget.setStyleSheet(f"background:{_BG};")
        sv = QVBoxLayout(stock_widget); sv.setContentsMargins(20, 20, 20, 20); sv.setSpacing(16)
        sv.addWidget(self._build_filters())
        sv.addWidget(self._build_main_table())
        self.tabs.addTab(stock_widget, qta.icon('fa5s.boxes', color=_PRIMARY), "  STOCK  ")

        # Menu Tab
        self.menu_tab = self._build_menu_tab()
        self.tabs.addTab(self.menu_tab, qta.icon('fa5s.utensils', color=_SUCCESS), "  MENU  ")

        # Categories Tab
        self.categories_tab = CategoriesSettingsTab()
        self.tabs.addTab(self.categories_tab, qta.icon('fa5s.tags', color=_WARNING), "  CATEGORIES  ")

        # Reconcile Tab
        self.reconcile_tab = self._build_reconcile_tab()
        self.tabs.addTab(self.reconcile_tab, qta.icon('fa5s.balance-scale', color=_WARNING), "  RECONCILE  ")

        # Wastage Tab
        self.wastage_tab = self._build_wastage_tab()
        self.tabs.addTab(self.wastage_tab, qta.icon('fa5s.trash-alt', color=_DANGER), "  WASTAGE  ")

        # History Tab
        self.history_tab = self._build_history_tab()
        self.tabs.addTab(self.history_tab, qta.icon('fa5s.history', color=_INFO), "  HISTORY  ")

        # Suppliers Tab
        self.tabs.addTab(SupplierPage(), qta.icon('fa5s.truck', color=_TEXT_SEC), "  SUPPLIERS  ")

        main_layout.addWidget(self.tabs)

        # Initial low stock check
        self.check_low_stock()

    # ── TOP BAR (with responsive search) ─────────────────────────────────────
    def _build_top_bar(self):
        container = QFrame()
        container.setStyleSheet(f"QFrame {{ background:{_SURFACE}; border-bottom:1px solid {_BORDER}; }}")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(24, 16, 24, 16)

        # Left: title + subtitle
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Inventory Management")
        title.setStyleSheet(f"font-size:26px; font-weight:800; color:{_TEXT_PRI}; border:none;")
        subtitle = QLabel("Track stock, recipes, wastage, and suppliers")
        subtitle.setStyleSheet(f"font-size:13px; color:{_TEXT_SEC}; border:none;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        # Right: actions + search
        right_layout = QHBoxLayout()
        right_layout.setSpacing(12)

        # Search (will shrink gracefully)
        self.global_search = QLineEdit()
        self.global_search.setPlaceholderText("🔍  Search inventory...")
        self.global_search.setMinimumWidth(200)
        self.global_search.setMaximumWidth(400)
        self.global_search.setFixedHeight(40)
        self.global_search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.global_search.setStyleSheet(f"""
            QLineEdit {{
                background: {_BG};
                border: 1px solid {_BORDER};
                border-radius: 20px;
                padding: 0 16px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {_PRIMARY};
                background: {_SURFACE};
            }}
        """)
        self.global_search.textChanged.connect(lambda: self.filter_inventory())

        if has_permission(self.user, "inventory"):
            btn_add = _action_btn("  Add Stock", "fa5s.plus", _SUCCESS, "#047857", height=40, radius=20)
            btn_add.clicked.connect(self.show_add_stock_dialog)
            right_layout.addWidget(btn_add)

            btn_export = _flat_btn("  Export CSV", _TEXT_SEC, _BG, height=40, radius=20)
            btn_export.setIcon(qta.icon('fa5s.file-export', color=_TEXT_SEC))
            btn_export.clicked.connect(self.export_inventory_csv)
            right_layout.addWidget(btn_export)

        btn_refresh = _icon_btn("fa5s.sync-alt", _TEXT_SEC, _BG, _BORDER, "Refresh", (40, 40), 20)
        btn_refresh.clicked.connect(self.load_inventory)
        right_layout.addWidget(btn_refresh)

        layout.addLayout(title_col)
        layout.addStretch()
        layout.addWidget(self.global_search)
        layout.addLayout(right_layout)

        return container

    # ── STATS CARDS (now with equal stretch) ─────────────────────────────────
    def _build_stats_row(self):
        container = QFrame()
        container.setStyleSheet(f"QFrame {{ background:{_BG}; border:none; }}")
        container.setFixedHeight(110)
        row = QHBoxLayout(container)
        row.setContentsMargins(24, 12, 24, 12)
        row.setSpacing(16)

        def _stat_card(title_text, icon_name, color, bg_lt):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {_SURFACE};
                    border-radius: 18px;
                    border: 1px solid {_BORDER};
                    box-shadow: {_SHADOW};
                }}
            """)
            card.setFixedHeight(86)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(18, 12, 20, 12)
            cl.setSpacing(14)

            icon_wrap = QLabel()
            icon_wrap.setFixedSize(48, 48)
            icon_wrap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_wrap.setPixmap(qta.icon(icon_name, color=color).pixmap(24, 24))
            icon_wrap.setStyleSheet(f"background:{bg_lt}; border-radius:14px;")

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            val_lbl = QLabel("0")
            val_lbl.setStyleSheet(f"font-size:28px; font-weight:900; color:{color}; line-height:1;")
            title_lbl = QLabel(title_text)
            title_lbl.setStyleSheet(f"font-size:12px; font-weight:700; color:{_TEXT_HINT}; letter-spacing:0.3px;")
            text_col.addWidget(val_lbl)
            text_col.addWidget(title_lbl)

            cl.addWidget(icon_wrap)
            cl.addLayout(text_col)
            cl.addStretch()
            row.addWidget(card, 1)  # stretch factor 1 → equal width
            return val_lbl

        self.stat_total = _stat_card("TOTAL ITEMS",  "fa5s.boxes",                _PRIMARY, _PRIMARY_LT)
        self.stat_low   = _stat_card("LOW STOCK",    "fa5s.exclamation-triangle", _WARNING, _WARNING_LT)
        self.stat_out   = _stat_card("OUT OF STOCK", "fa5s.times-circle",         _DANGER,  _DANGER_LT)
        self.stat_value = _stat_card("TOTAL VALUE",  "fa5s.coins",                _SUCCESS, _SUCCESS_LT)
        # No final stretch needed because cards stretch equally
        return container

    # ── FILTERS (integrated with the table) ──────────────────────────────────
    def _build_filters(self):
        bar = QFrame()
        bar.setStyleSheet("QFrame { background:transparent; border:none; }")
        row = QHBoxLayout(bar); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(12)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.addItems(["Food", "Beverages", "Supplies", "Equipment"])
        self.category_filter.setFixedHeight(40)
        self.category_filter.setFixedWidth(180)
        self.category_filter.currentTextChanged.connect(self.filter_inventory)

        self.low_stock_check = QCheckBox("  Low Stock Only")
        self.low_stock_check.setStyleSheet(
            f"font-size:13px; font-weight:700; color:{_WARNING}; spacing:6px;"
        )
        self.low_stock_check.setIcon(qta.icon('fa5s.exclamation-triangle', color=_WARNING))
        self.low_stock_check.stateChanged.connect(self.filter_inventory)

        row.addWidget(_section_title("FILTER BY:"))
        row.addWidget(self.category_filter)
        row.addWidget(self.low_stock_check)
        row.addStretch()
        return bar

    # ── MAIN TABLE (modern, with action buttons) ─────────────────────────────
    def _build_main_table(self):
        card = _card(20, with_shadow=True)
        cl = QVBoxLayout(card); cl.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Item Name", "Category", "Quantity", "Unit",
            "Cost / Unit", "Value", "Threshold", "Actions"
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in [1, 2, 3, 4, 5, 6]:
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 260)  # enough for 5 icons + badge

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        cl.addWidget(self.table)
        return card

    # ── MENU TAB ─────────────────────────────────────────────────────────────
    def _build_menu_tab(self):
        container = QWidget(); container.setStyleSheet(f"background:{_BG};")
        v = QVBoxLayout(container); v.setContentsMargins(20, 20, 20, 20); v.setSpacing(16)

        # Top card with menu selector and add button
        top_card = _card(16)
        top_row = QHBoxLayout(top_card); top_row.setContentsMargins(16, 12, 16, 12); top_row.setSpacing(12)
        top_row.addWidget(_section_title("MENU ITEM:"))
        self.menu_combo = QComboBox(); self.menu_combo.setFixedHeight(42); self.menu_combo.setMinimumWidth(250)
        top_row.addWidget(self.menu_combo)
        btn_add_menu = _action_btn("Add Menu Item", "fa5s.plus", _SUCCESS, "#047857", height=42, radius=10)
        btn_add_menu.clicked.connect(self.show_add_menu_item_dialog)
        self.menu_refresh = _icon_btn("fa5s.sync-alt", _INFO, _INFO_LT, _INFO, "Refresh", (42, 42), 10)
        self.menu_refresh.clicked.connect(self.load_menu_items)
        top_row.addWidget(btn_add_menu); top_row.addWidget(self.menu_refresh); top_row.addStretch()
        v.addWidget(top_card)

        # Recipe card
        recipe_card = _card(16)
        rc = QVBoxLayout(recipe_card); rc.setContentsMargins(0, 0, 0, 0)

        recipe_hdr = QFrame()
        recipe_hdr.setFixedHeight(50)
        recipe_hdr.setStyleSheet(
            f"QFrame {{ background:{_BG}; border-bottom:1px solid {_BORDER};"
            f" border-top-left-radius:16px; border-top-right-radius:16px; }}"
        )
        rh = QHBoxLayout(recipe_hdr); rh.setContentsMargins(16, 0, 16, 0)
        rh.addWidget(_icon_widget('fa5s.flask', _PRIMARY, size=16))
        rh.addSpacing(8)
        rh_title = QLabel("Recipe Ingredients")
        rh_title.setStyleSheet(f"font-size:14px; font-weight:800; color:{_TEXT_PRI};")
        rh.addWidget(rh_title); rh.addStretch()
        rc.addWidget(recipe_hdr)

        self.recipe_table = QTableWidget()
        self.recipe_table.setColumnCount(3)
        self.recipe_table.setHorizontalHeaderLabels(["Ingredient", "Quantity", "Unit"])
        self.recipe_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.recipe_table.verticalHeader().setVisible(False)
        self.recipe_table.setShowGrid(False); self.recipe_table.setAlternatingRowColors(True)
        rc.addWidget(self.recipe_table)
        v.addWidget(recipe_card)

        # Action buttons for recipe
        actions = QHBoxLayout(); actions.setSpacing(12)
        self.btn_add_ing     = _action_btn("Add Ingredient",  "fa5s.plus",  _SUCCESS,  "#047857", height=44, radius=10)
        self.btn_remove_ing  = _action_btn("Remove Selected", "fa5s.trash", _DANGER,   "#c0303c", height=44, radius=10)
        self.btn_save_recipe = _action_btn("Save Recipe",     "fa5s.save",  _PRIMARY,  _PRIMARY_DK, height=44, radius=10)
        self.btn_add_ing.clicked.connect(self.add_ingredient_dialog)
        self.btn_remove_ing.clicked.connect(self.remove_selected_ingredient)
        self.btn_save_recipe.clicked.connect(self.save_recipe)
        actions.addWidget(self.btn_add_ing); actions.addWidget(self.btn_remove_ing)
        actions.addStretch(); actions.addWidget(self.btn_save_recipe)
        v.addLayout(actions)

        self.menu_combo.currentIndexChanged.connect(self.load_selected_recipe)
        self.load_menu_items()
        return container

    # ── RECONCILE TAB ─────────────────────────────────────────────────────────
    def _build_reconcile_tab(self):
        container = QWidget(); container.setStyleSheet(f"background:{_BG};")
        v = QVBoxLayout(container); v.setContentsMargins(20, 20, 20, 20); v.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_icon_widget('fa5s.balance-scale', _WARNING, size=24))
        hdr.addSpacing(8)
        hdr_title = QLabel("Stock Reconciliation")
        hdr_title.setStyleSheet(f"font-size:20px; font-weight:800; color:{_TEXT_PRI};")
        hdr.addWidget(hdr_title); hdr.addStretch()
        v.addLayout(hdr)

        card = _card(16)
        fl = QGridLayout(card); fl.setContentsMargins(28, 24, 28, 24); fl.setSpacing(16)

        def _lbl(txt):
            l = QLabel(txt); l.setStyleSheet(f"font-size:13px; font-weight:600; color:{_TEXT_SEC};"); return l

        fl.addWidget(_lbl("Select Item:"), 0, 0)
        self.recon_item = QComboBox(); self.recon_item.setFixedHeight(44)
        inv_list, _ = get_inventory()
        self._recon_items = inv_list
        for it in inv_list:
            self.recon_item.addItem(it.get("item_name", ""))
        fl.addWidget(self.recon_item, 0, 1)

        fl.addWidget(_lbl("System Stock:"), 1, 0)
        self.recon_current = QLabel("0")
        self.recon_current.setStyleSheet(f"font-size:30px; font-weight:900; color:{_PRIMARY};")
        fl.addWidget(self.recon_current, 1, 1)

        fl.addWidget(_lbl("Physical Count:"), 2, 0)
        self.recon_physical = QDoubleSpinBox()
        self.recon_physical.setRange(0, 1_000_000); self.recon_physical.setDecimals(4); self.recon_physical.setFixedHeight(50)
        self.recon_physical.setStyleSheet(
            f"font-size:20px; font-weight:800; border:2px solid {_WARNING}; border-radius:12px;"
            f" padding:4px 16px; color:{_TEXT_PRI}; background:#FFFBEB;"
        )
        fl.addWidget(self.recon_physical, 2, 1)

        self.recon_apply = _action_btn("Apply Reconciliation", "fa5s.check-circle", _WARNING, "#D97706", _DARK1, height=50, radius=12)
        self.recon_apply.clicked.connect(self.apply_reconcile)
        fl.addWidget(self.recon_apply, 3, 0, 1, 2)

        # Set column stretch to make input column wider
        fl.setColumnStretch(0, 1)
        fl.setColumnStretch(1, 3)

        v.addWidget(card)
        v.addStretch()

        self.recon_item.currentIndexChanged.connect(self.update_recon_current)
        self.update_recon_current()
        return container

    # ── WASTAGE TAB ───────────────────────────────────────────────────────────
    def _build_wastage_tab(self):
        container = QWidget(); container.setStyleSheet(f"background:{_BG};")
        v = QVBoxLayout(container); v.setContentsMargins(20, 20, 20, 20); v.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_icon_widget('fa5s.trash-alt', _DANGER, size=24))
        hdr.addSpacing(8)
        hdr_title = QLabel("Record Wastage")
        hdr_title.setStyleSheet(f"font-size:20px; font-weight:800; color:{_TEXT_PRI};")
        hdr.addWidget(hdr_title); hdr.addStretch()
        v.addLayout(hdr)

        # Form card (horizontal layout, responsive)
        form_card = QFrame()
        form_card.setStyleSheet(f"QFrame {{ background:{_DANGER_LT}; border-radius:16px; border:1px solid #FECACA; }}")
        fl = QHBoxLayout(form_card); fl.setContentsMargins(20, 16, 20, 16); fl.setSpacing(16)

        # Item
        item_box = QVBoxLayout(); item_box.setSpacing(4)
        item_box.addWidget(_field_lbl("ITEM"))
        self.w_item = QComboBox()
        self.w_item.setFixedHeight(42)
        self.w_item.setMinimumWidth(180)
        self.w_item.setStyleSheet(f"QComboBox {{ border:1px solid #FECACA; border-radius:10px; background:white; padding:0 12px; }}")
        inv_list, _ = get_inventory()
        self._w_items = inv_list
        for it in inv_list:
            self.w_item.addItem(it.get("item_name", ""))
        item_box.addWidget(self.w_item)
        fl.addLayout(item_box)

        # Quantity
        qty_box = QVBoxLayout(); qty_box.setSpacing(4)
        qty_box.addWidget(_field_lbl("QUANTITY"))
        self.w_qty = QDoubleSpinBox()
        self.w_qty.setRange(0, 1_000_000); self.w_qty.setDecimals(4); self.w_qty.setValue(1)
        self.w_qty.setFixedHeight(42); self.w_qty.setFixedWidth(100)
        self.w_qty.setStyleSheet(f"border:1px solid #FECACA; border-radius:10px; background:white; padding:0 12px;")
        qty_box.addWidget(self.w_qty)
        fl.addLayout(qty_box)

        # Reason
        reason_box = QVBoxLayout(); reason_box.setSpacing(4)
        reason_box.addWidget(_field_lbl("REASON"))
        self.w_reason = QComboBox()
        self.w_reason.setFixedHeight(42); self.w_reason.setMinimumWidth(150)
        self.w_reason.setStyleSheet(f"QComboBox {{ border:1px solid #FECACA; border-radius:10px; background:white; padding:0 12px; }}")
        for r in get_wastage_reasons():
            self.w_reason.addItem(r)
        reason_box.addWidget(self.w_reason)
        fl.addLayout(reason_box)

        # Notes
        notes_box = QVBoxLayout(); notes_box.setSpacing(4)
        notes_box.addWidget(_field_lbl("NOTES"))
        self.w_notes = QLineEdit()
        self.w_notes.setPlaceholderText("Optional...")
        self.w_notes.setFixedHeight(42); self.w_notes.setMinimumWidth(200)
        self.w_notes.setStyleSheet(f"border:1px solid #FECACA; border-radius:10px; background:white; padding:0 12px;")
        notes_box.addWidget(self.w_notes)
        fl.addLayout(notes_box)

        # Buttons
        btn_col = QVBoxLayout(); btn_col.setSpacing(8)
        self.w_save = _action_btn("Record", "fa5s.minus-circle", _DANGER, "#DC2626", height=42, radius=10)
        self.w_save.clicked.connect(self.record_wastage_action)
        btn_refresh_w = _icon_btn("fa5s.sync-alt", _INFO, _INFO_LT, _INFO, "Refresh", (42, 42), 10)
        btn_refresh_w.clicked.connect(self.load_wastage_recent)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.w_save)
        btn_row.addWidget(btn_refresh_w)
        btn_col.addLayout(btn_row)
        fl.addLayout(btn_col)

        v.addWidget(form_card)

        # Recent wastage table
        table_card = _card(16)
        tcl = QVBoxLayout(table_card); tcl.setContentsMargins(0, 0, 0, 0)
        self.w_table = QTableWidget()
        self.w_table.setColumnCount(6)
        self.w_table.setHorizontalHeaderLabels(["Item", "Qty", "Unit", "Reason", "Cost/Unit", "Time"])
        self.w_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.w_table.verticalHeader().setVisible(False)
        self.w_table.setShowGrid(False); self.w_table.setAlternatingRowColors(True)
        tcl.addWidget(self.w_table)
        v.addWidget(table_card)

        self.load_wastage_recent()
        return container

    # ── HISTORY TAB ───────────────────────────────────────────────────────────
    def _build_history_tab(self):
        container = QWidget(); container.setStyleSheet(f"background:{_BG};")
        v = QVBoxLayout(container); v.setContentsMargins(20, 20, 20, 20); v.setSpacing(16)

        # Controls card
        ctrl_card = _card(16)
        controls = QHBoxLayout(ctrl_card); controls.setContentsMargins(16, 12, 16, 12); controls.setSpacing(12)
        controls.addWidget(_section_title("FILTER:"))

        self.history_item_filter = QLineEdit()
        self.history_item_filter.setPlaceholderText("Item name...")
        self.history_item_filter.setFixedHeight(42)
        self.history_item_filter.setFixedWidth(200)
        controls.addWidget(self.history_item_filter)

        btn_apply = _action_btn("Apply", "fa5s.filter", _PRIMARY, _PRIMARY_DK, height=42, radius=10)
        btn_apply.clicked.connect(self.load_history)
        controls.addWidget(btn_apply)
        controls.addStretch()

        self.history_prev = QPushButton("← Prev")
        self.history_prev.setFixedHeight(42)
        self.history_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_prev.setStyleSheet(
            f"QPushButton {{ background:{_BG}; color:{_TEXT_SEC}; border:1px solid {_BORDER}; border-radius:10px; font-size:13px; font-weight:600; padding:0 16px; }}"
            f"QPushButton:hover {{ background:{_BORDER}; }}"
        )
        self.history_label = QLabel("0 – 0")
        self.history_label.setStyleSheet(
            f"font-size:13px; font-weight:700; color:{_TEXT_SEC}; background:{_BG};"
            f" padding:8px 20px; border-radius:10px; border:1px solid {_BORDER};"
        )
        self.history_next = QPushButton("Next →")
        self.history_next.setFixedHeight(42)
        self.history_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_next.setStyleSheet(
            f"QPushButton {{ background:{_PRIMARY}; color:white; border:none; border-radius:10px; font-size:13px; font-weight:700; padding:0 16px; }}"
            f"QPushButton:hover {{ background:{_PRIMARY_DK}; }}"
        )
        controls.addWidget(self.history_prev)
        controls.addWidget(self.history_label)
        controls.addWidget(self.history_next)
        v.addWidget(ctrl_card)

        # History table
        table_card = _card(16)
        tcl = QVBoxLayout(table_card); tcl.setContentsMargins(0, 0, 0, 0)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels(["Item", "Change", "Prev Qty", "New Qty", "Cost/Unit", "Reason", "Time"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setShowGrid(False); self.history_table.setAlternatingRowColors(True)
        tcl.addWidget(self.history_table)
        v.addWidget(table_card)

        self.history_skip = 0; self.history_limit = 50
        self.history_prev.clicked.connect(self.history_prev_page)
        self.history_next.clicked.connect(self.history_next_page)
        self.load_history()
        return container

    # ─────────────────────────────────────────────────────────────────────────
    #  ALL ORIGINAL LOGIC BELOW (unchanged, only UI enhancements above)
    # ─────────────────────────────────────────────────────────────────────────

    def show_add_menu_item_dialog(self):
        dlg = AddMenuItemDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                add_menu_item(
                    name=dlg.name.text(), price=dlg.price.value(),
                    category=dlg.category.currentText(), code=dlg.code.text(),
                    available=True, is_combo=False, combo_items=[]
                )
                QMessageBox.information(self, "Success", "Menu item added")
                self.load_menu_items()
                name = dlg.name.text()
                for i in range(self.menu_combo.count()):
                    if self.menu_combo.itemText(i).strip().lower() == name.strip().lower():
                        self.menu_combo.setCurrentIndex(i); break
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add menu item: {str(e)}")

    def load_menu_items(self):
        try:
            self.menu_combo.clear()
            items = get_menu_items(); self._menu_items = items
            for it in items:
                self.menu_combo.addItem(it.get("name", ""), userData=str(it.get("_id")))
            self.load_selected_recipe()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load menu items: {str(e)}")

    def load_selected_recipe(self):
        self.recipe_table.setRowCount(0)
        mid = self.menu_combo.currentData()
        if not mid: return
        try:
            r = get_recipe(mid)
            ings = r.get("ingredients", []) if r else []
            for ing in ings:
                row = self.recipe_table.rowCount()
                self.recipe_table.insertRow(row)
                self.recipe_table.setItem(row, 0, QTableWidgetItem(ing.get("item_name", "")))
                self.recipe_table.setItem(row, 1, QTableWidgetItem(str(ing.get("quantity", 0))))
                self.recipe_table.setItem(row, 2, QTableWidgetItem(ing.get("unit", "pcs")))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load recipe: {str(e)}")

    def add_ingredient_dialog(self):
        try: items, _ = get_inventory()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load inventory: {str(e)}"); return

        dlg = QDialog(self); dlg.setWindowTitle("Add Ingredient"); dlg.setFixedSize(380, 220)
        dlg.setStyleSheet(INV_STYLE)
        layout = QVBoxLayout(dlg); layout.setContentsMargins(24, 24, 24, 24); layout.setSpacing(14)
        layout.addWidget(_field_lbl("INGREDIENT"))
        combo = QComboBox(); combo.setFixedHeight(40)
        inv = items if isinstance(items, list) else items[0]
        ing_map = []
        for it in inv:
            name = it.get("item_name", "")
            combo.addItem(name); ing_map.append({"name": name, "unit": it.get("unit", "pcs")})
        layout.addWidget(combo)
        layout.addWidget(_field_lbl("QUANTITY"))
        qty = QDoubleSpinBox(); qty.setRange(0, 1_000_000); qty.setDecimals(4); qty.setValue(1); qty.setFixedHeight(40)
        layout.addWidget(qty)
        btns = QHBoxLayout(); btns.setSpacing(12)
        b_cancel = QPushButton("Cancel"); b_cancel.setFixedHeight(40); b_cancel.setFixedWidth(100)
        b_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        b_cancel.setStyleSheet(
            f"QPushButton {{ background:{_BG}; border:1px solid {_BORDER}; border-radius:10px; color:{_TEXT_SEC}; font-weight:600; }}"
            f"QPushButton:hover {{ background:{_BORDER}; }}"
        )
        b_cancel.clicked.connect(dlg.reject)
        b_add = _action_btn("Add", "fa5s.plus", _SUCCESS, "#047857", height=40, radius=10)
        b_add.clicked.connect(dlg.accept)
        btns.addWidget(b_cancel); btns.addStretch(); btns.addWidget(b_add)
        layout.addLayout(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            idx = combo.currentIndex()
            data = ing_map[idx] if idx >= 0 else {"name": "", "unit": "pcs"}
            row = self.recipe_table.rowCount()
            self.recipe_table.insertRow(row)
            self.recipe_table.setItem(row, 0, QTableWidgetItem(data["name"]))
            self.recipe_table.setItem(row, 1, QTableWidgetItem(str(qty.value())))
            self.recipe_table.setItem(row, 2, QTableWidgetItem(data["unit"]))

    def remove_selected_ingredient(self):
        r = self.recipe_table.currentRow()
        if r >= 0: self.recipe_table.removeRow(r)

    def save_recipe(self):
        mid = self.menu_combo.currentData()
        if not mid: QMessageBox.warning(self, "Warning", "Select a menu item"); return
        ings = []
        for r in range(self.recipe_table.rowCount()):
            ings.append({"item_name": self.recipe_table.item(r, 0).text(),
                         "quantity": float(self.recipe_table.item(r, 1).text()),
                         "unit": self.recipe_table.item(r, 2).text()})
        try:
            add_recipe(mid, ings); QMessageBox.information(self, "Success", "Recipe saved")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save recipe: {str(e)}")

    def update_recon_current(self):
        idx = self.recon_item.currentIndex()
        if idx < 0: self.recon_current.setText("0"); self.recon_physical.setValue(0); return
        it = self._recon_items[idx]; q = float(it.get("qty", 0))
        self.recon_current.setText(str(q)); self.recon_physical.setValue(q)

    def apply_reconcile(self):
        idx = self.recon_item.currentIndex()
        if idx < 0: return
        name = self._recon_items[idx].get("item_name", "")
        try:
            reconcile_stock(name, self.recon_physical.value(), user=self.user.get('username', 'System'))
            QMessageBox.information(self, "Success", "Reconciled")
            self.load_inventory(); self.update_recon_current()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reconcile: {str(e)}")

    def load_wastage_recent(self):
        try:
            items, total = get_wastage_paginated(0, 20)
            self.w_table.setRowCount(len(items))
            for i, r in enumerate(items):
                self.w_table.setItem(i, 0, QTableWidgetItem(str(r.get("item_name", ""))))
                self.w_table.setItem(i, 1, QTableWidgetItem(str(r.get("quantity", 0))))
                self.w_table.setItem(i, 2, QTableWidgetItem(str(r.get("unit", ""))))
                self.w_table.setItem(i, 3, QTableWidgetItem(str(r.get("reason", ""))))
                self.w_table.setItem(i, 4, QTableWidgetItem(str(r.get("cost_per_unit", 0))))
                self.w_table.setItem(i, 5, QTableWidgetItem(str(r.get("recorded_at", ""))))
        except Exception as e:
            print(f"Wastage load error: {e}")

    def record_wastage_action(self):
        idx = self.w_item.currentIndex()
        if idx < 0: return
        it = self._w_items[idx]
        try:
            record_wastage(
                item_name=it.get("item_name", ""), quantity=self.w_qty.value(),
                unit=it.get("unit", "pcs"), reason=self.w_reason.currentText(),
                user_id=self.user.get('_id', self.user.get('username', 'System')),
                notes=self.w_notes.text(), cost_per_unit=it.get("cost_per_unit", 0)
            )
            QMessageBox.information(self, "Success", "Recorded")
            self.w_notes.setText(""); self.load_inventory(); self.load_wastage_recent()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to record wastage: {str(e)}")

    def load_history(self):
        try:
            name_filter = self.history_item_filter.text().strip() if hasattr(self, "history_item_filter") else None
            logs, total = get_stock_history(name_filter if name_filter else None, self.history_limit, self.history_skip)
            self.history_table.setRowCount(len(logs))
            for i, l in enumerate(logs):
                self.history_table.setItem(i, 0, QTableWidgetItem(str(l.get("item_name", ""))))
                chg = l.get("change", 0)
                chg_item = QTableWidgetItem(f"+{chg}" if chg > 0 else str(chg))
                chg_item.setForeground(QColor(C['success'] if chg > 0 else C['danger']))
                chg_item.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
                self.history_table.setItem(i, 1, chg_item)
                self.history_table.setItem(i, 2, QTableWidgetItem(str(l.get("previous_qty", 0))))
                self.history_table.setItem(i, 3, QTableWidgetItem(str(l.get("new_qty", 0))))
                self.history_table.setItem(i, 4, QTableWidgetItem(str(l.get("cost_per_unit", 0))))
                self.history_table.setItem(i, 5, QTableWidgetItem(str(l.get("reason", ""))))
                ts = l.get("timestamp"); ts_str = str(ts) if ts else ""
                self.history_table.setItem(i, 6, QTableWidgetItem(ts_str))
                self.history_table.setRowHeight(i, 42)
            start = self.history_skip + 1 if logs else 0; end = self.history_skip + len(logs)
            self.history_label.setText(f"{start} – {end} / {total}")
            self.history_prev.setEnabled(self.history_skip > 0)
            self.history_next.setEnabled(self.history_skip + self.history_limit < total)
        except Exception as e:
            print(f"History load error: {e}")

    def history_prev_page(self):
        self.history_skip = max(0, self.history_skip - self.history_limit); self.load_history()

    def history_next_page(self):
        self.history_skip += self.history_limit; self.load_history()

    def load_inventory(self):
        try:
            items, total = get_inventory({}, 0, 0)
            self.update_stats(items); self.populate_table(items)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load inventory: {str(e)}")

    def export_inventory_csv(self):
        try:
            items, _ = get_inventory()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S"); fname = f"inventory_export_{ts}.csv"
            import csv
            with open(fname, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Item Name", "Category", "Qty", "Unit", "Cost/Unit", "Value", "Threshold"])
                for it in items:
                    qty = it.get("qty", 0); cost = it.get("cost_per_unit", 0)
                    w.writerow([it.get("item_name", ""), it.get("category", "General"), qty,
                                it.get("unit", "pcs"), cost, qty * cost, it.get("threshold", 0)])
            QMessageBox.information(self, "Exported", f"CSV saved: {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

    def update_stats(self, items):
        self.stat_total.setText(str(len(items)))
        low_stock = [i for i in items if i.get('qty', 0) <= i.get('threshold', 0)]
        out_stock  = [i for i in items if i.get('qty', 0) <= 0]
        self.stat_low.setText(str(len(low_stock)))
        self.stat_out.setText(str(len(out_stock)))
        total_value = sum(i.get('qty', 0) * i.get('cost_per_unit', 0) for i in items)
        self.stat_value.setText(f"{total_value:,.0f}")

    def populate_table(self, items):
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            qty = item.get('qty', 0); thresh = item.get('threshold', 0); cost = item.get('cost_per_unit', 0)

            if qty <= 0:        row_color = "#FFF5F5"; qty_color = C['danger']
            elif qty <= thresh: row_color = "#FFFBEB"; qty_color = C['warning']
            else:               row_color = C['surface']; qty_color = C['success']

            # Name
            name_item = QTableWidgetItem(item.get('item_name', ''))
            name_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            name_item.setForeground(QColor(_TEXT_PRI))
            name_item.setBackground(QColor(row_color)); self.table.setItem(row, 0, name_item)

            # Category
            cat_item = QTableWidgetItem(item.get('category', 'General'))
            cat_item.setForeground(QColor(C['text_sec'])); cat_item.setBackground(QColor(row_color))
            self.table.setItem(row, 1, cat_item)

            # Quantity
            qty_item = QTableWidgetItem(str(qty))
            qty_item.setForeground(QColor(qty_color)); qty_item.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); qty_item.setBackground(QColor(row_color))
            self.table.setItem(row, 2, qty_item)

            # Unit
            unit_item = QTableWidgetItem(item.get('unit', 'pcs'))
            unit_item.setForeground(QColor(_TEXT_SEC)); unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            unit_item.setBackground(QColor(row_color)); self.table.setItem(row, 3, unit_item)

            # Cost
            cost_item = QTableWidgetItem(f"Rs {cost:.2f}" if cost else "—")
            cost_item.setForeground(QColor(_TEXT_SEC))
            cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            cost_item.setBackground(QColor(row_color)); self.table.setItem(row, 4, cost_item)

            # Value
            value = qty * cost
            val_item = QTableWidgetItem(f"Rs {value:,.2f}")
            val_item.setForeground(QColor(_PRIMARY if value > 0 else C['text_hint']))
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            val_item.setBackground(QColor(row_color)); self.table.setItem(row, 5, val_item)

            # Threshold
            th_item = QTableWidgetItem(str(thresh))
            th_item.setForeground(QColor(_TEXT_SEC)); th_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            th_item.setBackground(QColor(row_color)); self.table.setItem(row, 6, th_item)

            # Actions cell
            act_w = QWidget(); act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(6, 4, 6, 4); act_l.setSpacing(8)

            if qty <= 0:        badge = _badge("OUT", C['danger'])
            elif qty <= thresh: badge = _badge("LOW", C['warning'])
            else:               badge = _badge("OK",  C['success'])
            act_l.addWidget(badge)

            btn_add  = _icon_btn("fa5s.plus",         _SUCCESS, _SUCCESS_LT, _SUCCESS, "Add Stock",   (28, 28), 6)
            btn_rec  = _icon_btn("fa5s.balance-scale", _WARNING, _WARNING_LT, _WARNING, "Reconcile",   (28, 28), 6)
            btn_bat  = _icon_btn("fa5s.boxes",         _INFO,    _INFO_LT,    _INFO,    "Batches",     (28, 28), 6)
            btn_edit = _icon_btn("fa5s.edit",          _PRIMARY, _PRIMARY_LT, _PRIMARY, "Edit Details", (28, 28), 6)
            btn_del  = _icon_btn("fa5s.trash",         _DANGER,  _DANGER_LT,  _DANGER,  "Delete Item",  (28, 28), 6)

            btn_add.clicked.connect(lambda checked, name=item.get('item_name'): self.show_add_stock_dialog(name))
            btn_rec.clicked.connect(lambda checked, name=item.get('item_name'), q=qty: self.show_reconcile_dialog(name, q))
            btn_bat.clicked.connect(lambda checked, name=item.get('item_name'): self.show_batches_dialog(name))
            btn_edit.clicked.connect(lambda checked, it=item: self.edit_item_dialog(it))
            btn_del.clicked.connect(lambda checked, name=item.get('item_name'): self.delete_item_action(name))

            for b in [btn_add, btn_rec, btn_bat, btn_edit, btn_del]:
                act_l.addWidget(b)
            act_l.addStretch()
            self.table.setCellWidget(row, 7, act_w)
            self.table.setRowHeight(row, 50)

    def edit_item_dialog(self, item_data):
        if not has_permission(self.user, "inventory"):
            QMessageBox.warning(self, "Access Denied", "Permission denied"); return
        dlg = EditInventoryItemDialog(item_data, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                update_inventory_item(
                    item_name=item_data.get('item_name'),
                    threshold=dlg.threshold.value(),
                    unit=dlg.unit.text(),
                    cost_per_unit=dlg.cost.value(),
                    category=dlg.category.currentText()
                )
                QMessageBox.information(self, "Success", "Item updated")
                self.load_inventory()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_item_action(self, item_name):
        if not has_permission(self.user, "admin"):
            QMessageBox.warning(self, "Access Denied", "Only admins can delete items"); return
        res = QMessageBox.question(self, "Confirm Delete",
                                   f"Are you sure you want to delete '{item_name}'?\nThis cannot be undone.",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            try:
                if delete_inventory_item(item_name):
                    QMessageBox.information(self, "Success", "Item deleted"); self.load_inventory()
                else:
                    QMessageBox.warning(self, "Failed", "Could not delete item")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def filter_inventory(self):
        search_text = self.global_search.text().lower()
        category = self.category_filter.currentText()
        show_low_stock = self.low_stock_check.isChecked()
        try:
            items, _ = get_inventory()
        except:
            return
        filtered_items = []
        for item in items:
            if search_text and search_text not in item.get('item_name', '').lower(): continue
            if category != "All Categories" and item.get('category', 'General') != category: continue
            if show_low_stock and item.get('qty', 0) > item.get('threshold', 0): continue
            filtered_items.append(item)
        self.populate_table(filtered_items); self.update_stats(filtered_items)

    def check_low_stock(self):
        try:
            low_stock = low_stock_items(); count = len(low_stock)
            if count > 0:
                self.tabs.setTabIcon(0, qta.icon('fa5s.exclamation-circle', color=C['danger']))
                self.tabs.setTabText(0, f"  STOCK ({count} LOW)  ")
            else:
                self.tabs.setTabIcon(0, qta.icon('fa5s.boxes', color=_PRIMARY))
                self.tabs.setTabText(0, "  STOCK  ")
        except Exception as e:
            print(f"Error checking low stock: {e}")

    def show_add_stock_dialog(self, item_name=None):
        if not has_permission(self.user, "inventory"):
            QMessageBox.warning(self, "Access Denied", "You don't have permission to add stock"); return
        dialog = AddStockDialog(item_name, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                add_stock(
                    item_name=dialog.item_name.text(), qty=dialog.qty.value(),
                    cost_per_unit=dialog.cost.value(),
                    batch_no=dialog.batch_no.text() if dialog.batch_no.text() else None,
                    purchase_unit=dialog.purchase_unit.text() if dialog.purchase_unit.text() else None,
                    conversion_factor=dialog.conversion.value(),
                    supplier_id=dialog._supplier_ids[dialog.supplier.currentIndex()],
                    category=dialog.category.currentText(),
                    user=self.user.get('username', 'System')
                )
                QMessageBox.information(self, "Success", "Stock added successfully!")
                self.load_inventory()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add stock: {str(e)}")

    def show_reconcile_dialog(self, item_name, current_qty):
        if not has_permission(self.user, "inventory"):
            QMessageBox.warning(self, "Access Denied", "You don't have permission to reconcile stock"); return
        dialog = ReconcileStockDialog(item_name, current_qty, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                reconcile_stock(
                    item_name=item_name, physical_qty=dialog.physical_qty.value(),
                    user=self.user.get('username', 'System')
                )
                QMessageBox.information(self, "Success", "Stock reconciled successfully!")
                self.load_inventory()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reconcile stock: {str(e)}")

    def show_batches_dialog(self, item_name):
        dlg = QDialog(self); dlg.setWindowTitle(f"Batches – {item_name}"); dlg.setFixedSize(680, 480)
        dlg.setStyleSheet(INV_STYLE)
        v = QVBoxLayout(dlg); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)

        # Header
        v.addWidget(_gradient_header(f"Batches", item_name, 'fa5s.boxes', _INFO))

        body = QWidget(); body.setStyleSheet(f"background:{_BG};")
        bv = QVBoxLayout(body); bv.setContentsMargins(24, 20, 24, 20); bv.setSpacing(16)

        tbl = QTableWidget(); tbl.setColumnCount(5)
        tbl.setHorizontalHeaderLabels(["Batch No", "Qty", "Expiry", "Created", "Actions"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setVisible(False); tbl.setShowGrid(False); tbl.setAlternatingRowColors(True)
        bv.addWidget(tbl)

        batches = []
        try: batches = get_batches(item_name)
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

        tbl.setRowCount(len(batches))
        for i, b in enumerate(batches):
            tbl.setItem(i, 0, QTableWidgetItem(str(b.get("batch_no", ""))))
            qty_item = QTableWidgetItem(str(b.get("qty", 0)))
            qty_item.setFont(QFont("Consolas", 10, QFont.Weight.Bold)); tbl.setItem(i, 1, qty_item)
            exp = b.get("expiry_date"); tbl.setItem(i, 2, QTableWidgetItem(str(exp) if exp else "—"))
            cr = b.get("created_at");  tbl.setItem(i, 3, QTableWidgetItem(str(cr) if cr else "—"))
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(4, 2, 4, 2)
            rm = _icon_btn("fa5s.trash", _DANGER, _DANGER_LT, _DANGER, "Remove Batch", (28, 28), 6)
            rm.clicked.connect(lambda checked, idx=i: self.remove_batch_and_reload(item_name, idx, dlg))
            h.addWidget(rm); h.addStretch(); tbl.setCellWidget(i, 4, w)
            tbl.setRowHeight(i, 48)

        v.addWidget(body, stretch=1)

        footer = QFrame()
        footer.setStyleSheet(f"QFrame {{ background:{_SURFACE}; border-top:1px solid {_BORDER}; "
                             f"border-bottom-left-radius:24px; border-bottom-right-radius:24px; }}")
        fl = QHBoxLayout(footer); fl.setContentsMargins(24, 16, 24, 16)
        close_btn = QPushButton("  Close")
        close_btn.setIcon(qta.icon('fa5s.times', color=_TEXT_SEC))
        close_btn.setFixedHeight(44)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1.5px solid {_BORDER}; border-radius:12px;"
            f" color:{_TEXT_SEC}; font-weight:600; padding:0 28px; font-size:13px; }}"
            f"QPushButton:hover {{ background:{_BG}; }}"
        )
        close_btn.clicked.connect(dlg.reject)
        fl.addStretch(); fl.addWidget(close_btn)
        v.addWidget(footer)
        dlg.exec()

    def remove_batch_and_reload(self, item_name, batch_idx, dialog):
        try:
            ok = remove_batch(item_name, batch_idx, user=self.user.get('username', 'System'))
            if ok:
                QMessageBox.information(self, "Success", "Batch removed")
                dialog.reject(); self.load_inventory()
            else:
                QMessageBox.warning(self, "Warning", "Batch remove failed")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))