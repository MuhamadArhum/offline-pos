"""
Shared UI constants, styles, and helper functions.
ALL pages must import from here to ensure visual consistency.
Designed to match the Settings Page style (the reference design).
"""

from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import qtawesome as qta

# ─────────────────────────────────────────────────────────────────────────────
#  COLOR CONSTANTS  (single source of truth for the entire app)
# ─────────────────────────────────────────────────────────────────────────────
BG           = "#F0F2F5"        # Slate 100 - Professional background
SURFACE      = "#FFFFFF"
BORDER       = "#E2E8F0"        # Slate 200
DIVIDER      = "#F1F5F9"        # Slate 100
ACCENT       = "#059669"       # Emerald Green  (primary)
ACCENT_DARK  = "#064e3b"       # Dark Emerald
ACCENT_LIGHT = "#D1FAE5"       # Light Emerald
SUCCESS      = "#22c55e"
SUCCESS_LT   = "#dcfce7"
DANGER       = "#ef4444"
DANGER_LT    = "#fee2e2"
WARNING      = "#f59e0b"
WARNING_LT   = "#fef3c7"
INFO         = "#14b8a6"
INFO_LT      = "#ccfbf1"
AMBER        = "#f59e0b"
AMBER_LT     = "#fef9c3"
TEXT_PRI     = "#1e293b"
TEXT_SEC     = "#475569"
TEXT_MUTED   = "#94a3b8"

# Legacy C dict — imported by pages that still reference C['key']
C = {
    "bg":           BG,
    "surface":      SURFACE,
    "card":         SURFACE,
    "sidebar":      ACCENT_DARK,
    "sidebar_alt":  "#065f46",
    "primary":      ACCENT,
    "primary_dk":   ACCENT_DARK,
    "primary_lt":   ACCENT_LIGHT,
    "success":      SUCCESS,
    "success_lt":   SUCCESS_LT,
    "warning":      WARNING,
    "warning_lt":   WARNING_LT,
    "danger":       DANGER,
    "danger_lt":    DANGER_LT,
    "info":         INFO,
    "info_lt":      INFO_LT,
    "amber":        AMBER,
    "amber_lt":     AMBER_LT,
    "text_primary": TEXT_PRI,
    "text_sec":     TEXT_SEC,
    "text_hint":    TEXT_MUTED,
    "border":       BORDER,
    "divider":      DIVIDER,
    "table_free":   SUCCESS,
    "table_occ":    DANGER,
    "table_res":    WARNING,
}

# ─────────────────────────────────────────────────────────────────────────────
#  GLOBAL STYLESHEET
# ─────────────────────────────────────────────────────────────────────────────
# The global stylesheet is now loaded from app/resources/style.qss
# via Theme.get_stylesheet() in main.py
GLOBAL_STYLE = ""  # Deprecated, kept for compatibility

# ─────────────────────────────────────────────────────────────────────────────
#  COLOR UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
def _lighten(hex_color, factor=15):
    c = QColor(hex_color)
    return QColor(min(c.red()+factor,255), min(c.green()+factor,255), min(c.blue()+factor,255)).name()

def _darken(hex_color, factor=15):
    c = QColor(hex_color)
    return QColor(max(c.red()-factor,0), max(c.green()-factor,0), max(c.blue()-factor,0)).name()

# ─────────────────────────────────────────────────────────────────────────────
#  BUTTON HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def make_btn(text, color=ACCENT, text_color="white", icon=None, height=40):
    """Primary solid button (green by default)."""
    btn = QPushButton(text)
    if icon:
        btn.setIcon(icon)
    btn.setMinimumHeight(height)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    
    # Use consolidated class from style.qss
    btn.setProperty("class", "btn-primary")
    
    # Fallback/Inline override if custom color is passed (rare case)
    if color != ACCENT:
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
    """Outlined / ghost button (white bg, border)."""
    btn = QPushButton(text)
    if icon:
        btn.setIcon(icon)
    btn.setMinimumHeight(height)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setProperty("class", "btn-ghost")
    return btn

def make_danger_btn(text, icon=None, height=38):
    """Destructive / danger button (red)."""
    btn = QPushButton(text)
    if icon:
        btn.setIcon(icon)
    btn.setMinimumHeight(height)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setProperty("class", "btn-danger")
    return btn

def make_warning_btn(text, icon=None, height=38):
    """Warning button (amber)."""
    btn = QPushButton(text)
    if icon:
        btn.setIcon(icon)
    btn.setMinimumHeight(height)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setProperty("class", "btn-warning")
    return btn

# ─────────────────────────────────────────────────────────────────────────────
#  LAYOUT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def card():
    """White card frame with border and rounded corners."""
    f = QFrame()
    f.setProperty("class", "card")
    return f

def divider_line():
    """Thin horizontal divider line."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setProperty("class", "divider")
    return line

def section_header_lbl(text):
    """Small uppercase section label (e.g. 'FILTERS', 'ACTIONS')."""
    lbl = QLabel(text.upper())
    lbl.setProperty("class", "section-header")
    return lbl

def card_title(text, icon_name=None, icon_color=ACCENT):
    """Card title row with optional icon — returns a QHBoxLayout."""
    layout = QHBoxLayout()
    layout.setSpacing(10)
    if icon_name:
        ico = QLabel()
        ico.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(20, 20))
        ico.setStyleSheet("background: transparent;")
        layout.addWidget(ico)
    lbl = QLabel(text)
    # Inline style kept for specific font-size override not in global class yet
    lbl.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {TEXT_PRI}; background: transparent;")
    layout.addWidget(lbl)
    layout.addStretch()
    return layout

def page_header(title, subtitle=None, right_widget=None):
    """
    White 64px page header bar.
    Returns the QFrame (add it to your page layout first).
    """
    header = QFrame()
    header.setFixedHeight(64)
    header.setProperty("class", "page-header")
    
    h_layout = QHBoxLayout(header)
    h_layout.setContentsMargins(28, 0, 28, 0)
    h_layout.setSpacing(12)

    text_col = QWidget()
    text_col.setStyleSheet("background: transparent; border: none;")
    from PyQt6.QtWidgets import QVBoxLayout
    tc_lay = QVBoxLayout(text_col)
    tc_lay.setContentsMargins(0, 0, 0, 0)
    tc_lay.setSpacing(1)

    title_lbl = QLabel(title)
    title_lbl.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {TEXT_PRI}; background: transparent;")
    tc_lay.addWidget(title_lbl)

    if subtitle:
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED}; background: transparent;")
        tc_lay.addWidget(sub_lbl)

    h_layout.addWidget(text_col)
    h_layout.addStretch()

    if right_widget:
        h_layout.addWidget(right_widget)

    return header
