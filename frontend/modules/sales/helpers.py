"""
Shared styles, widget factories and utility functions for the Sales module.
"""

from PyQt6.QtWidgets import (QFrame, QLabel, QPushButton)
from PyQt6.QtCore import Qt
import qtawesome as qta
from datetime import datetime
from backend.core.database import orders_col, counters_col
from frontend.shared_ui import GLOBAL_STYLE

import random

# ─────────────────────────────────────────────────────────────────────────────
#  IMPROVED GLOBAL STYLE  (drop-in replacement)
# ─────────────────────────────────────────────────────────────────────────────
IMPROVED_STYLE = GLOBAL_STYLE + """

/* ── FONTS ──────────────────────────────────────────────────────────────── */
* { font-family: 'Segoe UI', 'SF Pro Display', system-ui, sans-serif; }

/* ── TABLE MANAGEMENT HEADER CARD ───────────────────────────────────────── */
QFrame[class="table-header-card"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0f172a, stop:0.5 #1e293b, stop:1 #0f172a);
    border: none;
    border-radius: 14px;
    padding: 4px;
}

/* ── TABLE ACTION BUTTONS ───────────────────────────────────────────────── */
QPushButton[class="table-action-btn"] {
    background: rgba(255,255,255,0.06);
    color: #94a3b8;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 8px;
    padding: 0 14px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.2px;
}
QPushButton[class="table-action-btn"]:hover {
    background: rgba(255,255,255,0.14);
    color: white;
    border-color: rgba(255,255,255,0.25);
}

/* ── TABLE TITLE ────────────────────────────────────────────────────────── */
QLabel[class="table-title"] {
    font-size: 22px;
    font-weight: 800;
    color: white;
    letter-spacing: -0.5px;
}

/* ── NOTIFICATION BUTTON ─────────────────────────────────────────────────── */
QPushButton[class="table-notify-btn"] {
    background: #ef4444;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 800;
    font-size: 12px;
    padding: 0 14px;
}

/* ── TABLE CARDS ─────────────────────────────────────────────────────────── */
QFrame[class="table-card"] {
    border-radius: 14px;
    border: 2px solid #e2e8f0;
}

/* ── TAKEAWAY BUTTON ─────────────────────────────────────────────────────── */
QPushButton[class="btn-takeaway"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #059669, stop:1 #10b981);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.3px;
}
QPushButton[class="btn-takeaway"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #059669, stop:1 #7c3aed);
}

/* ── BACK BUTTON ─────────────────────────────────────────────────────────── */
QPushButton[class="btn-back"] {
    background: rgba(255,255,255,0.08);
    color: #94a3b8;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 9px;
    padding: 0 16px;
    font-size: 13px;
    font-weight: 700;
}
QPushButton[class="btn-back"]:hover {
    background: rgba(255,255,255,0.15);
    color: white;
}

/* ── MENU SEARCH ─────────────────────────────────────────────────────────── */
QLineEdit[class="menu-search"] {
    background: #f8fafc;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 0 14px;
    font-size: 13px;
    color: #1e293b;
    selection-background-color: #059669;
}
QLineEdit[class="menu-search"]:focus {
    border-color: #059669;
    background: white;
}

/* ── CATEGORY BUTTONS ────────────────────────────────────────────────────── */
QPushButton[class="cat-btn"] {
    background: #f1f5f9;
    color: #64748b;
    border: 1.5px solid #e2e8f0;
    border-radius: 20px;
    padding: 0 18px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton[class="cat-btn"]:hover {
    background: #e2e8f0;
    color: #334155;
}
QPushButton[class="cat-btn-active"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #059669, stop:1 #10b981);
    color: white;
    border: none;
    border-radius: 20px;
    padding: 0 18px;
    font-size: 12px;
    font-weight: 700;
}

/* ── MENU ITEM CARDS ─────────────────────────────────────────────────────── */
QFrame[class="item-card"] {
    background: white;
    border: 1.5px solid #f1f5f9;
    border-radius: 14px;
}
QFrame[class="item-card"]:hover {
    border-color: #059669;
    background: #fafbff;
}

QLabel[class="item-name"] {
    color: #1e293b;
    font-size: 12px;
    font-weight: 700;
}
QLabel[class="item-price"] {
    color: #059669;
    font-size: 13px;
    font-weight: 800;
}

/* ── INFO LABEL ──────────────────────────────────────────────────────────── */
QLabel[class="info-label"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f8fafc, stop:1 #f1f5f9);
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px 14px;
    color: #475569;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}

/* ── CRM CARD ────────────────────────────────────────────────────────────── */
QFrame[class="crm-card"] {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 10px;
}

/* ── CART TABLE ──────────────────────────────────────────────────────────── */
QTableWidget[class="cart-table"] {
    background: white;
    border: 1.5px solid #f1f5f9;
    border-radius: 10px;
    gridline-color: transparent;
    selection-background-color: #ede9fe;
    selection-color: #059669;
    alternate-background-color: #fafbff;
}
QTableWidget[class="cart-table"] QHeaderView::section {
    background: #f8fafc;
    color: #64748b;
    font-size: 11px;
    font-weight: 700;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* ── TOTALS CARD ─────────────────────────────────────────────────────────── */
QFrame[class="totals-card"] {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 10px;
}

/* ── PIN DIALOG ──────────────────────────────────────────────────────────── */
QLabel[class="pin-title"] {
    font-size: 16px;
    font-weight: 800;
    color: #1e293b;
}
QLineEdit[class="pin-display"] {
    background: #f8fafc;
    border: 2px solid #059669;
    border-radius: 10px;
    font-size: 22px;
    font-weight: 900;
    color: #059669;
    letter-spacing: 8px;
}
QPushButton[class="pin-key"] {
    background: white;
    border: 1.5px solid #e2e8f0;
    border-radius: 10px;
    font-size: 18px;
    font-weight: 700;
    color: #1e293b;
}
QPushButton[class="pin-key"]:hover {
    background: #f1f5f9;
    border-color: #059669;
    color: #059669;
}
QPushButton[class="pin-key-c"] {
    background: #fef2f2;
    border-color: #fecaca;
    color: #ef4444;
}
QPushButton[class="pin-key-back"] {
    background: #fff7ed;
    border-color: #fed7aa;
    color: #f97316;
}
QPushButton[class="pin-confirm"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #059669, stop:1 #10b981);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 1px;
}
QPushButton[class="pin-confirm"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #059669, stop:1 #7c3aed);
}

/* ── PAYMENT DIALOG ──────────────────────────────────────────────────────── */
QFrame[class="payment-total-card"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0f172a, stop:1 #1e293b);
    border: none;
    border-radius: 14px;
}
QLabel[class="payment-total-label"] {
    color: #94a3b8;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
QLabel[class="payment-total-amount"] {
    color: white;
    font-size: 32px;
    font-weight: 900;
    letter-spacing: -1px;
}
QFrame[class="payment-method-btn"] {
    background: white;
    border: 2px solid #e2e8f0;
    border-radius: 12px;
}
QFrame[class="payment-method-btn-selected"] {
    border-color: #059669;
    background: #fafbff;
}
QDoubleSpinBox[class="payment-received"] {
    background: #f8fafc;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    font-size: 18px;
    font-weight: 800;
    color: #1e293b;
    padding: 0 12px;
}
QDoubleSpinBox[class="payment-received"]:focus {
    border-color: #059669;
}
QLabel[class="payment-change"] {
    color: #10b981;
    font-size: 15px;
    font-weight: 800;
}
QPushButton[class="payment-cancel"] {
    background: #f1f5f9;
    color: #64748b;
    border: 1.5px solid #e2e8f0;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 700;
    padding: 0 24px;
}
QPushButton[class="payment-cancel"]:hover {
    background: #e2e8f0;
}
QPushButton[class="payment-confirm"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #059669, stop:1 #10b981);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 800;
    padding: 0 28px;
}
QPushButton[class="payment-confirm"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #047857, stop:1 #059669);
}

/* ── SHIFT DIALOGS ───────────────────────────────────────────────────────── */
QLabel[class="shift-welcome"] {
    font-size: 17px;
    font-weight: 800;
    color: #1e293b;
    letter-spacing: -0.3px;
}
QDoubleSpinBox[class="shift-spin"] {
    background: #f8fafc;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    font-size: 16px;
    font-weight: 700;
    color: #1e293b;
    padding: 0 12px;
}
QDoubleSpinBox[class="shift-spin"]:focus {
    border-color: #059669;
}
QLabel[class="shift-diff"] {
    border-radius: 10px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 800;
    text-align: center;
}

/* ── SPLIT BILL DIALOG ───────────────────────────────────────────────────── */
QLabel[class="split-total"] {
    font-size: 15px;
    font-weight: 800;
    color: #1e293b;
}
QLabel[class="split-remaining"] {
    font-size: 13px;
    font-weight: 700;
}
QDoubleSpinBox[class="split-spin"] {
    background: #f8fafc;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    padding: 0 10px;
    font-size: 14px;
    font-weight: 700;
}

/* ── MODIFIER BUTTONS ────────────────────────────────────────────────────── */
QPushButton[class="modifier-btn"] {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    color: #475569;
    font-size: 12px;
    font-weight: 600;
}
QPushButton[class="modifier-btn"]:hover {
    background: #ede9fe;
    border-color: #059669;
    color: #059669;
}
QLineEdit[class="note-input"] {
    background: #f8fafc;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 0 14px;
    font-size: 13px;
    color: #1e293b;
}
QLineEdit[class="note-input"]:focus {
    border-color: #059669;
}

/* ── CARD BASE ───────────────────────────────────────────────────────────── */
QFrame[class="card"] {
    background: white;
    border: 1.5px solid #f1f5f9;
    border-radius: 12px;
}

/* ── DIVIDER ─────────────────────────────────────────────────────────────── */
QFrame[class="divider"] {
    color: #e2e8f0;
    background: #e2e8f0;
    max-height: 1px;
}

/* ── BADGE ───────────────────────────────────────────────────────────────── */
QLabel[class="badge"] {
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.3px;
}

/* ── ACTION BUTTONS (generic) ────────────────────────────────────────────── */
QPushButton[class="action-btn"] {
    border: none;
    border-radius: 8px;
    color: white;
    font-size: 12px;
    font-weight: 700;
    padding: 0 16px;
}
QPushButton[class="action-btn"]:hover {
    opacity: 0.9;
}

/* ── ICON BUTTONS ────────────────────────────────────────────────────────── */
QPushButton[class="icon-btn"] {
    background: rgba(99,102,241,0.1);
    border: none;
    border-radius: 8px;
}
QPushButton[class="icon-btn"]:hover {
    background: rgba(99,102,241,0.2);
}

/* ── KITCHEN DISPLAY ─────────────────────────────────────────────────────── */
QWidget[class="kitchen-display"] {
    background: #0f172a;
}
QLabel[class="kitchen-title"] {
    font-size: 22px;
    font-weight: 900;
    color: white;
    letter-spacing: -0.5px;
}
QFrame[class="kitchen-card"] {
    background: #1e293b;
    border-radius: 14px;
    border-left: 4px solid #10b981;
}
QLabel[class="kitchen-tbl"] {
    font-size: 16px;
    font-weight: 900;
    color: white;
}
QLabel[class="kitchen-timer"] {
    font-size: 13px;
    font-weight: 800;
}
QLabel[class="kitchen-meta"] {
    color: #64748b;
    font-size: 11px;
    font-weight: 600;
}
QLabel[class="kitchen-token"] {
    color: #f59e0b;
    font-size: 12px;
    font-weight: 800;
    background: rgba(245,158,11,0.1);
    border-radius: 6px;
    padding: 3px 8px;
}
QPushButton[class="btn-kitchen-ready"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #059669, stop:1 #10b981);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.5px;
}
QPushButton[class="btn-kitchen-refresh"] {
    background: rgba(245,158,11,0.15);
    color: #f59e0b;
    border: 1px solid rgba(245,158,11,0.3);
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    padding: 0 16px;
}

/* ── SCROLLBARS ──────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 3px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── COMBOBOX ────────────────────────────────────────────────────────────── */
QComboBox {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 0 10px;
    color: #1e293b;
    font-size: 12px;
    font-weight: 600;
}
QComboBox:focus { border-color: #059669; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: white;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    selection-background-color: #ede9fe;
    selection-color: #059669;
    font-size: 12px;
    padding: 4px;
}

/* ── LINE EDITS (generic) ────────────────────────────────────────────────── */
QLineEdit {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 0 10px;
    color: #1e293b;
    font-size: 12px;
    selection-background-color: #ede9fe;
}
QLineEdit:focus { border-color: #059669; background: white; }

/* ── SPINBOXES (generic) ─────────────────────────────────────────────────── */
QDoubleSpinBox, QSpinBox {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 0 8px;
    color: #1e293b;
    font-size: 12px;
}
QDoubleSpinBox:focus, QSpinBox:focus { border-color: #059669; }

/* ── DIALOG BASE ─────────────────────────────────────────────────────────── */
QDialog {
    background: #f8fafc;
    border-radius: 16px;
}

/* ── MESSAGE BOX ─────────────────────────────────────────────────────────── */
QMessageBox {
    background: white;
}
QMessageBox QPushButton {
    background: #059669;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 6px 20px;
    font-weight: 700;
    min-width: 80px;
}
QMessageBox QPushButton:hover {
    background: #059669;
}

"""


