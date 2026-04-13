"""
Print Preview Dialog — shows KOT and/or Bill preview before printing.
Uses QTextBrowser to render the HTML receipt/KOT on-screen.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextBrowser, QTabWidget, QWidget, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
import qtawesome as qta
import threading

from backend.utils.print_utils import (
    generate_kot_html,
    generate_thermal_invoice_html,
    print_kot,
    print_receipt,
    load_print_design,
    get_restaurant_info,
)

# ─── Colours (light theme) ─────────────────────────────────────────────────────
BG       = "#F0F2F5"
SURFACE  = "#FFFFFF"
BORDER   = "#E2E8F0"
ACCENT   = "#059669"
ACCENT_L = "#D1FAE5"
DANGER   = "#ef4444"
TEXT_PRI = "#1e293b"
TEXT_SEC = "#475569"


def _btn(text, color=ACCENT, icon_name=None, min_w=140, height=40):
    b = QPushButton(f"  {text}")
    if icon_name:
        b.setIcon(qta.icon(icon_name, color="white"))
    b.setMinimumWidth(min_w)
    b.setFixedHeight(height)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(f"""
        QPushButton {{
            background-color: {color};
            color: white; border: none; border-radius: 8px;
            font-size: 13px; font-weight: 700; padding: 0 16px;
        }}
        QPushButton:hover {{ background-color: {QColor(color).darker(115).name()}; }}
        QPushButton:pressed {{ background-color: {QColor(color).darker(130).name()}; }}
    """)
    return b


class _PreviewPane(QTextBrowser):
    """A styled HTML preview pane."""
    def __init__(self, html=""):
        super().__init__()
        self.setOpenLinks(False)
        self.setStyleSheet(f"""
            QTextBrowser {{
                background: white;
                border: 1.5px solid {BORDER};
                border-radius: 8px;
                padding: 8px;
                font-family: 'Courier New', monospace;
            }}
        """)
        if html:
            self.setHtml(html)


class PrintPreviewDialog(QDialog):
    """
    Shows a split preview of KOT (left) and Bill (right) before printing.
    mode: "both" | "kot" | "bill"
    """
    def __init__(self, order_data: dict, mode: str = "both", parent=None):
        super().__init__(parent)
        self.order_data = order_data
        self.mode = mode
        self._pd = load_print_design()
        self._ri = get_restaurant_info()

        self.setWindowTitle("Print Preview")
        self.setModal(True)
        self.setMinimumSize(860 if mode == "both" else 440, 620)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {BG}; }}
            QLabel {{ color: {TEXT_PRI}; background: transparent; }}
            QTabWidget::pane {{ border: none; background: {BG}; }}
            QTabBar::tab {{
                background: {SURFACE}; color: {TEXT_SEC};
                padding: 10px 20px; font-size: 13px; font-weight: 600;
                border: 1px solid {BORDER}; border-bottom: none;
                border-top-left-radius: 7px; border-top-right-radius: 7px;
                margin-right: 3px;
            }}
            QTabBar::tab:selected {{ background: {ACCENT}; color: white; border-color: {ACCENT}; }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setFixedHeight(58)
        hdr.setStyleSheet(f"background: {SURFACE}; border-bottom: 1.5px solid {BORDER};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(20, 0, 20, 0)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.eye", color=ACCENT).pixmap(22, 22))
        title_lbl = QLabel("Print Preview")
        title_lbl.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {TEXT_PRI};")
        sub_lbl = QLabel(f"  Order: {order_data.get('invoice_no', '')}  |  Table: {order_data.get('table_no', 'Takeaway')}")
        sub_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_SEC};")
        hl.addWidget(icon_lbl)
        hl.addWidget(title_lbl)
        hl.addWidget(sub_lbl)
        hl.addStretch()
        outer.addWidget(hdr)

        # ── Body ─────────────────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background: {BG};")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 14, 16, 10)
        body_layout.setSpacing(10)

        if mode == "both":
            split = QHBoxLayout()
            split.setSpacing(12)

            # KOT panel
            kot_panel = QVBoxLayout()
            kot_lbl = QLabel("  KOT — Kitchen Order Ticket")
            kot_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: #0ea5e9; padding: 4px 0;")
            self.kot_browser = _PreviewPane(self._render_kot())
            kot_panel.addWidget(kot_lbl)
            kot_panel.addWidget(self.kot_browser)

            # Bill panel
            bill_panel = QVBoxLayout()
            bill_lbl = QLabel("  BILL — Customer Receipt")
            bill_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {ACCENT}; padding: 4px 0;")
            self.bill_browser = _PreviewPane(self._render_bill())
            bill_panel.addWidget(bill_lbl)
            bill_panel.addWidget(self.bill_browser)

            split.addLayout(kot_panel, 1)
            split.addLayout(bill_panel, 1)
            body_layout.addLayout(split)

        elif mode == "kot":
            lbl = QLabel("  KOT — Kitchen Order Ticket")
            lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: #0ea5e9; padding: 4px 0;")
            self.kot_browser = _PreviewPane(self._render_kot())
            body_layout.addWidget(lbl)
            body_layout.addWidget(self.kot_browser)

        elif mode == "bill":
            lbl = QLabel("  BILL — Customer Receipt")
            lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {ACCENT}; padding: 4px 0;")
            self.bill_browser = _PreviewPane(self._render_bill())
            body_layout.addWidget(lbl)
            body_layout.addWidget(self.bill_browser)

        outer.addWidget(body, stretch=1)

        # ── Footer buttons ────────────────────────────────────────────────────────
        footer = QFrame()
        footer.setFixedHeight(64)
        footer.setStyleSheet(f"background: {SURFACE}; border-top: 1.5px solid {BORDER};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(20, 0, 20, 0)
        fl.setSpacing(10)

        btn_close = _btn("Close", color="#64748b", icon_name="fa5s.times", min_w=100)
        btn_close.clicked.connect(self.reject)
        fl.addWidget(btn_close)
        fl.addStretch()

        if mode in ("both", "kot"):
            self.btn_print_kot = _btn("Print KOT", color="#0ea5e9", icon_name="fa5s.paper-plane")
            self.btn_print_kot.clicked.connect(self._print_kot)
            fl.addWidget(self.btn_print_kot)

        if mode in ("both", "bill"):
            self.btn_print_bill = _btn("Print Bill", color=ACCENT, icon_name="fa5s.print")
            self.btn_print_bill.clicked.connect(self._print_bill)
            fl.addWidget(self.btn_print_bill)

        if mode == "both":
            btn_both = _btn("Print Both", color="#7c3aed", icon_name="fa5s.layer-group")
            btn_both.clicked.connect(self._print_both)
            fl.addWidget(btn_both)

        outer.addWidget(footer)

    # ── HTML generators ────────────────────────────────────────────────────────

    def _render_kot(self):
        return generate_kot_html(
            self.order_data,
            restaurant_info=self._ri,
            print_design=self._pd.get("kot"),
        )

    def _render_bill(self):
        return generate_thermal_invoice_html(
            self.order_data,
            restaurant_info=self._ri,
            print_design=self._pd.get("bill"),
        )

    # ── Print actions ─────────────────────────────────────────────────────────

    def _set_printing(self, printing: bool):
        for attr in ("btn_print_kot", "btn_print_bill"):
            btn = getattr(self, attr, None)
            if btn:
                btn.setEnabled(not printing)

    def _print_kot(self):
        self._set_printing(True)
        order = self.order_data
        def _do():
            success, msg = print_kot(order)
            if not success:
                print(f"[KOT Print Error] {msg}")
        threading.Thread(target=_do, daemon=True).start()
        self.accept()

    def _print_bill(self):
        self._set_printing(True)
        order = self.order_data
        def _do():
            success, msg = print_receipt(order)
            if not success:
                print(f"[Bill Print Error] {msg}")
        threading.Thread(target=_do, daemon=True).start()
        self.accept()

    def _print_both(self):
        self._set_printing(True)
        order = self.order_data
        def _do():
            print_kot(order)
            print_receipt(order)
        threading.Thread(target=_do, daemon=True).start()
        self.accept()