# ─────────────────────────────────────────────────────────────────────────────
#  WIDGET FACTORIES
# ─────────────────────────────────────────────────────────────────────────────

def _divider():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setProperty("class", "divider")
    return f


def _card(radius=10, padding="16px"):
    f = QFrame()
    f.setProperty("class", "card")
    return f


def _badge(text, bg, fg="white", radius=10):
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setProperty("class", "badge")
    lbl.setStyleSheet(f"background-color: {bg}; color: {fg};")
    return lbl


def _icon_btn(icon_name, icon_color, bg, hover_bg, tooltip="", fixed_size=None):
    btn = QPushButton()
    btn.setIcon(qta.icon(icon_name, color=icon_color))
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if fixed_size:
        btn.setFixedSize(*fixed_size)
    btn.setProperty("class", "icon-btn")
    return btn


def _action_btn(text, icon_name, bg, hover_bg, fg="white", height=36):
    btn = QPushButton(f"  {text}")
    btn.setIcon(qta.icon(icon_name, color=fg))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
    btn.setProperty("class", "action-btn")
    btn.setStyleSheet(f"background-color: {bg};")
    return btn


# ─────────────────────────────────────────────────────────────────────────────
#  UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def generate_invoice_no():
    """Sequential invoice numbers: INV-0001, INV-0002, ... stored in DB counter."""
    try:
        result = counters_col.find_one_and_update(
            {"_id": "invoice_no"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True,
        )
        seq = result.get("seq", 1)
        return f"INV-{seq:04d}"
    except Exception:
        # Fallback agar DB unavailable ho
        return f"INV-{datetime.now().strftime('%H%M%S')}"


def generate_token_no(shift_id, order_type):
    if not shift_id:
        return "N/A"
    prefix = "DIN"
    if order_type == "Takeaway":
        prefix = "TA"
    elif order_type == "Delivery":
        prefix = "DL"
    shift_id_str = str(shift_id)
    count = orders_col.count_documents({
        "shift_id": {"$in": [shift_id_str, shift_id]},
        "order_type": order_type
    })
    return f"{prefix}-{count + 1:02d}"
